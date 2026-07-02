from __future__ import annotations

import argparse
import os
import socket
import threading
import time
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_MODEL_PATH = BASE_DIR / "runs" / "classify" / "grocery-classifier-public4" / "weights" / "best.pt"
DEFAULT_DETECTOR_MODEL_PATH = BASE_DIR / "yolov8n.pt"

SKIP_LABELS = {"none", "background", "no prediction"}
EXCLUDED_DETECTOR_LABELS = {"person"}
TRUSTED_DETECTOR_LABELS = {
    "apple",
    "banana",
    "broccoli",
    "cake",
    "carrot",
    "donut",
    "hot_dog",
    "orange",
    "pizza",
    "sandwich",
}
cv2 = None


def env_flag(name: str, default: str = "0") -> bool:
    return os.environ.get(name, default).strip().lower() in {"1", "true", "yes", "on"}


@dataclass
class Prediction:
    label: str
    confidence: float | None
    candidates: list[tuple[str, float]]


@dataclass
class ScanSettings:
    crop_ratio: float
    min_confidence: float
    background_strong_confidence: float
    detection_confidence: float
    detection_imgsz: int
    crop_padding_ratio: float
    min_crop_padding: int
    max_crop_padding: int
    contour_min_area_ratio: float
    contour_max_area_ratio: float
    max_candidates: int
    use_contour_proposals: bool


@dataclass
class CropCandidate:
    crop: object
    coords: tuple[int, int, int, int]
    source: str
    source_confidence: float | None = None
    detector_label: str | None = None


@dataclass
class ClassifiedCandidate:
    crop: object
    coords: tuple[int, int, int, int]
    source: str
    prediction: Prediction


