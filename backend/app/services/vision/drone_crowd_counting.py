import os
from pathlib import Path
from threading import Lock

import cv2
import numpy as np
import torch
import torch.nn as nn


BACKEND_DIR = Path(__file__).resolve().parents[3]
DEFAULT_MODEL_PATH = BACKEND_DIR / "models" / "partBmodel_best.pth.tar"
MODEL_PATH = Path(os.getenv("DRONE_CROWD_MODEL_PATH", DEFAULT_MODEL_PATH))
MODEL_NAME = "CSRNet Part B Best"
IMAGENET_MEAN = torch.tensor([0.485, 0.456, 0.406]).view(1, 3, 1, 1)
IMAGENET_STD = torch.tensor([0.229, 0.224, 0.225]).view(1, 3, 1, 1)

_device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
_model = None
_model_error = None
_model_lock = Lock()


class CSRNet(nn.Module):
    """CSRNet architecture from leeyeehoo/CSRNet-pytorch."""

    def __init__(self):
        super().__init__()
        frontend_feat = [64, 64, "M", 128, 128, "M", 256, 256, 256, "M", 512, 512, 512]
        backend_feat = [512, 512, 512, 256, 128, 64]

        self.frontend = make_layers(frontend_feat)
        self.backend = make_layers(backend_feat, in_channels=512, dilation=True)
        self.output_layer = nn.Conv2d(64, 1, kernel_size=1)
        self._initialize_weights()

    def forward(self, x):
        x = self.frontend(x)
        x = self.backend(x)
        return self.output_layer(x)

    def _initialize_weights(self):  # pragma: no cover - deterministic shape init only
        for layer in self.modules():
            if isinstance(layer, nn.Conv2d):
                nn.init.normal_(layer.weight, std=0.01)
                if layer.bias is not None:
                    nn.init.constant_(layer.bias, 0)


def make_layers(cfg, in_channels=3, dilation=False):
    dilation_rate = 2 if dilation else 1
    layers = []

    for item in cfg:
        if item == "M":
            layers.append(nn.MaxPool2d(kernel_size=2, stride=2))
            continue

        layers.extend(
            [
                nn.Conv2d(
                    in_channels,
                    item,
                    kernel_size=3,
                    padding=dilation_rate,
                    dilation=dilation_rate,
                ),
                nn.ReLU(inplace=True),
            ]
        )
        in_channels = item

    return nn.Sequential(*layers)


def _extract_state_dict(checkpoint):
    state_dict = checkpoint.get("state_dict", checkpoint) if isinstance(checkpoint, dict) else checkpoint

    if not isinstance(state_dict, dict):
        raise ValueError("Checkpoint does not contain a PyTorch state_dict")

    return {
        key.removeprefix("module."): value
        for key, value in state_dict.items()
        if isinstance(value, torch.Tensor)
    }


def _load_model():
    global _model, _model_error

    if _model is not None:
        return _model

    with _model_lock:
        if _model is not None:
            return _model

        if not MODEL_PATH.exists():
            _model_error = f"Model weights not found at {MODEL_PATH}"
            return None

        try:
            model = CSRNet().to(_device)
            checkpoint = torch.load(MODEL_PATH, map_location=_device, weights_only=False)
            model.load_state_dict(_extract_state_dict(checkpoint))
            model.eval()
            _model = model
            _model_error = None
        except Exception as error:
            _model = None
            _model_error = str(error)

        return _model


def get_model_status():
    model = _load_model()

    return {
        "model_name": MODEL_NAME,
        "model_path": str(MODEL_PATH),
        "runtime_device": str(_device),
        "configured": MODEL_PATH.exists(),
        "loaded": model is not None,
        "error": _model_error,
    }


def estimate_crowd(frame):
    model = _load_model()

    if model is None:
        raise RuntimeError(_model_error or "Drone crowd model is not configured")

    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    image = rgb_frame.astype(np.float32) / 255.0
    tensor = torch.tensor(image).permute(2, 0, 1).unsqueeze(0).to(_device)
    tensor = (tensor - IMAGENET_MEAN.to(_device)) / IMAGENET_STD.to(_device)

    with torch.no_grad():
        density = model(tensor)

    return {
        "count": float(density.sum().item()),
        "model_name": MODEL_NAME,
        "model_path": str(MODEL_PATH),
        "runtime_device": str(_device),
    }
