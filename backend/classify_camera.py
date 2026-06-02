from __future__ import annotations

import os
from pathlib import Path

import cv2
import requests
from ultralytics import YOLO

import pi_fridge_camera as bridge

BASE_DIR = Path(__file__).resolve().parent
MODEL_PATH = Path(
    os.environ.get(
        "CLASSIFIER_MODEL_PATH",
        str(BASE_DIR / "runs" / "classify" / "grocery-classifier-public4" / "weights" / "best.pt"),
    )
)
DETECTOR_MODEL_PATH = os.environ.get("DETECTOR_MODEL_PATH", str(BASE_DIR / "yolov8n.pt"))
CAMERA_INDEX = int(os.environ.get("CAMERA_INDEX", "0"))
CAMERA_WIDTH = int(os.environ.get("CAMERA_WIDTH", "640"))
CAMERA_HEIGHT = int(os.environ.get("CAMERA_HEIGHT", "480"))
CAMERA_FPS = float(os.environ.get("CAMERA_FPS", "30"))
BACKEND_URL = os.environ.get("BACKEND_URL", "http://127.0.0.1:5000").rstrip("/")
FRIDGE_ID = os.environ.get("FRIDGE_ID")


def env_flag(name: str, default: str = "0") -> bool:
    return os.environ.get(name, default).strip().lower() in {"1", "true", "yes"}


SETTINGS = bridge.ScanSettings(
    crop_ratio=float(os.environ.get("CENTER_CROP_RATIO", "0.65")),
    min_confidence=float(os.environ.get("CLASSIFIER_MIN_CONFIDENCE", "0.65")),
    background_strong_confidence=float(os.environ.get("CLASSIFIER_BACKGROUND_STRONG_CONFIDENCE", "0.90")),
    detection_confidence=float(os.environ.get("DETECTION_CONFIDENCE", "0.30")),
    detection_imgsz=int(os.environ.get("DETECTION_IMGSZ", "640")),
    crop_padding_ratio=float(os.environ.get("CROP_PADDING_RATIO", "0.15")),
    min_crop_padding=int(os.environ.get("MIN_CROP_PADDING", "24")),
    max_crop_padding=int(os.environ.get("MAX_CROP_PADDING", "96")),
    contour_min_area_ratio=float(os.environ.get("CONTOUR_MIN_AREA_RATIO", "0.01")),
    contour_max_area_ratio=float(os.environ.get("CONTOUR_MAX_AREA_RATIO", "0.85")),
    max_candidates=int(os.environ.get("MAX_CANDIDATES", "4")),
    use_contour_proposals=not env_flag("DISABLE_CONTOUR_PROPOSALS"),
)


def draw_candidates(frame, candidates: list[bridge.ClassifiedCandidate]):
    preview = frame.copy()
    for candidate in candidates:
        x1, y1, x2, y2 = candidate.coords
        prediction = candidate.prediction
        is_uploadable = bridge.is_uploadable(prediction)
        color = (0, 200, 0) if is_uploadable else (0, 165, 255)
        confidence = "n/a" if prediction.confidence is None else f"{prediction.confidence:.2f}"
        label_text = f"{prediction.label} {confidence} [{candidate.source}]"
        cv2.rectangle(preview, (x1, y1), (x2, y2), color, 2)
        cv2.putText(
            preview,
            label_text,
            (x1, max(24, y1 - 10)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            color,
            2,
            cv2.LINE_AA,
        )
    return preview


def main() -> None:
    if not MODEL_PATH.exists():
        raise SystemExit(f"Classifier model was not found: {MODEL_PATH}")

    bridge.cv2 = cv2
    classifier = YOLO(str(MODEL_PATH))
    detector = bridge.load_detector(DETECTOR_MODEL_PATH, env_flag("DISABLE_DETECTOR"))
    cap = cv2.VideoCapture(CAMERA_INDEX)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_HEIGHT)
    cap.set(cv2.CAP_PROP_FPS, CAMERA_FPS)

    if not cap.isOpened():
        raise SystemExit("Camera is not available.")

    print("Dynamic preview started. Press s to upload recognized boxes or q to quit.")
    while True:
        success, frame = cap.read()
        if not success:
            break

        candidates = bridge.classify_frame(frame, detector, classifier, SETTINGS)
        cv2.imshow("Ingredient Classification", draw_candidates(frame, candidates))
        key = cv2.waitKey(1)
        if key == ord("s"):
            try:
                bridge.upload_candidates(
                    f"{BACKEND_URL}/upload",
                    FRIDGE_ID,
                    frame,
                    candidates,
                    dry_run=False,
                )
            except requests.RequestException as exc:
                print(f"Upload failed: {exc}")
            except RuntimeError as exc:
                print(str(exc))
        if key == ord("q"):
            break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
