from __future__ import annotations

import os
from pathlib import Path

from ultralytics.data.dataset import ClassificationDataset
from ultralytics import YOLO

BASE_DIR = Path(__file__).resolve().parent
DATASET_DIR = BASE_DIR / "datasets" / "grocery_classifier"
MODEL_NAME = os.environ.get("CLASSIFIER_BASE_MODEL", "yolov8n-cls.pt")
EPOCHS = int(os.environ.get("CLASSIFIER_EPOCHS", "20"))
IMAGE_SIZE = int(os.environ.get("CLASSIFIER_IMGSZ", "224"))
BATCH_SIZE = int(os.environ.get("CLASSIFIER_BATCH", "32"))
RUN_NAME = os.environ.get("CLASSIFIER_RUN_NAME", "grocery-classifier")
WORKERS = int(os.environ.get("CLASSIFIER_WORKERS", "0"))
DEGREES = float(os.environ.get("CLASSIFIER_DEGREES", "8"))
TRANSLATE = float(os.environ.get("CLASSIFIER_TRANSLATE", "0.12"))
SCALE = float(os.environ.get("CLASSIFIER_SCALE", "0.35"))
FLIPLR = float(os.environ.get("CLASSIFIER_FLIPLR", "0.5"))
ERASING = float(os.environ.get("CLASSIFIER_ERASING", "0.25"))


def disable_parallel_image_verification() -> None:
    def trust_existing_samples(self):
        return self.samples

    ClassificationDataset.verify_images = trust_existing_samples


def main() -> None:
    if not DATASET_DIR.exists():
        raise SystemExit(
            f"Dataset directory was not found: {DATASET_DIR}\n"
            "Run prepare_grocery_classifier_dataset.py first."
        )

    disable_parallel_image_verification()
    model = YOLO(MODEL_NAME)
    model.train(
        data=str(DATASET_DIR),
        epochs=EPOCHS,
        imgsz=IMAGE_SIZE,
        batch=BATCH_SIZE,
        name=RUN_NAME,
        project=str(BASE_DIR / "runs" / "classify"),
        workers=WORKERS,
        degrees=DEGREES,
        translate=TRANSLATE,
        scale=SCALE,
        fliplr=FLIPLR,
        erasing=ERASING,
    )

    print("Training finished.")
    print(
        "Use this classifier in detect.py with:\n"
        "$env:CLASSIFIER_MODEL_PATH=\"C:\\path\\to\\best.pt\""
    )


if __name__ == "__main__":
    main()
