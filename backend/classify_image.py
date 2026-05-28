from __future__ import annotations

import os
import sys
from pathlib import Path

from ultralytics import YOLO

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_MODEL_PATH = BASE_DIR / "runs" / "classify" / "grocery-classifier-public4" / "weights" / "best.pt"
MIN_CONFIDENCE = float(os.environ.get("CLASSIFIER_MIN_CONFIDENCE", "0.65"))
BACKGROUND_STRONG_CONFIDENCE = float(os.environ.get("CLASSIFIER_BACKGROUND_STRONG_CONFIDENCE", "0.90"))


def choose_prediction(results):
    probs = results[0].probs
    if probs is None:
        return None, []

    top_indices = [int(index) for index in probs.top5]
    top_confidences = probs.top5conf.tolist()
    candidates = [(results[0].names[index], confidence) for index, confidence in zip(top_indices, top_confidences)]

    top_label, top_confidence = candidates[0]
    if top_confidence < MIN_CONFIDENCE:
        return ("none", top_confidence), candidates

    if top_label == "background" and top_confidence < BACKGROUND_STRONG_CONFIDENCE:
        for label, confidence in candidates[1:]:
            if label != "background" and confidence >= MIN_CONFIDENCE:
                return (label, confidence), candidates
        return ("none", top_confidence), candidates

    return (top_label, top_confidence), candidates


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit("Usage: python backend\\classify_image.py <image_path> [model_path]")

    image_path = Path(sys.argv[1]).resolve()
    model_path = Path(sys.argv[2]).resolve() if len(sys.argv) >= 3 else DEFAULT_MODEL_PATH

    if not image_path.exists():
        raise SystemExit(f"Image was not found: {image_path}")
    if not model_path.exists():
        raise SystemExit(f"Model was not found: {model_path}")

    model = YOLO(str(model_path))
    results = model(str(image_path), verbose=False)
    selected, candidates = choose_prediction(results)
    if selected is None:
        raise SystemExit("This model did not return classification probabilities.")

    print(f"Image: {image_path}")
    print(f"Model: {model_path}")
    print(f"Selected: {selected[0]} ({selected[1]:.4f})")
    print("Top predictions:")
    for label, confidence in candidates:
        print(f"  {label}: {confidence:.4f}")


if __name__ == "__main__":
    main()
