import os
import time
from pathlib import Path
from threading import Lock, Thread

import cv2
import requests
from ultralytics import YOLO

BASE_DIR = Path(__file__).resolve().parent
TEMP_DIR = BASE_DIR / "temp"
CROP_DIR = TEMP_DIR / "crops"

DETECTOR_MODEL_PATH = os.environ.get("DETECTOR_MODEL_PATH", str(BASE_DIR / "yolov8n.pt"))
DEFAULT_CLASSIFIER_MODEL_PATH = BASE_DIR / "runs" / "classify" / "grocery-classifier-public4" / "weights" / "best.pt"
CLASSIFIER_MODEL_PATH = os.environ.get("CLASSIFIER_MODEL_PATH", str(DEFAULT_CLASSIFIER_MODEL_PATH))
SERVER_UPLOAD_URL = os.environ.get("SERVER_UPLOAD_URL", "http://127.0.0.1:5000/upload")
FRIDGE_ID = os.environ.get("FRIDGE_ID")
CAMERA_INDEX = int(os.environ.get("CAMERA_INDEX", "0"))
CAMERA_WIDTH = int(os.environ.get("CAMERA_WIDTH", "640"))
CAMERA_HEIGHT = int(os.environ.get("CAMERA_HEIGHT", "480"))
DETECTION_IMGSZ = int(os.environ.get("DETECTION_IMGSZ", "640"))
CONFIDENCE_THRESHOLD = float(os.environ.get("CONFIDENCE_THRESHOLD", "0.30"))
CLASSIFIER_CONFIDENCE_THRESHOLD = float(os.environ.get("CLASSIFIER_CONFIDENCE_THRESHOLD", "0.55"))
CLASSIFIER_BACKGROUND_STRONG_CONFIDENCE = float(os.environ.get("CLASSIFIER_BACKGROUND_STRONG_CONFIDENCE", "0.90"))
CLASSIFY_ALL_CROPS = os.environ.get("CLASSIFY_ALL_CROPS", "1").strip().lower() not in {"0", "false", "no"}
COOLDOWN_SECONDS = int(os.environ.get("COOLDOWN_SECONDS", "5"))
MIN_CROP_PADDING = int(os.environ.get("MIN_CROP_PADDING", "24"))
MAX_CROP_PADDING = int(os.environ.get("MAX_CROP_PADDING", "80"))
FALLBACK_CENTER_CROP_RATIO = float(os.environ.get("FALLBACK_CENTER_CROP_RATIO", "0.70"))
DETECTION_FRAME_INTERVAL = max(1, int(os.environ.get("DETECTION_FRAME_INTERVAL", "3")))
DISPLAY_MAX_WIDTH = int(os.environ.get("DISPLAY_MAX_WIDTH", "960"))

EXCLUDED_LABELS = {
    "person",
}
APP_INGREDIENT_LABELS = {
    "apple",
    "avocado",
    "banana",
    "bottle",
    "broccoli",
    "cabbage",
    "carrot",
    "cheese",
    "cucumber",
    "egg",
    "eggplant",
    "garlic",
    "ginger",
    "green_onion",
    "ham",
    "hot_dog",
    "kiwi",
    "leek",
    "lemon",
    "lettuce",
    "lime",
    "mango",
    "milk",
    "mushroom",
    "onion",
    "orange",
    "paprika",
    "pear",
    "peach",
    "pineapple",
    "potato",
    "spinach",
    "tofu",
    "tomato",
    "watermelon",
    "zucchini",
}
LABEL_MAP = {
    "aubergine": "eggplant",
    "bottle": "bottle",
    "drink bottle": "bottle",
    "eggplant": "eggplant",
    "green onion": "green_onion",
    "green onions": "green_onion",
    "hot dog": "hot_dog",
    "mushrooms": "mushroom",
    "orange bell pepper": "paprika",
    "pepper": "paprika",
    "bell pepper": "paprika",
    "scallion": "green_onion",
    "spring onion": "green_onion",
}
PUBLIC_DATASET_LABEL_MAP = {
    "apple": "apple",
    "avocado": "avocado",
    "banana": "banana",
    "bell pepper": "paprika",
    "broccoli": "broccoli",
    "cabbage": "cabbage",
    "carrot": "carrot",
    "cheese": "cheese",
    "cucumber": "cucumber",
    "egg": "egg",
    "eggplant": "eggplant",
    "aubergine": "eggplant",
    "garlic": "garlic",
    "ginger": "ginger",
    "green onion": "green_onion",
    "ham": "ham",
    "kiwi": "kiwi",
    "leek": "leek",
    "lemon": "lemon",
    "lettuce": "lettuce",
    "lime": "lime",
    "mango": "mango",
    "milk": "milk",
    "mushroom": "mushroom",
    "onion": "onion",
    "orange": "orange",
    "paprika": "paprika",
    "pear": "pear",
    "peach": "peach",
    "pineapple": "pineapple",
    "potato": "potato",
    "spinach": "spinach",
    "sausage": "hot_dog",
    "scallion": "green_onion",
    "spring onion": "green_onion",
    "tofu": "tofu",
    "tomato": "tomato",
    "watermelon": "watermelon",
    "zucchini": "zucchini",
}