class OpenCVCamera:
    def __init__(self, camera_index: int, width: int, height: int, fps: float) -> None:
        global cv2
        self.cap = cv2.VideoCapture(camera_index)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        self.cap.set(cv2.CAP_PROP_FPS, fps)
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
    def __init__(self, width: int, height: int, fps: float) -> None:
        from picamera2 import Picamera2

        global cv2
        self.camera = Picamera2()
        config = self.camera.create_preview_configuration(
            main={"size": (width, height), "format": "RGB888"},
            controls={"FrameRate": fps},
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


def make_camera(camera_backend: str, camera_index: int, width: int, height: int, fps: float):
    global cv2
    if cv2 is None:
        import cv2 as cv2_module

        cv2 = cv2_module

    if camera_backend == "picamera2":
        return Picamera2Camera(width, height, fps)
    if camera_backend == "opencv":
        return OpenCVCamera(camera_index, width, height, fps)

    try:
        return Picamera2Camera(width, height, fps)
    except Exception as error:
        print(f"Picamera2 unavailable, falling back to OpenCV: {error}")
        return OpenCVCamera(camera_index, width, height, fps)


def center_crop_box(frame, ratio: float) -> tuple[int, int, int, int]:
    height, width = frame.shape[:2]
    crop_width = int(width * ratio)
    crop_height = int(height * ratio)
    x1 = max(0, (width - crop_width) // 2)
    y1 = max(0, (height - crop_height) // 2)
    x2 = min(width, x1 + crop_width)
    y2 = min(height, y1 + crop_height)
    return x1, y1, x2, y2


def center_crop_candidate(frame, ratio: float) -> CropCandidate:
    x1, y1, x2, y2 = center_crop_box(frame, ratio)
    return CropCandidate(
        crop=frame[y1:y2, x1:x2],
        coords=(x1, y1, x2, y2),
        source="center-fallback",
    )


def expand_box(
    frame,
    coords: tuple[int, int, int, int],
    settings: ScanSettings,
) -> tuple[int, int, int, int]:
    height, width = frame.shape[:2]
    x1, y1, x2, y2 = coords
    box_width = max(1, x2 - x1)
    box_height = max(1, y2 - y1)
    padding = max(
        settings.min_crop_padding,
        int(max(box_width, box_height) * settings.crop_padding_ratio),
    )
    padding = min(padding, settings.max_crop_padding)
    return (
        max(0, x1 - padding),
        max(0, y1 - padding),
        min(width, x2 + padding),
        min(height, y2 + padding),
    )


def make_crop_candidate(
    frame,
    coords: tuple[int, int, int, int],
    source: str,
    settings: ScanSettings,
    source_confidence: float | None = None,
    detector_label: str | None = None,
) -> CropCandidate | None:
    x1, y1, x2, y2 = expand_box(frame, coords, settings)
    crop = frame[y1:y2, x1:x2]
    if crop.size == 0:
        return None
    return CropCandidate(
        crop=crop,
        coords=(x1, y1, x2, y2),
        source=source,
        source_confidence=source_confidence,
        detector_label=detector_label,
    )


def box_overlap_ratio(
    first: tuple[int, int, int, int],
    second: tuple[int, int, int, int],
) -> float:
    first_x1, first_y1, first_x2, first_y2 = first
    second_x1, second_y1, second_x2, second_y2 = second
    intersection_width = max(0, min(first_x2, second_x2) - max(first_x1, second_x1))
    intersection_height = max(0, min(first_y2, second_y2) - max(first_y1, second_y1))
    intersection_area = intersection_width * intersection_height
    first_area = max(1, (first_x2 - first_x1) * (first_y2 - first_y1))
    second_area = max(1, (second_x2 - second_x1) * (second_y2 - second_y1))
    return intersection_area / min(first_area, second_area)


def append_non_overlapping(
    candidates: list[CropCandidate],
    candidate: CropCandidate | None,
    max_candidates: int,
) -> None:
    if candidate is None or len(candidates) >= max_candidates:
        return
    if any(box_overlap_ratio(existing.coords, candidate.coords) >= 0.65 for existing in candidates):
        return
    candidates.append(candidate)


def detector_crop_candidates(
    frame,
    detector,
    settings: ScanSettings,
) -> list[CropCandidate]:
    if detector is None:
        return []

    results = detector(frame, imgsz=settings.detection_imgsz, verbose=False)
    candidates = []
    for box in results[0].boxes:
        confidence = float(box.conf[0].item())
        if confidence < settings.detection_confidence:
            continue
        class_id = int(box.cls[0].item())
        label = detector.names[class_id]
        if label in EXCLUDED_DETECTOR_LABELS:
            continue
        normalized_label = label.strip().lower().replace("-", " ").replace("_", " ")
        normalized_label = normalized_label.replace("hot dog", "hot_dog").replace(" ", "_")
        coords = tuple(int(value) for value in box.xyxy[0].tolist())
        append_non_overlapping(
            candidates,
            make_crop_candidate(
                frame,
                coords,
                f"detector:{label}",
                settings,
                confidence,
                normalized_label,
            ),
            settings.max_candidates,
        )
    return candidates


def contour_crop_candidates(frame, settings: ScanSettings) -> list[CropCandidate]:
    if not settings.use_contour_proposals:
        return []

    height, width = frame.shape[:2]
    frame_area = height * width
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blurred, 60, 150)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (7, 7))
    mask = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel, iterations=2)
    mask = cv2.dilate(mask, kernel, iterations=1)
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    boxes = []
    for contour in contours:
        x, y, box_width, box_height = cv2.boundingRect(contour)
        area_ratio = (box_width * box_height) / frame_area
        if area_ratio < settings.contour_min_area_ratio:
            continue
        if area_ratio > settings.contour_max_area_ratio:
            continue
        boxes.append((box_width * box_height, (x, y, x + box_width, y + box_height)))

    candidates = []
    for _, coords in sorted(boxes, reverse=True):
        append_non_overlapping(
            candidates,
            make_crop_candidate(frame, coords, "contour", settings),
            settings.max_candidates,
        )
    return candidates


