import os
from pathlib import Path
import threading

import cv2
import numpy as np


MODEL_NAME = "nwpu-density-map-torchscript"
BACKEND_DIR = Path(__file__).resolve().parents[3]
DEFAULT_MODEL_PATH = BACKEND_DIR / "crowd_count_model.pt"
configured_model_path = os.getenv("CROWD_COUNT_MODEL_PATH")

if configured_model_path:
    configured_model_path = Path(configured_model_path)
    MODEL_PATH = (
        configured_model_path
        if configured_model_path.is_absolute()
        else BACKEND_DIR / configured_model_path
    )
else:
    MODEL_PATH = DEFAULT_MODEL_PATH

MAX_INPUT_SIZE = int(os.getenv("CROWD_COUNT_MAX_INPUT_SIZE", "1280"))

_model = None
_model_error = None
_model_lock = threading.Lock()


def get_model_status():
    return {
        "model_name": MODEL_NAME,
        "model_path": str(MODEL_PATH),
        "configured": MODEL_PATH.exists(),
        "loaded": _model is not None,
        "error": _model_error
    }


def _load_model():
    global _model, _model_error

    if _model is not None:
        return _model

    if not MODEL_PATH.exists():
        _model_error = f"Model file not found: {MODEL_PATH}"
        return None

    try:
        import torch

        model = torch.jit.load(str(MODEL_PATH), map_location="cpu")
        model.eval()
        _model = model
        _model_error = None
        return _model
    except Exception as error:
        _model_error = str(error)
        return None


def _resize_for_model(frame):
    height, width = frame.shape[:2]
    longest_side = max(height, width)

    if longest_side <= MAX_INPUT_SIZE:
        return frame, 1.0

    scale = MAX_INPUT_SIZE / longest_side
    resized = cv2.resize(
        frame,
        (int(width * scale), int(height * scale)),
        interpolation=cv2.INTER_AREA
    )

    return resized, scale


def _preprocess(frame):
    frame, scale = _resize_for_model(frame)
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0

    mean = np.array([0.485, 0.456, 0.406], dtype=np.float32)
    std = np.array([0.229, 0.224, 0.225], dtype=np.float32)
    rgb = (rgb - mean) / std

    tensor = rgb.transpose(2, 0, 1)[None, ...]

    return tensor, scale


def count_crowd(frame):
    with _model_lock:
        model = _load_model()

        if model is None:
            raise RuntimeError(_model_error or "Crowd counting model is not configured")

        import torch

        tensor, _scale = _preprocess(frame)
        input_tensor = torch.from_numpy(tensor)

        with torch.no_grad():
            density_map = model(input_tensor)

        if isinstance(density_map, (list, tuple)):
            density_map = density_map[0]

        density_map = density_map.detach().cpu().float()

        # Most density-map models are trained so the output sum is the count.
        count = float(density_map.sum().item())

        return {
            "count": max(0.0, count),
            "model_name": MODEL_NAME
        }
