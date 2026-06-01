# Crowd Counting Model

This project now has backend and dashboard support for density-map crowd counting.

The backend expects a TorchScript model at:

```text
backend/crowd_count_model.pt
```

or at the path configured by:

```env
CROWD_COUNT_MODEL_PATH=/absolute/path/to/crowd_count_model.pt
```

## Model Contract

The model should accept one normalized RGB image tensor:

```text
shape: [1, 3, H, W]
normalization: ImageNet mean/std
```

It should return a density map tensor whose sum is the estimated people count:

```python
count = density_map.sum()
```

This matches common density-map models such as CSRNet, DM-Count, and similar architectures after exporting to TorchScript.

## Training With Your DLR Aerial Crowd Dataset

You provided:

```text
/Users/vanshtalreja/Downloads/DLR_AerialCrowdDataset.zip
```

This is not NWPU-Crowd, but it is very relevant for aerial crowd counting because it contains large aerial crowd images with point annotation masks.

Smoke test:

```bash
.venv/bin/python scripts/train_crowd_count.py \
  --data /Users/vanshtalreja/Downloads/DLR_AerialCrowdDataset.zip \
  --epochs 1 \
  --batch-size 1 \
  --crop-size 256 \
  --samples-per-epoch 2 \
  --checkpoint /private/tmp/crowd_smoke/best.pth \
  --output /private/tmp/crowd_smoke/crowd_count_model.pt
```

Real CPU-friendly run:

```bash
.venv/bin/python scripts/train_crowd_count.py \
  --data /Users/vanshtalreja/Downloads/DLR_AerialCrowdDataset.zip \
  --epochs 50 \
  --batch-size 1 \
  --crop-size 512 \
  --samples-per-epoch 512 \
  --checkpoint runs/crowd_count/best.pth \
  --output backend/crowd_count_model.pt
```

GPU run, if CUDA is available:

```bash
.venv/bin/python scripts/train_crowd_count.py \
  --data /Users/vanshtalreja/Downloads/DLR_AerialCrowdDataset.zip \
  --epochs 100 \
  --batch-size 4 \
  --crop-size 512 \
  --samples-per-epoch 1024 \
  --checkpoint runs/crowd_count/best.pth \
  --output backend/crowd_count_model.pt
```

After training, restart the backend and the dashboard should show the crowd model as configured/loaded.

## Recommended NWPU Training Flow

1. Download NWPU-Crowd from the official benchmark page:
   https://gjy3035.github.io/NWPU-Crowd-Sample-Code/

2. Adapt `scripts/train_crowd_count.py` to the NWPU annotation structure, or train a stronger external model such as CSRNet/DM-Count.

3. Export the trained model to TorchScript:

```python
import torch

model.eval()
example = torch.randn(1, 3, 768, 1024)
traced = torch.jit.trace(model, example)
traced.save("backend/crowd_count_model.pt")
```

4. Restart the backend.

5. Open the dashboard and click `Run Crowd Count` for a selected camera.

## API

Check model status:

```http
GET /crowd-count/model/status
```

Run count on a camera:

```http
POST /devices/{camera_id}/crowd-count
```

List saved counts:

```http
GET /crowd-counts?camera_id={camera_id}
```

Get latest count:

```http
GET /devices/{camera_id}/crowd-count/latest
```