def collect_crop_candidates(
    frame,
    detector,
    settings: ScanSettings,
) -> list[CropCandidate]:
    candidates = detector_crop_candidates(frame, detector, settings)
    for contour_candidate in contour_crop_candidates(frame, settings):
        append_non_overlapping(candidates, contour_candidate, settings.max_candidates)
    if not candidates:
        candidates.append(center_crop_candidate(frame, settings.crop_ratio))
    return candidates


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


def is_uploadable(prediction: Prediction) -> bool:
    return prediction.label.lower() not in SKIP_LABELS


def classify_frame(
    frame,
    detector,
    classifier,
    settings: ScanSettings,
) -> list[ClassifiedCandidate]:
    crop_candidates = collect_crop_candidates(frame, detector, settings)
    classified = [
        ClassifiedCandidate(
            crop=candidate.crop,
            coords=candidate.coords,
            source=candidate.source,
            prediction=classify_crop_candidate(candidate, classifier, settings),
        )
        for candidate in crop_candidates
    ]

    if any(is_uploadable(candidate.prediction) for candidate in classified):
        return classified
    if any(candidate.source == "center-fallback" for candidate in classified):
        return classified

    fallback = center_crop_candidate(frame, settings.crop_ratio)
    classified.append(
        ClassifiedCandidate(
            crop=fallback.crop,
            coords=fallback.coords,
            source=fallback.source,
            prediction=choose_prediction(
                classifier(fallback.crop, verbose=False),
                settings.min_confidence,
                settings.background_strong_confidence,
            ),
        )
    )
    return classified


def classify_crop_candidate(
    candidate: CropCandidate,
    classifier,
    settings: ScanSettings,
) -> Prediction:
    if (
        candidate.detector_label in TRUSTED_DETECTOR_LABELS
        and candidate.source_confidence is not None
    ):
        return Prediction(
            candidate.detector_label,
            candidate.source_confidence,
            [(candidate.detector_label, candidate.source_confidence)],
        )
    return choose_prediction(
        classifier(candidate.crop, verbose=False),
        settings.min_confidence,
        settings.background_strong_confidence,
    )


def uploadable_candidates(
    candidates: list[ClassifiedCandidate],
) -> list[ClassifiedCandidate]:
    return [candidate for candidate in candidates if is_uploadable(candidate.prediction)]


def prediction_signature(
    candidates: list[ClassifiedCandidate],
) -> tuple[str, ...]:
    return tuple(sorted(candidate.prediction.label for candidate in uploadable_candidates(candidates)))


def format_candidates(candidates: list[ClassifiedCandidate]) -> str:
    return ", ".join(
        f"{candidate.prediction.label} "
        f"({'n/a' if candidate.prediction.confidence is None else f'{candidate.prediction.confidence:.2f}'}) "
        f"[{candidate.source}]"
        for candidate in candidates
    )


def draw_preview_frame(
    frame,
    candidates: list[ClassifiedCandidate] | None = None,
    status: str | None = None,
):
    preview = frame.copy()
    if candidates:
        for candidate in candidates:
            x1, y1, x2, y2 = candidate.coords
            prediction = candidate.prediction
            is_candidate_uploadable = is_uploadable(prediction)
            color = (0, 200, 0) if is_candidate_uploadable else (0, 165, 255)
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

    if status:
        cv2.rectangle(preview, (0, 0), (preview.shape[1], 34), (0, 0, 0), -1)
        cv2.putText(
            preview,
            status,
            (10, 23),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.65,
            (255, 255, 255),
            2,
            cv2.LINE_AA,
        )
    return preview


