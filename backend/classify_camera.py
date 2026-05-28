from __future__ import annotations

import os
from pathlib import Path

import cv2
import requests
from ultralytics import YOLO

BASE_DIR = Path(__file__).resolve().parent
MODEL_PATH = Path(
    os.environ.get(
        "CLASSIFIER_MODEL_PATH",
        str(BASE_DIR / "runs" / "classify" / "grocery-classifier-public4" / "weights" / "best.pt"),
    )
)
CAMERA_INDEX = int(os.environ.get("CAMERA_INDEX", "0"))
CAMERA_WIDTH = int(os.environ.get("CAMERA_WIDTH", "640"))
CAMERA_HEIGHT = int(os.environ.get("CAMERA_HEIGHT", "480"))
CENTER_CROP_RATIO = float(os.environ.get("CENTER_CROP_RATIO", "0.65"))
MIN_CONFIDENCE = float(os.environ.get("CLASSIFIER_MIN_CONFIDENCE", "0.65"))
BACKGROUND_STRONG_CONFIDENCE = float(os.environ.get("CLASSIFIER_BACKGROUND_STRONG_CONFIDENCE", "0.90"))
BACKEND_URL = os.environ.get("BACKEND_URL", "http://127.0.0.1:5000").rstrip("/")
FRIDGE_ID = os.environ.get("FRIDGE_ID")


def center_crop(frame):
    height, width = frame.shape[:2]
    crop_width = int(width * CENTER_CROP_RATIO)
    crop_height = int(height * CENTER_CROP_RATIO)
    x1 = max(0, (width - crop_width) // 2)
    y1 = max(0, (height - crop_height) // 2)
    x2 = x1 + crop_width
    y2 = y1 + crop_height
    return frame[y1:y2, x1:x2], (x1, y1, x2, y2)


def choose_prediction(results):
    probs = results[0].probs
    if probs is None:
        return "No prediction", None

    top_indices = [int(index) for index in probs.top5]
    top_confidences = probs.top5conf.tolist()
    candidates = [(results[0].names[index], confidence) for index, confidence in zip(top_indices, top_confidences)]

    top_label, top_confidence = candidates[0]
    if top_confidence < MIN_CONFIDENCE:
        return "none", top_confidence

    if top_label == "background" and top_confidence < BACKGROUND_STRONG_CONFIDENCE:
        for label, confidence in candidates[1:]:
            if label != "background" and confidence >= MIN_CONFIDENCE:
                return label, confidence
        return "none", top_confidence

    return top_label, top_confidence


def encode_jpeg(image):
    success, buffer = cv2.imencode(".jpg", image)
    if not success:
        raise RuntimeError("Failed to encode camera frame.")
    return buffer.tobytes()


def upload_prediction(frame, cropped, label, confidence):
    if label in {"none", "background", "No prediction"}:
        print(f"Skipped upload: {label}")
        return

    data = {
        "label": label,
        "detected_name": label,
        "quantity": "1",
        "unit": "개",
    }
    if confidence is not None:
        data["confidence"] = f"{confidence:.4f}"
    if FRIDGE_ID:
        data["fridge_id"] = FRIDGE_ID

    files = {
        "image": ("camera.jpg", encode_jpeg(frame), "image/jpeg"),
        "crop_image": ("camera_crop.jpg", encode_jpeg(cropped), "image/jpeg"),
    }

    response = requests.post(f"{BACKEND_URL}/upload", data=data, files=files, timeout=10)
    response.raise_for_status()
    item = response.json()
    print(f"Uploaded: {item['display_name']} -> fridge {item['fridge_id']}")


def main() -> None:
    if not MODEL_PATH.exists():
        raise SystemExit(f"Model was not found: {MODEL_PATH}")

    model = YOLO(str(MODEL_PATH))
    cap = cv2.VideoCapture(CAMERA_INDEX)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_HEIGHT)

    if not cap.isOpened():
        raise SystemExit("Camera is not available.")

    while True:
        success, frame = cap.read()
        if not success:
            break

        cropped, (x1, y1, x2, y2) = center_crop(frame)
        results = model(cropped, verbose=False)

        label, confidence = choose_prediction(results)
        label_text = label if confidence is None else f"{label} {confidence:.2f}"

        preview = frame.copy()
        cv2.rectangle(preview, (x1, y1), (x2, y2), (0, 200, 0), 2)
        cv2.putText(
            preview,
            label_text,
            (20, 40),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.9,
            (0, 200, 0),
            2,
            cv2.LINE_AA,
        )
        cv2.imshow("Ingredient Classification", preview)
        key = cv2.waitKey(1)
        if key == ord("s"):
            try:
                upload_prediction(frame, cropped, label, confidence)
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
