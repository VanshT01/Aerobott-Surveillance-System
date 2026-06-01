import argparse
import random
import zipfile
from io import BytesIO
from pathlib import Path

import cv2
import numpy as np
from PIL import Image
import torch
from torch import nn
from torch.utils.data import Dataset, DataLoader


IMAGENET_MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32)
IMAGENET_STD = np.array([0.229, 0.224, 0.225], dtype=np.float32)


class SmallDensityNet(nn.Module):
    def __init__(self):
        super().__init__()

        self.net = nn.Sequential(
            nn.Conv2d(3, 32, 3, padding=1),
            nn.ReLU(inplace=True),
            nn.Conv2d(32, 32, 3, padding=1),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(2),

            nn.Conv2d(32, 64, 3, padding=1),
            nn.ReLU(inplace=True),
            nn.Conv2d(64, 64, 3, padding=1),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(2),

            nn.Conv2d(64, 128, 3, padding=2, dilation=2),
            nn.ReLU(inplace=True),
            nn.Conv2d(128, 128, 3, padding=2, dilation=2),
            nn.ReLU(inplace=True),
            nn.Conv2d(128, 64, 3, padding=2, dilation=2),
            nn.ReLU(inplace=True),
            nn.Conv2d(64, 1, 1),
            nn.Softplus()
        )

    def forward(self, x):
        return self.net(x)


