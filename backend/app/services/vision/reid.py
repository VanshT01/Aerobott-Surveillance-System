import json
import os
import shutil
import threading
from datetime import datetime, timezone
from pathlib import Path

import cv2
import numpy as np

from app.db.session import SessionLocal
from app.repositories import crud


BACKEND_DIR = Path(__file__).resolve().parents[3]
REID_DIR = BACKEND_DIR / "reid"
REID_MATCH_THRESHOLD = float(os.getenv("REID_MATCH_THRESHOLD", "0.82"))
REID_FALLBACK_MATCH_THRESHOLD = float(os.getenv("REID_FALLBACK_MATCH_THRESHOLD", "0.55"))
REID_SAMPLE_INTERVAL_SECONDS = float(os.getenv("REID_SAMPLE_INTERVAL_SECONDS", "3.0"))
REID_TRACK_CACHE_SECONDS = float(os.getenv("REID_TRACK_CACHE_SECONDS", "30.0"))
REID_MIN_CROP_WIDTH = int(os.getenv("REID_MIN_CROP_WIDTH", "32"))
REID_MIN_CROP_HEIGHT = int(os.getenv("REID_MIN_CROP_HEIGHT", "64"))
REID_TORCHREID_MODEL = os.getenv("REID_TORCHREID_MODEL", "osnet_x1_0")
REID_TORCHREID_MODEL_PATH = os.getenv("REID_TORCHREID_MODEL_PATH")

_extractor = None
_extractor_error = None
_extractor_lock = threading.Lock()
_last_samples = {}
_track_identity_cache = {}
_sample_lock = threading.Lock()


def _load_torchreid_extractor():
    global _extractor, _extractor_error

    if _extractor is not None or _extractor_error is not None:
        return _extractor

    with _extractor_lock:
        if _extractor is not None or _extractor_error is not None:
            return _extractor

        if not REID_TORCHREID_MODEL_PATH:
            _extractor_error = "REID_TORCHREID_MODEL_PATH is not configured"
            return None

        model_path = Path(REID_TORCHREID_MODEL_PATH)

        if not model_path.exists():
            _extractor_error = f"ReID model weights not found at {model_path}"
            return None

        try:
            from torchreid.utils import FeatureExtractor

            _extractor = FeatureExtractor(
                model_name=REID_TORCHREID_MODEL,
                model_path=str(model_path),
                device="cpu"
            )
            _extractor_error = None
        except Exception as error:
            _extractor = None
            _extractor_error = str(error)

        return _extractor


def _normalize(vector):
    array = np.asarray(vector, dtype=np.float32).reshape(-1)
    norm = float(np.linalg.norm(array))

    if norm == 0:
        return array

    return array / norm


def _fallback_embedding(crop):
    resized = cv2.resize(crop, (128, 256), interpolation=cv2.INTER_AREA)
    hsv = cv2.cvtColor(resized, cv2.COLOR_BGR2HSV)
    upper = hsv[:128, :, :]
    lower = hsv[128:, :, :]
    full_hist = cv2.calcHist([hsv], [0, 1], None, [24, 16], [0, 180, 0, 256])
    upper_hist = cv2.calcHist([upper], [0, 1], None, [16, 12], [0, 180, 0, 256])
    lower_hist = cv2.calcHist([lower], [0, 1], None, [16, 12], [0, 180, 0, 256])
    embedding = np.concatenate([
        _normalize(full_hist),
        _normalize(upper_hist),
        _normalize(lower_hist)
    ])
    return _normalize(embedding).astype(float).tolist()


def _embedding_from_crop(crop, snapshot_path: Path):
    extractor = _load_torchreid_extractor()

    if extractor is None:
        return _fallback_embedding(crop), "fallback-hsv"

    features = extractor([str(snapshot_path)])
    feature = features[0].detach().cpu().numpy()
    return _normalize(feature).astype(float).tolist(), f"torchreid:{REID_TORCHREID_MODEL}"


def _cosine_similarity(left, right):
    left_array = _normalize(left)
    right_array = _normalize(right)
    return float(np.dot(left_array, right_array))


def _active_match_threshold():
    return REID_MATCH_THRESHOLD if _extractor is not None else REID_FALLBACK_MATCH_THRESHOLD


def _find_match(db, embedding):
    best_identity = None
    best_similarity = None

    for identity in crud.get_identity_embeddings(db):
        centroid = json.loads(identity.centroid_embedding)
        similarity = _cosine_similarity(embedding, centroid)

        if best_similarity is None or similarity > best_similarity:
            best_identity = identity
            best_similarity = similarity

    if best_identity is not None and best_similarity is not None and best_similarity >= _active_match_threshold():
        return best_identity, best_similarity

    return None, best_similarity