class PreviewStreamer:
    def __init__(self, host: str, port: int, jpeg_quality: int) -> None:
        self.host = host
        self.port = port
        self.jpeg_quality = jpeg_quality
        self.condition = threading.Condition()
        self.latest_jpeg: bytes | None = None
        self.frame_id = 0
        self.server: ThreadingHTTPServer | None = None
        self.thread: threading.Thread | None = None

    def start(self) -> None:
        streamer = self

        class PreviewHandler(BaseHTTPRequestHandler):
            def do_GET(self):
                if self.path in {"/", "/index.html"}:
                    self.send_response(200)
                    self.send_header("Content-Type", "text/html; charset=utf-8")
                    self.end_headers()
                    self.wfile.write(
                        b"<!doctype html><html><head><title>Fridge Camera</title>"
                        b"<style>body{margin:0;background:#111;color:#eee;font-family:sans-serif;}"
                        b"img{display:block;max-width:100vw;max-height:100vh;margin:auto;}</style>"
                        b"</head><body><img src='/stream.mjpg'></body></html>"
                    )
                    return

                if self.path.startswith("/snapshot.jpg"):
                    with streamer.condition:
                        jpeg = streamer.latest_jpeg
                    if jpeg is None:
                        self.send_response(503)
                        self.end_headers()
                        return
                    self.send_response(200)
                    self.send_header("Content-Type", "image/jpeg")
                    self.send_header("Content-Length", str(len(jpeg)))
                    self.end_headers()
                    self.wfile.write(jpeg)
                    return

                if not self.path.startswith("/stream.mjpg"):
                    self.send_response(404)
                    self.end_headers()
                    return

                self.send_response(200)
                self.send_header("Age", "0")
                self.send_header("Cache-Control", "no-cache, private")
                self.send_header("Pragma", "no-cache")
                self.send_header("Content-Type", "multipart/x-mixed-replace; boundary=frame")
                self.end_headers()

                last_seen_frame_id = -1
                while True:
                    with streamer.condition:
                        streamer.condition.wait_for(
                            lambda: streamer.frame_id != last_seen_frame_id,
                            timeout=5.0,
                        )
                        jpeg = streamer.latest_jpeg
                        last_seen_frame_id = streamer.frame_id
                    if jpeg is None:
                        continue
                    try:
                        self.wfile.write(b"--frame\r\n")
                        self.wfile.write(b"Content-Type: image/jpeg\r\n")
                        self.wfile.write(f"Content-Length: {len(jpeg)}\r\n\r\n".encode("ascii"))
                        self.wfile.write(jpeg)
                        self.wfile.write(b"\r\n")
                    except (BrokenPipeError, ConnectionResetError):
                        return

            def log_message(self, _format, *_args):
                return

        self.server = ThreadingHTTPServer((self.host, self.port), PreviewHandler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        display_host = self.host
        if display_host in {"0.0.0.0", ""}:
            display_host = local_ip_hint()
        print(f"Preview stream: http://{display_host}:{self.port}/")

    def update(
        self,
        frame,
        candidates: list[ClassifiedCandidate] | None = None,
        status: str | None = None,
    ) -> None:
        preview = draw_preview_frame(frame, candidates, status)
        ok, buffer = cv2.imencode(
            ".jpg",
            preview,
            [int(cv2.IMWRITE_JPEG_QUALITY), self.jpeg_quality],
        )
        if not ok:
            return
        with self.condition:
            self.latest_jpeg = buffer.tobytes()
            self.frame_id += 1
            self.condition.notify_all()

    def close(self) -> None:
        if self.server is not None:
            self.server.shutdown()
            self.server.server_close()


def local_ip_hint() -> str:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(("8.8.8.8", 80))
            return sock.getsockname()[0]
    except OSError:
        return "<raspberry-pi-ip>"


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


def consume_prediction(
    consume_url: str,
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
    response = requests.post(consume_url, data=data, files=files, timeout=15)
    response.raise_for_status()
    return response.json()


def upload_candidates(
    upload_url: str,
    fridge_id: str | None,
    frame,
    candidates: list[ClassifiedCandidate],
    dry_run: bool,
) -> None:
    for candidate in uploadable_candidates(candidates):
        prediction = candidate.prediction
        if dry_run:
            print(f"Dry run upload skipped: {prediction.label} [{candidate.source}]")
            continue
        item = upload_prediction(upload_url, fridge_id, frame, candidate.crop, prediction)
        print(
            f"Uploaded: {item['display_name']} "
            f"confidence={item.get('confidence')} fridge={item['fridge_id']} "
            f"source={candidate.source}"
        )


def consume_candidates(
    consume_url: str,
    fridge_id: str | None,
    frame,
    candidates: list[ClassifiedCandidate],
    dry_run: bool,
) -> None:
    for candidate in uploadable_candidates(candidates):
        prediction = candidate.prediction
        if dry_run:
            print(f"Dry run consume skipped: {prediction.label} [{candidate.source}]")
            continue
        result = consume_prediction(consume_url, fridge_id, frame, candidate.crop, prediction)
        if result.get("consumed"):
            item = result.get("item") or {}
            deleted = " deleted" if result.get("deleted") else ""
            print(
                f"Consumed: {item.get('display_name', prediction.label)} "
                f"remaining={result.get('remaining_quantity')}{deleted} "
                f"source={candidate.source}"
            )
        else:
            print(
                f"Consume skipped: {prediction.label} "
                f"reason={result.get('reason', 'unknown')} source={candidate.source}"
            )


def apply_candidates(
    action: str,
    action_url: str,
    fridge_id: str | None,
    frame,
    candidates: list[ClassifiedCandidate],
    dry_run: bool,
) -> None:
    if action == "consume":
        consume_candidates(action_url, fridge_id, frame, candidates, dry_run)
        return
    upload_candidates(action_url, fridge_id, frame, candidates, dry_run)


def discard_camera_frames(camera, count: int) -> None:
    for _ in range(max(0, count)):
        camera.read()


def scan_settings(args: argparse.Namespace) -> ScanSettings:
    return ScanSettings(
        crop_ratio=args.crop_ratio,
        min_confidence=args.min_confidence,
        background_strong_confidence=args.background_strong_confidence,
        detection_confidence=args.detection_confidence,
        detection_imgsz=args.detection_imgsz,
        crop_padding_ratio=args.crop_padding_ratio,
        min_crop_padding=args.min_crop_padding,
        max_crop_padding=args.max_crop_padding,
        contour_min_area_ratio=args.contour_min_area_ratio,
        contour_max_area_ratio=args.contour_max_area_ratio,
        max_candidates=args.max_candidates,
        use_contour_proposals=not args.disable_contour_proposals,
    )


def load_detector(model_path: str, disabled: bool = False):
    if disabled:
        print("Dynamic YOLO detector disabled. Using contour proposals and center fallback.")
        return None

    detector_path = Path(model_path).expanduser().resolve()
    if not detector_path.exists():
        print(f"Detector model was not found: {detector_path}")
        print("Using contour proposals and center fallback.")
        return None

    from ultralytics import YOLO

    print(f"Loaded dynamic detector: {detector_path}")
    return YOLO(str(detector_path))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Detect, classify and upload ingredients from a Raspberry Pi camera."
    )
    parser.add_argument("--backend-url", default=os.environ.get("BACKEND_URL", "http://127.0.0.1:5000"))
    parser.add_argument("--fridge-id", default=os.environ.get("FRIDGE_ID"))
    parser.add_argument("--model", default=os.environ.get("CLASSIFIER_MODEL_PATH", str(DEFAULT_MODEL_PATH)))
    parser.add_argument("--detector-model", default=os.environ.get("DETECTOR_MODEL_PATH", str(DEFAULT_DETECTOR_MODEL_PATH)))
    parser.add_argument("--disable-detector", action="store_true")
    parser.add_argument("--camera-backend", choices=["auto", "picamera2", "opencv"], default=os.environ.get("CAMERA_BACKEND", "auto"))
    parser.add_argument("--camera-index", type=int, default=int(os.environ.get("CAMERA_INDEX", "0")))
    parser.add_argument("--width", type=int, default=int(os.environ.get("CAMERA_WIDTH", "640")))
    parser.add_argument("--height", type=int, default=int(os.environ.get("CAMERA_HEIGHT", "480")))
    parser.add_argument("--fps", type=float, default=float(os.environ.get("CAMERA_FPS", "30")))
    parser.add_argument("--crop-ratio", type=float, default=float(os.environ.get("CENTER_CROP_RATIO", "0.65")))
    parser.add_argument("--min-confidence", type=float, default=float(os.environ.get("CLASSIFIER_MIN_CONFIDENCE", "0.65")))
    parser.add_argument("--background-strong-confidence", type=float, default=float(os.environ.get("CLASSIFIER_BACKGROUND_STRONG_CONFIDENCE", "0.90")))
    parser.add_argument("--detection-confidence", type=float, default=float(os.environ.get("DETECTION_CONFIDENCE", "0.30")))
    parser.add_argument("--detection-imgsz", type=int, default=int(os.environ.get("DETECTION_IMGSZ", "640")))
    parser.add_argument("--crop-padding-ratio", type=float, default=float(os.environ.get("CROP_PADDING_RATIO", "0.15")))
    parser.add_argument("--min-crop-padding", type=int, default=int(os.environ.get("MIN_CROP_PADDING", "24")))
    parser.add_argument("--max-crop-padding", type=int, default=int(os.environ.get("MAX_CROP_PADDING", "96")))
    parser.add_argument("--contour-min-area-ratio", type=float, default=float(os.environ.get("CONTOUR_MIN_AREA_RATIO", "0.01")))
    parser.add_argument("--contour-max-area-ratio", type=float, default=float(os.environ.get("CONTOUR_MAX_AREA_RATIO", "0.85")))
    parser.add_argument("--max-candidates", type=int, default=int(os.environ.get("MAX_CANDIDATES", "4")))
    parser.add_argument("--disable-contour-proposals", action="store_true")
    parser.add_argument("--interval", type=float, default=float(os.environ.get("SCAN_INTERVAL_SECONDS", "1.0")))
    parser.add_argument("--cooldown", type=float, default=float(os.environ.get("UPLOAD_COOLDOWN_SECONDS", "20.0")))
    parser.add_argument("--stable-frames", type=int, default=int(os.environ.get("STABLE_FRAMES", "3")))
    parser.add_argument("--scan-timeout", type=float, default=float(os.environ.get("SCAN_TIMEOUT_SECONDS", "20.0")))
    parser.add_argument("--trigger", choices=["continuous", "reed"], default=os.environ.get("TRIGGER_MODE", "continuous"))
    parser.add_argument("--reed-pin", type=int, default=int(os.environ.get("REED_PIN", "17")))
    parser.add_argument("--reed-open-level", choices=["high", "low"], default=os.environ.get("REED_OPEN_LEVEL", "high"))
    parser.add_argument("--reed-bounce-time", type=float, default=float(os.environ.get("REED_BOUNCE_TIME", "0.1")))
    parser.add_argument("--reed-camera-mode", choices=["on-demand", "warm"], default=os.environ.get("REED_CAMERA_MODE", "on-demand"))
    parser.add_argument("--reed-workflow", choices=["add-on-open", "add-on-open-consume-on-close"], default=os.environ.get("REED_WORKFLOW", "add-on-open"))
    parser.add_argument("--warm-camera", action="store_true", default=env_flag("WARM_CAMERA"), help="Shortcut for --reed-camera-mode warm.")
    parser.add_argument("--warm-camera-discard-frames", type=int, default=int(os.environ.get("WARM_CAMERA_DISCARD_FRAMES", "2")))
    parser.add_argument("--post-open-delay", type=float, default=float(os.environ.get("POST_OPEN_DELAY_SECONDS", "0.0")))
    parser.add_argument("--post-close-delay", type=float, default=float(os.environ.get("POST_CLOSE_DELAY_SECONDS", "0.0")))
    parser.add_argument("--preview-stream", action="store_true", default=env_flag("PREVIEW_STREAM"), help="Serve a browser camera preview from this Pi.")
    parser.add_argument("--preview-stream-host", default=os.environ.get("PREVIEW_STREAM_HOST", "0.0.0.0"))
    parser.add_argument("--preview-stream-port", type=int, default=int(os.environ.get("PREVIEW_STREAM_PORT", "8080")))
    parser.add_argument("--preview-stream-quality", type=int, default=int(os.environ.get("PREVIEW_STREAM_QUALITY", "80")))
    parser.add_argument("--preview-idle-interval", type=float, default=float(os.environ.get("PREVIEW_IDLE_INTERVAL_SECONDS", "0.2")))
    parser.add_argument("--once", action="store_true", help="Upload the first stable prediction and exit.")
    parser.add_argument("--dry-run", action="store_true", help="Classify frames without uploading.")
    args = parser.parse_args()
    if args.warm_camera:
        args.reed_camera_mode = "warm"
    return args


def scan_until_action(
    camera,
    detector,
    classifier,
    args: argparse.Namespace,
    action_url: str,
    action: str,
    preview_stream: PreviewStreamer | None = None,
) -> bool:
    settings = scan_settings(args)
    last_signature: tuple[str, ...] = ()
    stable_count = 0
    started_at = time.time()

    while True:
        if args.scan_timeout > 0 and time.time() - started_at > args.scan_timeout:
            print(f"Scan timed out without a {action}.")
            return False

        frame = camera.read()
        candidates = classify_frame(frame, detector, classifier, settings)
        signature = prediction_signature(candidates)
        print(f"Read: {format_candidates(candidates)}")
        if preview_stream is not None:
            preview_stream.update(frame, candidates, f"{action} scan")

        if signature and signature == last_signature:
            stable_count += 1
        else:
            last_signature = signature
            stable_count = 1 if signature else 0

        if signature and stable_count >= args.stable_frames:
            apply_candidates(action, action_url, args.fridge_id, frame, candidates, args.dry_run)
            return True

        time.sleep(args.interval)


def scan_until_upload(camera, detector, classifier, args: argparse.Namespace, upload_url: str) -> bool:
    return scan_until_action(camera, detector, classifier, args, upload_url, "upload")


def run_continuous(
    detector,
    classifier,
    args: argparse.Namespace,
    upload_url: str,
    preview_stream: PreviewStreamer | None = None,
) -> None:
    camera = make_camera(args.camera_backend, args.camera_index, args.width, args.height, args.fps)
    print(f"Camera started. Upload target: {upload_url}")

    settings = scan_settings(args)
    last_signature: tuple[str, ...] = ()
    stable_count = 0
    last_uploaded_signature: tuple[str, ...] = ()
    last_uploaded_at = 0.0

    try:
        while True:
            frame = camera.read()
            candidates = classify_frame(frame, detector, classifier, settings)
            signature = prediction_signature(candidates)
            print(f"Read: {format_candidates(candidates)}")
            if preview_stream is not None:
                preview_stream.update(frame, candidates, "continuous scan")

            if signature and signature == last_signature:
                stable_count += 1
            else:
                last_signature = signature
                stable_count = 1 if signature else 0

            current_time = time.time()
            cooldown_elapsed = current_time - last_uploaded_at >= args.cooldown
            labels_changed = signature != last_uploaded_signature

            if signature and stable_count >= args.stable_frames and (cooldown_elapsed or labels_changed):
                upload_candidates(upload_url, args.fridge_id, frame, candidates, args.dry_run)
                last_uploaded_signature = signature
                last_uploaded_at = current_time
                if args.once:
                    return

            time.sleep(args.interval)
    finally:
        camera.close()


def wait_for_reed_state(
    sensor: ReedDoorSensor,
    target_open: bool,
    args: argparse.Namespace,
    camera=None,
    preview_stream: PreviewStreamer | None = None,
    status: str | None = None,
) -> None:
    while sensor.is_open() != target_open:
        if camera is not None and preview_stream is not None:
            frame = camera.read()
            preview_stream.update(frame, None, status)
            time.sleep(args.preview_idle_interval)
        else:
            time.sleep(0.05)


def scan_reed_event(
    warm_camera,
    detector,
    classifier,
    args: argparse.Namespace,
    action_url: str,
    action: str,
    preview_stream: PreviewStreamer | None = None,
) -> None:
    camera = warm_camera
    if camera is not None:
        discard_camera_frames(camera, args.warm_camera_discard_frames)
    else:
        camera = make_camera(args.camera_backend, args.camera_index, args.width, args.height, args.fps)

    try:
        scan_until_action(camera, detector, classifier, args, action_url, action, preview_stream)
    finally:
        if warm_camera is None:
            camera.close()
            print("Camera stopped.")
        else:
            print("Scan finished. Keeping camera warm.")


def run_reed_triggered(
    detector,
    classifier,
    args: argparse.Namespace,
    upload_url: str,
    consume_url: str,
    preview_stream: PreviewStreamer | None = None,
) -> None:
    sensor = ReedDoorSensor(args.reed_pin, args.reed_open_level, args.reed_bounce_time)
    warm_camera = None
    consume_on_close = args.reed_workflow == "add-on-open-consume-on-close"
    print(
        f"Waiting for reed open on GPIO {args.reed_pin} "
        f"(open level: {args.reed_open_level}, workflow: {args.reed_workflow})."
    )

    if args.reed_camera_mode == "warm":
        warm_camera = make_camera(args.camera_backend, args.camera_index, args.width, args.height, args.fps)
        print("Camera is warmed and ready; detection will run only on reed events.")

    try:
        while True:
            wait_for_reed_state(
                sensor,
                True,
                args,
                warm_camera,
                preview_stream,
                "waiting for reed open",
            )
            print("Reed opened. Starting add scan.")
            if args.post_open_delay > 0:
                time.sleep(args.post_open_delay)
            scan_reed_event(warm_camera, detector, classifier, args, upload_url, "upload", preview_stream)

            if args.once and not consume_on_close:
                return

            wait_for_reed_state(
                sensor,
                False,
                args,
                warm_camera,
                preview_stream,
                "waiting for reed close",
            )
            if consume_on_close:
                print("Reed closed. Starting consume scan.")
                if args.post_close_delay > 0:
                    time.sleep(args.post_close_delay)
                scan_reed_event(warm_camera, detector, classifier, args, consume_url, "consume", preview_stream)
                if args.once:
                    return
                print("Consume scan finished. Ready for next open event.")
            else:
                print("Reed closed. Ready for next open event.")
            time.sleep(args.cooldown)
    finally:
        if warm_camera is not None:
            warm_camera.close()


def main() -> None:
    args = parse_args()
    model_path = Path(args.model).expanduser().resolve()
    backend_url = args.backend_url.rstrip("/")
    upload_url = backend_url + "/upload"
    consume_url = backend_url + "/consume"

    if not model_path.exists():
        raise SystemExit(f"Model was not found: {model_path}")
    if not args.dry_run:
        check_backend(upload_url)

    from ultralytics import YOLO

    classifier = YOLO(str(model_path))
    detector = load_detector(args.detector_model, args.disable_detector)
    preview_stream = None
    if args.preview_stream:
        preview_stream = PreviewStreamer(
            args.preview_stream_host,
            args.preview_stream_port,
            max(1, min(100, args.preview_stream_quality)),
        )
        preview_stream.start()

    try:
        if args.trigger == "reed":
            run_reed_triggered(detector, classifier, args, upload_url, consume_url, preview_stream)
        else:
            run_continuous(detector, classifier, args, upload_url, preview_stream)
    finally:
        if preview_stream is not None:
            preview_stream.close()


if __name__ == "__main__":
    main()