def normalize_label(label: str) -> str:
    normalized = label.strip().lower().replace("_", " ")
    normalized = LABEL_MAP.get(normalized, normalized)
    return normalized.replace(" ", "_")


def normalize_public_dataset_label(label: str) -> str:
    normalized = label.strip().lower().replace("_", " ")
    mapped = PUBLIC_DATASET_LABEL_MAP.get(normalized, normalized)
    return normalize_label(mapped)


def enhance_crop(crop):
    resized = cv2.resize(crop, None, fx=1.4, fy=1.4, interpolation=cv2.INTER_CUBIC)
    lab = cv2.cvtColor(resized, cv2.COLOR_BGR2LAB)
    l_channel, a_channel, b_channel = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    enhanced_l = clahe.apply(l_channel)
    merged = cv2.merge((enhanced_l, a_channel, b_channel))
    return cv2.cvtColor(merged, cv2.COLOR_LAB2BGR)


def crop_box(frame, x1, y1, x2, y2):
    height, width = frame.shape[:2]
    box_width = max(1, x2 - x1)
    box_height = max(1, y2 - y1)
    dynamic_padding = max(MIN_CROP_PADDING, int(max(box_width, box_height) * 0.12))
    dynamic_padding = min(dynamic_padding, MAX_CROP_PADDING)
    x1 = max(0, x1 - dynamic_padding)
    y1 = max(0, y1 - dynamic_padding)
    x2 = min(width, x2 + dynamic_padding)
    y2 = min(height, y2 + dynamic_padding)
    return frame[y1:y2, x1:x2]