def _get_cached_track_identity(db, camera_id: int, tracking_id: int | None, now: datetime):
    if tracking_id is None:
        return None

    cache_key = (camera_id, tracking_id)

    with _sample_lock:
        cached = _track_identity_cache.get(cache_key)

        if not cached:
            return None

        identity_id, last_seen = cached

        if (now - last_seen).total_seconds() > REID_TRACK_CACHE_SECONDS:
            del _track_identity_cache[cache_key]
            return None

        _track_identity_cache[cache_key] = (identity_id, now)

    return crud.get_person_identity(db, identity_id)


def _cache_track_identity(camera_id: int, tracking_id: int | None, identity_id: int, now: datetime):
    if tracking_id is None:
        return

    with _sample_lock:
        _track_identity_cache[(camera_id, tracking_id)] = (identity_id, now)


def _should_sample(camera_id: int, tracking_id: int | None, bbox: list[int], now: datetime):
    sample_key = (camera_id, tracking_id if tracking_id is not None else tuple(bbox))

    with _sample_lock:
        last_sampled = _last_samples.get(sample_key)

        if last_sampled and (now - last_sampled).total_seconds() < REID_SAMPLE_INTERVAL_SECONDS:
            return False

        _last_samples[sample_key] = now

    return True


def _crop_person(frame, bbox: list[int]):
    height, width = frame.shape[:2]
    x1, y1, x2, y2 = bbox
    x1 = max(0, min(width - 1, int(x1)))
    y1 = max(0, min(height - 1, int(y1)))
    x2 = max(0, min(width, int(x2)))
    y2 = max(0, min(height, int(y2)))

    if x2 <= x1 or y2 <= y1:
        return None

    if x2 - x1 < REID_MIN_CROP_WIDTH or y2 - y1 < REID_MIN_CROP_HEIGHT:
        return None

    return frame[y1:y2, x1:x2]


def process_person_detections(camera_id: int, frame, detections: list[dict]):
    now = datetime.now(timezone.utc)
    people = [detection for detection in detections if detection.get("class") == "person"]

    if not people:
        return []

    stored = []
    db = SessionLocal()

    try:
        for detection in people:
            bbox = detection["box"]
            tracking_id = detection.get("tracking_id")

            if not _should_sample(camera_id, tracking_id, bbox, now):
                continue

            crop = _crop_person(frame, bbox)

            if crop is None:
                continue

            camera_folder = REID_DIR / f"camera{camera_id}"
            camera_folder.mkdir(parents=True, exist_ok=True)
            timestamp = now.strftime("%Y%m%d_%H%M%S_%f")
            track_part = tracking_id if tracking_id is not None else "untracked"
            snapshot_path = camera_folder / f"{timestamp}_track{track_part}.jpg"
            cv2.imwrite(str(snapshot_path), crop)

            embedding, _ = _embedding_from_crop(crop, snapshot_path)
            identity = _get_cached_track_identity(db, camera_id, tracking_id, now)
            similarity = 1.0 if identity is not None else None

            if identity is None:
                identity, similarity = _find_match(db, embedding)

            if identity is None:
                identity = crud.create_person_identity(db, embedding)
                similarity = None
            else:
                _cache_track_identity(camera_id, tracking_id, identity.id, now)

            appearance = crud.create_person_appearance(
                db=db,
                identity_id=identity.id,
                camera_id=camera_id,
                tracking_id=tracking_id,
                event_time=now,
                snapshot=str(snapshot_path),
                bbox=bbox,
                embedding=embedding,
                similarity=similarity
            )
            crud.update_person_identity_centroid(db, identity, embedding)
            _cache_track_identity(camera_id, tracking_id, identity.id, now)
            stored.append(appearance)
    finally:
        db.close()

    return stored


def get_reid_status():
    extractor = _load_torchreid_extractor()

    return {
        "embedding_backend": f"torchreid:{REID_TORCHREID_MODEL}" if extractor is not None else "fallback-hsv",
        "torchreid_configured": bool(REID_TORCHREID_MODEL_PATH),
        "torchreid_loaded": extractor is not None,
        "torchreid_error": _extractor_error,
        "match_threshold": _active_match_threshold(),
        "torchreid_match_threshold": REID_MATCH_THRESHOLD,
        "fallback_match_threshold": REID_FALLBACK_MATCH_THRESHOLD,
        "sample_interval_seconds": REID_SAMPLE_INTERVAL_SECONDS,
        "track_cache_seconds": REID_TRACK_CACHE_SECONDS,
    }


def reset_reid_runtime():
    with _sample_lock:
        _last_samples.clear()
        _track_identity_cache.clear()

    shutil.rmtree(REID_DIR, ignore_errors=True)