class DLRAerialCrowdDataset(Dataset):
    def __init__(
        self,
        dataset_path,
        split="Train",
        crop_size=512,
        samples_per_epoch=512,
        sigma=6.0
    ):
        self.dataset_path = Path(dataset_path)
        self.split = split
        self.crop_size = crop_size
        self.samples_per_epoch = samples_per_epoch
        self.sigma = sigma
        self.output_stride = 4

        self.zip_file = None
        self.root_prefix = "DLR_AerialCrowdDataset"

        if self.dataset_path.suffix == ".zip":
            with zipfile.ZipFile(self.dataset_path) as archive:
                self.image_names = sorted([
                    name for name in archive.namelist()
                    if name.startswith(f"{self.root_prefix}/{split}/Images/")
                    and name.lower().endswith(".jpg")
                ])
        else:
            images_dir = self.dataset_path / split / "Images"
            self.image_names = sorted(str(path) for path in images_dir.glob("*.jpg"))

        if not self.image_names:
            raise RuntimeError(f"No {split} images found in {dataset_path}")

    def __len__(self):
        return self.samples_per_epoch

    def _archive(self):
        if self.zip_file is None:
            self.zip_file = zipfile.ZipFile(self.dataset_path)

        return self.zip_file

    def _read_pair(self, image_name):
        if self.dataset_path.suffix == ".zip":
            annotation_name = image_name.replace("/Images/", "/Annotation/").replace(".jpg", ".png")

            archive = self._archive()
            image = Image.open(BytesIO(archive.read(image_name))).convert("RGB")
            annotation = Image.open(BytesIO(archive.read(annotation_name))).convert("L")
        else:
            image_path = Path(image_name)
            annotation_path = (
                self.dataset_path
                / self.split
                / "Annotation"
                / f"{image_path.stem}.png"
            )

            image = Image.open(image_path).convert("RGB")
            annotation = Image.open(annotation_path).convert("L")

        return np.array(image), np.array(annotation)

    def _random_crop(self, image, annotation):
        height, width = image.shape[:2]
        crop_size = min(self.crop_size, height, width)

        if width == crop_size:
            x = 0
        else:
            x = random.randint(0, width - crop_size)

        if height == crop_size:
            y = 0
        else:
            y = random.randint(0, height - crop_size)

        return (
            image[y:y + crop_size, x:x + crop_size],
            annotation[y:y + crop_size, x:x + crop_size]
        )

    def _density_map(self, annotation):
        point_map = (annotation > 0).astype(np.float32)
        point_count = float(point_map.sum())

        if point_count == 0:
            density = point_map
        else:
            density = cv2.GaussianBlur(point_map, (0, 0), self.sigma)
            density_sum = float(density.sum())

            if density_sum > 0:
                density *= point_count / density_sum

        out_h = max(1, density.shape[0] // self.output_stride)
        out_w = max(1, density.shape[1] // self.output_stride)
        resized = cv2.resize(density, (out_w, out_h), interpolation=cv2.INTER_AREA)
        resized *= (density.shape[0] * density.shape[1]) / (out_h * out_w)

        return resized.astype(np.float32)

    def __getitem__(self, index):
        image_name = random.choice(self.image_names)
        image, annotation = self._read_pair(image_name)
        image, annotation = self._random_crop(image, annotation)

        image = image.astype(np.float32) / 255.0
        image = (image - IMAGENET_MEAN) / IMAGENET_STD
        image = image.transpose(2, 0, 1)

        density = self._density_map(annotation)

        return (
            torch.from_numpy(image).float(),
            torch.from_numpy(density[None, ...]).float()
        )


def evaluate(model, loader, device):
    model.eval()
    errors = []

    with torch.no_grad():
        for images, targets in loader:
            images = images.to(device)
            targets = targets.to(device)
            predictions = model(images)

            pred_counts = predictions.flatten(1).sum(dim=1)
            target_counts = targets.flatten(1).sum(dim=1)
            errors.extend((pred_counts - target_counts).abs().cpu().tolist())

    model.train()

    if not errors:
        return 0.0

    return sum(errors) / len(errors)


def export_torchscript(model, output_path, crop_size):
    model.eval()
    example = torch.randn(1, 3, crop_size, crop_size)
    traced = torch.jit.trace(model.cpu(), example)
    traced.save(str(output_path))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", required=True, help="DLR dataset zip or extracted dataset path")
    parser.add_argument("--epochs", type=int, default=20)
    parser.add_argument("--batch-size", type=int, default=2)
    parser.add_argument("--crop-size", type=int, default=512)
    parser.add_argument("--samples-per-epoch", type=int, default=512)
    parser.add_argument("--lr", type=float, default=1e-4)
    parser.add_argument("--output", default="backend/crowd_count_model.pt")
    parser.add_argument("--checkpoint", default="runs/crowd_count/best.pth")
    args = parser.parse_args()

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Using device: {device}", flush=True)

    train_dataset = DLRAerialCrowdDataset(
        args.data,
        split="Train",
        crop_size=args.crop_size,
        samples_per_epoch=args.samples_per_epoch
    )
    test_dataset = DLRAerialCrowdDataset(
        args.data,
        split="Test",
        crop_size=args.crop_size,
        samples_per_epoch=max(32, args.batch_size * 8)
    )

    train_loader = DataLoader(
        train_dataset,
        batch_size=args.batch_size,
        shuffle=False,
        num_workers=0
    )
    test_loader = DataLoader(
        test_dataset,
        batch_size=args.batch_size,
        shuffle=False,
        num_workers=0
    )

    model = SmallDensityNet().to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=args.lr)
    loss_fn = nn.MSELoss()
    best_mae = float("inf")

    checkpoint_path = Path(args.checkpoint)
    checkpoint_path.parent.mkdir(parents=True, exist_ok=True)

    for epoch in range(1, args.epochs + 1):
        model.train()
        running_loss = 0.0

        for step, (images, targets) in enumerate(train_loader, start=1):
            images = images.to(device)
            targets = targets.to(device)

            predictions = model(images)
            density_loss = loss_fn(predictions, targets)
            count_loss = (
                predictions.flatten(1).sum(dim=1)
                - targets.flatten(1).sum(dim=1)
            ).abs().mean()
            loss = density_loss + 1e-4 * count_loss

            optimizer.zero_grad()
            loss.backward()
            optimizer.step()

            running_loss += float(loss.item())

            if step == 1 or step % 25 == 0:
                print(
                    f"epoch={epoch} step={step}/{len(train_loader)} "
                    f"loss={running_loss / step:.4f}",
                    flush=True
                )

        mae = evaluate(model, test_loader, device)
        print(
            f"epoch={epoch} train_loss={running_loss / len(train_loader):.4f} val_mae={mae:.2f}",
            flush=True
        )

        if mae < best_mae:
            best_mae = mae
            torch.save(model.state_dict(), checkpoint_path)
            print(f"saved checkpoint: {checkpoint_path}", flush=True)

    model.load_state_dict(torch.load(checkpoint_path, map_location=device))
    export_torchscript(model, Path(args.output), args.crop_size)
    print(f"exported TorchScript model: {args.output}", flush=True)


if __name__ == "__main__":
    main()
