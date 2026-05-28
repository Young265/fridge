from __future__ import annotations

import argparse
import os
import time
from dataclasses import dataclass
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_MODEL_PATH = BASE_DIR / "runs" / "classify" / "grocery-classifier-public4" / "weights" / "best.pt"

SKIP_LABELS = {"none", "background", "no prediction"}
cv2 = None


@dataclass
class Prediction:
    label: str
    confidence: float | None
    candidates: list[tuple[str, float]]


class OpenCVCamera:
    def __init__(self, camera_index: int, width: int, height: int) -> None:
        global cv2
        self.cap = cv2.VideoCapture(camera_index)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        if not self.cap.isOpened():
            raise RuntimeError(f"OpenCV camera is not available: index {camera_index}")

    def read(self):
        ok, frame = self.cap.read()
        if not ok:
            raise RuntimeError("Failed to read a camera frame.")
        return frame

    def close(self) -> None:
        self.cap.release()


class Picamera2Camera:
    def __init__(self, width: int, height: int) -> None:
        from picamera2 import Picamera2

        global cv2
        self.camera = Picamera2()
        config = self.camera.create_preview_configuration(
            main={"size": (width, height), "format": "RGB888"}
        )
        self.camera.configure(config)
        self.camera.start()
        time.sleep(1.0)

    def read(self):
        rgb = self.camera.capture_array()
        return cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)

    def close(self) -> None:
        self.camera.stop()


class ReedDoorSensor:
    def __init__(self, pin: int, open_level: str, bounce_time: float) -> None:
        from gpiozero import Button

        self.open_level = open_level
        self.switch = Button(pin, pull_up=True, bounce_time=bounce_time)

    def is_open(self) -> bool:
        if self.open_level == "high":
            return not self.switch.is_pressed
        return self.switch.is_pressed

    def wait_for_open(self, interval: float = 0.05) -> None:
        while not self.is_open():
            time.sleep(interval)

    def wait_for_close(self, interval: float = 0.05) -> None:
        while self.is_open():
            time.sleep(interval)


def make_camera(camera_backend: str, camera_index: int, width: int, height: int):
    global cv2
    if cv2 is None:
        import cv2 as cv2_module

        cv2 = cv2_module

    if camera_backend == "picamera2":
        return Picamera2Camera(width, height)
    if camera_backend == "opencv":
        return OpenCVCamera(camera_index, width, height)

    try:
        return Picamera2Camera(width, height)
    except Exception as error:
        print(f"Picamera2 unavailable, falling back to OpenCV: {error}")
        return OpenCVCamera(camera_index, width, height)


