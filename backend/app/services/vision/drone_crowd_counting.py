import os
from pathlib import Path
from threading import Lock

import cv2
import numpy as np
import torch
import torch.nn as nn
from torchvision import models


BACKEND_DIR = Path(__file__).resolve().parents[3]
DEFAULT_MODEL_PATH = BACKEND_DIR / "models" / "csrnet_drone.pth"
MODEL_PATH = Path(os.getenv("DRONE_CROWD_MODEL_PATH", DEFAULT_MODEL_PATH))
MODEL_NAME = "Drone CSRNet"
INPUT_SIZE = (512, 512)

_device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
_model = None
_model_error = None
_model_lock = Lock()


class CSRNet(nn.Module):
    """CSRNet architecture from Mehak2005si/Drone-CrowdCounting."""

    def __init__(self):
        super().__init__()
        self.frontend = models.vgg16(weights=None).features[:23]
        self.backend = nn.Sequential(
            nn.Conv2d(512, 512, kernel_size=3, padding=2, dilation=2),
            nn.ReLU(inplace=True),
            nn.Conv2d(512, 512, kernel_size=3, padding=2, dilation=2),
            nn.ReLU(inplace=True),
            nn.Conv2d(512, 512, kernel_size=3, padding=2, dilation=2),
            nn.ReLU(inplace=True),
            nn.Conv2d(512, 256, kernel_size=3, padding=2, dilation=2),
            nn.ReLU(inplace=True),
            nn.Conv2d(256, 128, kernel_size=3, padding=2, dilation=2),
            nn.ReLU(inplace=True),
            nn.Conv2d(128, 64, kernel_size=3, padding=2, dilation=2),
            nn.ReLU(inplace=True),
        )
        self.output_layer = nn.Conv2d(64, 1, kernel_size=1)
        self._initialize_weights()

    def forward(self, x):
        x = self.frontend(x)
        x = self.backend(x)
        return self.output_layer(x)

    def _initialize_weights(self):
        for module in [self.backend, self.output_layer]:
            for layer in module.modules():
                if isinstance(layer, nn.Conv2d):
                    nn.init.normal_(layer.weight, std=0.01)
                    if layer.bias is not None:
                        nn.init.constant_(layer.bias, 0)


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
            state_dict = torch.load(MODEL_PATH, map_location=_device)
            model.load_state_dict(state_dict)
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
    resized = cv2.resize(rgb_frame, INPUT_SIZE)
    image = resized.astype(np.float32) / 255.0
    tensor = torch.tensor(image).permute(2, 0, 1).unsqueeze(0).to(_device)

    with torch.no_grad():
        density = model(tensor)

    return {
        "count": float(density.sum().item()),
        "model_name": MODEL_NAME,
        "model_path": str(MODEL_PATH),
        "runtime_device": str(_device),
    }
