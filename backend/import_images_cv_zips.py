from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path
from zipfile import ZipFile

BASE_DIR = Path(__file__).resolve().parent
CUSTOM_DATASET_DIR = BASE_DIR / "custom_dataset"
IMAGE_EXTENSIONS = {".bmp", ".jpeg", ".jpg", ".png", ".webp"}

LABEL_ALIASES = {
    "aubergine": "eggplant",
    "bell pepper": "paprika",
    "fruit and vegetable cabbage": "cabbage",
    "fruit and vegetable eggplant": "eggplant",
    "fruit and vegetable garlic": "garlic",
    "fruit and vegetable lettuce": "lettuce",
    "fruit and vegetable onion": "onion",
    "fruit and vegetable potato": "potato",
    "fruit and vegetable spinach": "spinach",
    "fruit and vegetable tomato": "tomato",
    "fruit_and_vegetable cabbage": "cabbage",
    "fruit_and_vegetable eggplant": "eggplant",
    "fruit_and_vegetable garlic": "garlic",
    "fruit_and_vegetable lettuce": "lettuce",
    "fruit_and_vegetable onion": "onion",
    "fruit_and_vegetable potato": "potato",
    "fruit_and_vegetable spinach": "spinach",
    "fruit_and_vegetable tomato": "tomato",
    "green onion": "green_onion",
    "green onions": "green_onion",
    "scallion": "green_onion",
    "spring onion": "green_onion",
}


def normalize_label(label: str) -> str:
    normalized = label.strip().lower().replace("-", " ").replace("_", " ")
    normalized = LABEL_ALIASES.get(normalized, normalized)
    return normalized.replace(" ", "_")


def read_meta(zip_file: ZipFile) -> dict:
    for entry in zip_file.infolist():
        if entry.filename.endswith("meta.json"):
            with zip_file.open(entry) as file:
                return json.load(file)
    return {}


def unique_target_path(target_dir: Path, filename: str) -> Path:
    target = target_dir / filename
    if not target.exists():
        return target

    stem = target.stem
    suffix = target.suffix
    index = 1
    while True:
        candidate = target_dir / f"{stem}_{index}{suffix}"
        if not candidate.exists():
            return candidate
        index += 1


def import_zip(zip_path: Path) -> tuple[str, int]:
    copied = 0
    with ZipFile(zip_path) as zip_file:
        meta = read_meta(zip_file)
        labels = meta.get("labels") or []
        default_label = normalize_label(labels[0]) if labels else None

        for entry in zip_file.infolist():
            if entry.is_dir():
                continue
            source_path = Path(entry.filename)
            if source_path.suffix.lower() not in IMAGE_EXTENSIONS:
                continue

            parts = entry.filename.split("/")
            raw_label = parts[-2] if len(parts) >= 2 else default_label
            label = normalize_label(raw_label or "")
            if not label:
                continue

            target_dir = CUSTOM_DATASET_DIR / label / "public"
            target_dir.mkdir(parents=True, exist_ok=True)
            target_path = unique_target_path(target_dir, source_path.name)
            with zip_file.open(entry) as source_file, target_path.open("wb") as target_file:
                shutil.copyfileobj(source_file, target_file)
            copied += 1

    return zip_path.name, copied


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit("Usage: python backend\\import_images_cv_zips.py <zip_path> [<zip_path> ...]")

    for raw_path in sys.argv[1:]:
        zip_path = Path(raw_path).resolve()
        if not zip_path.exists():
            print(f"Missing: {zip_path}")
            continue
        name, copied = import_zip(zip_path)
        print(f"Imported {copied} images from {name}")


if __name__ == "__main__":
    main()