def center_crop(frame, ratio: float):
    height, width = frame.shape[:2]
    crop_width = int(width * ratio)
    crop_height = int(height * ratio)
    x1 = max(0, (width - crop_width) // 2)
    y1 = max(0, (height - crop_height) // 2)
    x2 = x1 + crop_width
    y2 = y1 + crop_height
    return frame[y1:y2, x1:x2]


def encode_jpeg(image) -> bytes:
    ok, buffer = cv2.imencode(".jpg", image)
    if not ok:
        raise RuntimeError("Failed to encode a camera frame.")
    return buffer.tobytes()


def choose_prediction(
    results,
    min_confidence: float,
    background_strong_confidence: float,
) -> Prediction:
    probs = results[0].probs
    if probs is None:
        return Prediction("no prediction", None, [])

    top_indices = [int(index) for index in probs.top5]
    top_confidences = [float(value) for value in probs.top5conf.tolist()]
    candidates = [
        (results[0].names[index], confidence)
        for index, confidence in zip(top_indices, top_confidences)
    ]

    top_label, top_confidence = candidates[0]
    if top_confidence < min_confidence:
        return Prediction("none", top_confidence, candidates)

    if top_label == "background" and top_confidence < background_strong_confidence:
        for label, confidence in candidates[1:]:
            if label != "background" and confidence >= min_confidence:
                return Prediction(label, confidence, candidates)
        return Prediction("none", top_confidence, candidates)

    return Prediction(top_label, top_confidence, candidates)


def check_backend(upload_url: str) -> None:
    import requests

    health_url = upload_url.rsplit("/", 1)[0] + "/health"
    response = requests.get(health_url, timeout=5)
    response.raise_for_status()


def upload_prediction(
    upload_url: str,
    fridge_id: str | None,
    frame,
    crop,
    prediction: Prediction,
) -> dict:
    import requests

    data = {
        "label": prediction.label,
        "detected_name": prediction.label,
        "quantity": "1",
        "unit": "ea",
    }
    if prediction.confidence is not None:
        data["confidence"] = f"{prediction.confidence:.4f}"
    if fridge_id:
        data["fridge_id"] = fridge_id

    files = {
        "image": ("pi_camera.jpg", encode_jpeg(frame), "image/jpeg"),
        "crop_image": ("pi_camera_crop.jpg", encode_jpeg(crop), "image/jpeg"),
    }
    response = requests.post(upload_url, data=data, files=files, timeout=15)
    response.raise_for_status()
    return response.json()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Read one ingredient from a Raspberry Pi camera and upload it to the fridge backend."
    )
    parser.add_argument("--backend-url", default=os.environ.get("BACKEND_URL", "http://127.0.0.1:5000"))
    parser.add_argument("--fridge-id", default=os.environ.get("FRIDGE_ID"))
    parser.add_argument("--model", default=os.environ.get("CLASSIFIER_MODEL_PATH", str(DEFAULT_MODEL_PATH)))
    parser.add_argument("--camera-backend", choices=["auto", "picamera2", "opencv"], default=os.environ.get("CAMERA_BACKEND", "auto"))
    parser.add_argument("--camera-index", type=int, default=int(os.environ.get("CAMERA_INDEX", "0")))
    parser.add_argument("--width", type=int, default=int(os.environ.get("CAMERA_WIDTH", "640")))
    parser.add_argument("--height", type=int, default=int(os.environ.get("CAMERA_HEIGHT", "480")))
    parser.add_argument("--crop-ratio", type=float, default=float(os.environ.get("CENTER_CROP_RATIO", "0.65")))
    parser.add_argument("--min-confidence", type=float, default=float(os.environ.get("CLASSIFIER_MIN_CONFIDENCE", "0.65")))
    parser.add_argument("--background-strong-confidence", type=float, default=float(os.environ.get("CLASSIFIER_BACKGROUND_STRONG_CONFIDENCE", "0.90")))
    parser.add_argument("--interval", type=float, default=float(os.environ.get("SCAN_INTERVAL_SECONDS", "1.0")))
    parser.add_argument("--cooldown", type=float, default=float(os.environ.get("UPLOAD_COOLDOWN_SECONDS", "20.0")))
    parser.add_argument("--stable-frames", type=int, default=int(os.environ.get("STABLE_FRAMES", "3")))
    parser.add_argument("--scan-timeout", type=float, default=float(os.environ.get("SCAN_TIMEOUT_SECONDS", "20.0")))
    parser.add_argument("--trigger", choices=["continuous", "reed"], default=os.environ.get("TRIGGER_MODE", "continuous"))
    parser.add_argument("--reed-pin", type=int, default=int(os.environ.get("REED_PIN", "17")))
    parser.add_argument("--reed-open-level", choices=["high", "low"], default=os.environ.get("REED_OPEN_LEVEL", "high"))
    parser.add_argument("--reed-bounce-time", type=float, default=float(os.environ.get("REED_BOUNCE_TIME", "0.1")))
    parser.add_argument("--post-open-delay", type=float, default=float(os.environ.get("POST_OPEN_DELAY_SECONDS", "0.0")))
    parser.add_argument("--once", action="store_true", help="Upload the first stable prediction and exit.")
    parser.add_argument("--dry-run", action="store_true", help="Classify frames without uploading.")
    return parser.parse_args()


def scan_until_upload(camera, model, args: argparse.Namespace, upload_url: str) -> bool:
    last_label: str | None = None
    stable_count = 0
    started_at = time.time()

    while True:
        if args.scan_timeout > 0 and time.time() - started_at > args.scan_timeout:
            print("Scan timed out without an upload.")
            return False

        frame = camera.read()
        crop = center_crop(frame, args.crop_ratio)
        results = model(crop, verbose=False)
        prediction = choose_prediction(
            results,
            args.min_confidence,
            args.background_strong_confidence,
        )

        confidence_text = "n/a" if prediction.confidence is None else f"{prediction.confidence:.2f}"
        print(f"Read: {prediction.label} ({confidence_text})")

        if prediction.label == last_label:
            stable_count += 1
        else:
            last_label = prediction.label
            stable_count = 1

        is_uploadable = prediction.label.lower() not in SKIP_LABELS
        is_stable = stable_count >= args.stable_frames

        if is_uploadable and is_stable:
            if args.dry_run:
                print(f"Dry run upload skipped: {prediction.label}")
            else:
                item = upload_prediction(upload_url, args.fridge_id, frame, crop, prediction)
                print(
                    f"Uploaded: {item['display_name']} "
                    f"confidence={item.get('confidence')} fridge={item['fridge_id']}"
                )
            return True

        time.sleep(args.interval)


def run_continuous(model, args: argparse.Namespace, upload_url: str) -> None:
    camera = make_camera(args.camera_backend, args.camera_index, args.width, args.height)
    print(f"Camera started. Upload target: {upload_url}")

    last_label: str | None = None
    stable_count = 0
    last_uploaded_label: str | None = None
    last_uploaded_at = 0.0

    try:
        while True:
            frame = camera.read()
            crop = center_crop(frame, args.crop_ratio)
            results = model(crop, verbose=False)
            prediction = choose_prediction(
                results,
                args.min_confidence,
                args.background_strong_confidence,
            )

            confidence_text = "n/a" if prediction.confidence is None else f"{prediction.confidence:.2f}"
            print(f"Read: {prediction.label} ({confidence_text})")

            if prediction.label == last_label:
                stable_count += 1
            else:
                last_label = prediction.label
                stable_count = 1

            current_time = time.time()
            is_uploadable = prediction.label.lower() not in SKIP_LABELS
            is_stable = stable_count >= args.stable_frames
            cooldown_elapsed = current_time - last_uploaded_at >= args.cooldown
            label_changed = prediction.label != last_uploaded_label

            if is_uploadable and is_stable and (cooldown_elapsed or label_changed):
                if args.dry_run:
                    print(f"Dry run upload skipped: {prediction.label}")
                else:
                    item = upload_prediction(upload_url, args.fridge_id, frame, crop, prediction)
                    print(
                        f"Uploaded: {item['display_name']} "
                        f"confidence={item.get('confidence')} fridge={item['fridge_id']}"
                    )
                last_uploaded_label = prediction.label
                last_uploaded_at = current_time
                if args.once:
                    return

            time.sleep(args.interval)
    finally:
        camera.close()


def run_reed_triggered(model, args: argparse.Namespace, upload_url: str) -> None:
    sensor = ReedDoorSensor(args.reed_pin, args.reed_open_level, args.reed_bounce_time)
    print(
        f"Waiting for door open on GPIO {args.reed_pin} "
        f"(open level: {args.reed_open_level})."
    )

    while True:
        sensor.wait_for_open()
        print("Door opened. Starting camera scan.")
        if args.post_open_delay > 0:
            time.sleep(args.post_open_delay)

        camera = make_camera(args.camera_backend, args.camera_index, args.width, args.height)
        try:
            scan_until_upload(camera, model, args, upload_url)
        finally:
            camera.close()
            print("Camera stopped. Waiting for door close.")

        if args.once:
            return

        sensor.wait_for_close()
        print("Door closed. Ready for next open event.")
        time.sleep(args.cooldown)


def main() -> None:
    args = parse_args()
    model_path = Path(args.model).expanduser().resolve()
    upload_url = args.backend_url.rstrip("/") + "/upload"

    if not model_path.exists():
        raise SystemExit(f"Model was not found: {model_path}")
    if not args.dry_run:
        check_backend(upload_url)

    from ultralytics import YOLO

    model = YOLO(str(model_path))
    if args.trigger == "reed":
        run_reed_triggered(model, args, upload_url)
    else:
        run_continuous(model, args, upload_url)


if __name__ == "__main__":
    main()
