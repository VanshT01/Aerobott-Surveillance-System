#!/usr/bin/env python3
"""Prepare ShanghaiTech annotations for CSRNet training.

Expected input layout is the standard ShanghaiTech structure:

part_A_final/train_data/images/IMG_1.jpg
part_A_final/train_data/ground_truth/GT_IMG_1.mat
part_A_final/test_data/images/IMG_1.jpg
part_A_final/test_data/ground_truth/GT_IMG_1.mat

The script writes one .h5 density map beside each .mat file and JSON image
lists that are compatible with the training script in this project.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prepare ShanghaiTech data for CSRNet")
    parser.add_argument("dataset_root", type=Path, help="Path containing part_A_final and/or part_B_final")
    parser.add_argument("--output-dir", type=Path, default=Path("backend/models/csrnet_data"))
    parser.add_argument("--parts", nargs="+", default=["part_A_final", "part_B_final"])
    return parser.parse_args()


def read_points(mat_path: Path) -> np.ndarray:
    from scipy.io import loadmat

    data = loadmat(mat_path)
    points = data["image_info"][0][0][0][0][0]
    return np.asarray(points, dtype=np.float32)


def geometry_adaptive_density(shape: tuple[int, int], points: np.ndarray) -> np.ndarray:
    from scipy.ndimage import gaussian_filter
    from scipy.spatial import KDTree

    density = np.zeros(shape, dtype=np.float32)

    if len(points) == 0:
        return density

    neighbor_count = min(4, len(points))
    tree = KDTree(points.copy(), leafsize=2048)
    distances, _ = tree.query(points, k=neighbor_count)
    distances = np.atleast_2d(distances)

    for index, point in enumerate(points):
        x = min(shape[1] - 1, max(0, int(point[0])))
        y = min(shape[0] - 1, max(0, int(point[1])))
        point_map = np.zeros(shape, dtype=np.float32)
        point_map[y, x] = 1.0

        sigma = np.average(distances[index][1:neighbor_count]) * 0.1 if neighbor_count > 1 else 15.0
        density += gaussian_filter(point_map, sigma, mode="constant")

    return density


def image_path_for_mat(mat_path: Path, image_dir: Path) -> Path:
    return image_dir / mat_path.name.removeprefix("GT_").replace(".mat", ".jpg")


def prepare_split(part_dir: Path, split: str) -> list[str]:
    import h5py
    from PIL import Image

    split_dir = part_dir / split
    image_dir = split_dir / "images"
    gt_dir = split_dir / "ground_truth"
    image_paths: list[str] = []

    if not image_dir.exists() or not gt_dir.exists():
        return image_paths

    for mat_path in sorted(gt_dir.glob("GT_*.mat")):
        image_path = image_path_for_mat(mat_path, image_dir)
        if not image_path.exists():
            print(f"missing image for {mat_path}")
            continue

        with Image.open(image_path) as image:
            width, height = image.size

        density = geometry_adaptive_density((height, width), read_points(mat_path))
        h5_path = gt_dir / image_path.with_suffix(".h5").name
        with h5py.File(h5_path, "w") as h5_file:
            h5_file["density"] = density

        image_paths.append(str(image_path.resolve()))

    return image_paths


def main() -> None:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    for part in args.parts:
        part_dir = args.dataset_root / part
        if not part_dir.exists():
            continue

        train = prepare_split(part_dir, "train_data")
        test = prepare_split(part_dir, "test_data")
        stem = part.replace("_final", "")

        if train:
            (args.output_dir / f"{stem}_train.json").write_text(json.dumps(train, indent=2))
        if test:
            (args.output_dir / f"{stem}_test.json").write_text(json.dumps(test, indent=2))

        print(f"{part}: {len(train)} train images, {len(test)} test images")


if __name__ == "__main__":
    main()
