from __future__ import annotations

import json
import os
from pathlib import Path

from ultralytics import YOLO

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_MODEL = BASE_DIR / "runs" / "classify" / "grocery-classifier-public4" / "weights" / "best.pt"
MODEL_PATH = Path(os.environ.get("CLASSIFIER_MODEL_PATH", DEFAULT_MODEL))
DATASET_DIR = Path(
    os.environ.get("CLASSIFIER_DATASET_DIR", BASE_DIR / "datasets" / "grocery_classifier")
)
OUTPUT_PATH = BASE_DIR / "runs" / "classify" / "evaluation_summary.json"
ALLOWED_LABELS = {
    label.strip().lower()
    for label in os.environ.get(
        "RECOGNITION_ALLOWED_LABELS", ""
    ).split(",")
    if label.strip()
}
CONFIDENCE_GATE = float(os.environ.get("CLASSIFIER_MIN_CONFIDENCE", "0.78"))
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


def main() -> None:
    if not MODEL_PATH.is_file():
        raise SystemExit(f"Classifier model was not found: {MODEL_PATH}")
    if not (DATASET_DIR / "test").is_dir():
        raise SystemExit(
            f"Test dataset was not found: {DATASET_DIR / 'test'}\n"
            "Run prepare_grocery_classifier_dataset.py first."
        )

    model = YOLO(str(MODEL_PATH))
    metrics = model.val(
        data=str(DATASET_DIR),
        split="test",
        project=str(BASE_DIR / "runs" / "classify"),
        name="grocery-classifier-evaluation",
        plots=True,
    )
    matrix = metrics.confusion_matrix.matrix
    names = model.names
    per_class = {}
    for class_id, class_name in names.items():
        true_total = float(matrix[:, class_id].sum())
        predicted_total = float(matrix[class_id, :].sum())
        correct = float(matrix[class_id, class_id])
        per_class[class_name] = {
            "precision": correct / predicted_total if predicted_total else 0.0,
            "recall": correct / true_total if true_total else 0.0,
            "test_images": int(true_total),
        }

    test_paths = sorted(
        path
        for path in (DATASET_DIR / "test").rglob("*")
        if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS
    )
    evaluation_labels = ALLOWED_LABELS or set(names.values())
    gated = {
        label: {"accepted": 0, "correct": 0, "true_images": 0}
        for label in sorted(evaluation_labels)
    }
    for path in test_paths:
        if path.parent.name in gated:
            gated[path.parent.name]["true_images"] += 1
    predictions = model.predict(
        source=[str(path) for path in test_paths],
        imgsz=224,
        verbose=False,
    )
    for path, result in zip(test_paths, predictions, strict=True):
        predicted = names[int(result.probs.top1)]
        confidence = float(result.probs.top1conf)
        if predicted not in gated or confidence < CONFIDENCE_GATE:
            continue
        gated[predicted]["accepted"] += 1
        if predicted == path.parent.name:
            gated[predicted]["correct"] += 1
    for values in gated.values():
        accepted = values["accepted"]
        true_images = values["true_images"]
        values["accepted_precision"] = (
            values["correct"] / accepted if accepted else 0.0
        )
        values["accepted_recall"] = (
            values["correct"] / true_images if true_images else 0.0
        )
    summary = {
        "model": str(MODEL_PATH),
        "dataset": str(DATASET_DIR),
        "top1_accuracy": float(metrics.top1),
        "top5_accuracy": float(metrics.top5),
        "per_class": per_class,
        "automatic_registration": {
            "minimum_confidence": CONFIDENCE_GATE,
            "allowed_labels": sorted(evaluation_labels),
            "per_class": gated,
        },
        "results_directory": str(metrics.save_dir),
    }
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