def center_crop_box(frame):
    height, width = frame.shape[:2]
    crop_width = int(width * FALLBACK_CENTER_CROP_RATIO)
    crop_height = int(height * FALLBACK_CENTER_CROP_RATIO)
    x1 = max(0, (width - crop_width) // 2)
    y1 = max(0, (height - crop_height) // 2)
    x2 = min(width, x1 + crop_width)
    y2 = min(height, y1 + crop_height)
    return x1, y1, x2, y2


def load_classifier():
    if not CLASSIFIER_MODEL_PATH:
        return None

    classifier_path = Path(CLASSIFIER_MODEL_PATH)
    if not classifier_path.exists():
        print(f"Classifier model was not found: {classifier_path}")
        return None

    print(f"Loaded classifier: {classifier_path}")
    return YOLO(str(classifier_path))


def choose_classifier_prediction(results):
    probs = results[0].probs
    if probs is None:
        return None

    top_indices = [int(index) for index in probs.top5]
    top_confidences = probs.top5conf.tolist()
    candidates = [(results[0].names[index], float(confidence)) for index, confidence in zip(top_indices, top_confidences)]
    top_label, top_confidence = candidates[0]

    if top_confidence < CLASSIFIER_CONFIDENCE_THRESHOLD:
        return None

    if top_label == "background":
        if top_confidence >= CLASSIFIER_BACKGROUND_STRONG_CONFIDENCE:
            return None
        for label, confidence in candidates[1:]:
            if label != "background" and confidence >= CLASSIFIER_CONFIDENCE_THRESHOLD:
                return label, confidence
        return None

    return top_label, top_confidence


def classify_crop(classifier, crop):
    if classifier is None:
        return None

    results = classifier(crop, verbose=False)
    if not results:
        return None

    probs = results[0].probs
    if probs is None:
        return None

    selected = choose_classifier_prediction(results)
    if selected is None:
        return None

    class_name, confidence = selected
    normalized_name = normalize_public_dataset_label(class_name)

    if normalized_name not in APP_INGREDIENT_LABELS:
        return None

    return {
        "raw_label": class_name,
        "label": normalized_name,
        "confidence": confidence,
    }


def draw_detections(frame, detections):
    annotated = frame.copy()
    for detection in detections:
        x1, y1, x2, y2 = detection["coords"]
        label_text = f"{detection['label']} {detection['confidence']:.2f}"
        cv2.rectangle(annotated, (x1, y1), (x2, y2), (0, 200, 0), 2)
        cv2.putText(
            annotated,
            label_text,
            (x1, max(24, y1 - 10)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (0, 200, 0),
            2,
            cv2.LINE_AA,
        )
    return annotated


def resize_for_display(frame):
    if frame.shape[1] <= DISPLAY_MAX_WIDTH:
        return frame
    scale = DISPLAY_MAX_WIDTH / frame.shape[1]
    return cv2.resize(frame, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)


class LatestFrameReader:
    def __init__(self, capture):
        self.capture = capture
        self.lock = Lock()
        self.frame = None
        self.running = True
        self.thread = Thread(target=self._read_loop, daemon=True)
        self.thread.start()

    def _read_loop(self):
        while self.running:
            success, frame = self.capture.read()
            if not success:
                continue
            with self.lock:
                self.frame = frame

    def get_frame(self):
        with self.lock:
            if self.frame is None:
                return None
            return self.frame.copy()

    def stop(self):
        self.running = False
        self.thread.join(timeout=1)


detector = YOLO(DETECTOR_MODEL_PATH)
classifier = load_classifier()
cap = cv2.VideoCapture(CAMERA_INDEX)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA_WIDTH)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_HEIGHT)
cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

if not cap.isOpened():
    print("Camera is not available.")
    raise SystemExit(1)

frame_reader = LatestFrameReader(cap)

TEMP_DIR.mkdir(exist_ok=True)
CROP_DIR.mkdir(parents=True, exist_ok=True)

last_uploaded_time = 0.0
frame_index = 0
last_detections = []


while True:
    frame = frame_reader.get_frame()
    if frame is None:
        time.sleep(0.01)
        continue

    frame_index += 1
    should_run_detection = frame_index % DETECTION_FRAME_INTERVAL == 0

    if should_run_detection:
        results = detector(frame, imgsz=DETECTION_IMGSZ, verbose=False)
        detections = []
        for box in results[0].boxes:
            cls_id = int(box.cls[0].item())
            confidence = float(box.conf[0].item())
            raw_label = detector.names[cls_id]
            if confidence < CONFIDENCE_THRESHOLD:
                continue
            if raw_label in EXCLUDED_LABELS:
                continue

            x1, y1, x2, y2 = [int(value) for value in box.xyxy[0].tolist()]
            detections.append(
                {
                    "raw_label": raw_label,
                    "label": normalize_label(raw_label),
                    "confidence": confidence,
                    "coords": (x1, y1, x2, y2),
                }
            )

        last_detections = detections
        current_time = time.time()

        if not detections and classifier is not None:
            x1, y1, x2, y2 = center_crop_box(frame)
            fallback_crop = enhance_crop(frame[y1:y2, x1:x2])
            fallback_classification = classify_crop(classifier, fallback_crop)
            if fallback_classification:
                detections.append(
                    {
                        "raw_label": f"center crop -> {fallback_classification['raw_label']}",
                        "label": fallback_classification["label"],
                        "confidence": fallback_classification["confidence"],
                        "coords": (x1, y1, x2, y2),
                        "fallback_crop": fallback_crop,
                    }
                )
                last_detections = detections

        if detections and (current_time - last_uploaded_time) >= COOLDOWN_SECONDS:
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            full_image_name = TEMP_DIR / f"{timestamp}.jpg"
            cv2.imwrite(str(full_image_name), frame)

            for index, detection in enumerate(detections, start=1):
                crop = crop_box(frame, *detection["coords"])
                if crop.size == 0:
                    continue

                should_classify = (
                    classifier is not None
                    and CLASSIFY_ALL_CROPS
                    and "fallback_crop" not in detection
                ) or (classifier is not None and detection["label"] not in APP_INGREDIENT_LABELS)
                enhanced_crop = detection["fallback_crop"] if "fallback_crop" in detection else (enhance_crop(crop) if should_classify else crop)
                classification = classify_crop(classifier, enhanced_crop) if should_classify else None
                final_label = classification["label"] if classification else detection["label"]
                final_confidence = classification["confidence"] if classification else detection["confidence"]
                detected_name = detection["raw_label"]

                if classification:
                    detected_name = f"{detection['raw_label']} -> {classification['raw_label']}"

                crop_image_name = CROP_DIR / f"{timestamp}_{index}.jpg"
                cv2.imwrite(str(crop_image_name), enhanced_crop)

                try:
                    with open(full_image_name, "rb") as image_file, open(crop_image_name, "rb") as crop_file:
                        files = {
                            "image": (full_image_name.name, image_file, "image/jpeg"),
                            "crop_image": (crop_image_name.name, crop_file, "image/jpeg"),
                        }
                        data = {
                            "label": final_label,
                            "detected_name": detected_name,
                            "confidence": f"{final_confidence:.4f}",
                            "quantity": "1",
                            "unit": "ea",
                        }
                        if FRIDGE_ID:
                            data["fridge_id"] = FRIDGE_ID
                        response = requests.post(SERVER_UPLOAD_URL, files=files, data=data, timeout=10)

                    if response.ok:
                        print(
                            f"Uploaded {detected_name} as {final_label} "
                            f"({final_confidence:.2f})"
                        )
                    else:
                        print("Upload failed:", response.text)
                except Exception as error:
                    print("Upload error:", error)

            last_uploaded_time = current_time

    display_frame = resize_for_display(draw_detections(frame, last_detections))
    cv2.imshow("YOLO Detection", display_frame)
    if cv2.waitKey(1) == ord("q"):
        break

frame_reader.stop()
cap.release()
cv2.destroyAllWindows()
