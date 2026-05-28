from __future__ import annotations

import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from zipfile import ZipFile

import cv2
import numpy as np

BASE_DIR = Path(__file__).resolve().parent
TARGET_DIR = BASE_DIR / "custom_dataset" / "egg" / "public"
TEMP_IMPORT_DIR = BASE_DIR / "temp_import" / "aihub_egg_sample"
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


def clamp(value: float, lower: int, upper: int) -> int:
    return max(lower, min(int(round(value)), upper))


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


def text_float(element: ET.Element, tag: str) -> float:
    child = element.find(tag)
    if child is None or child.text is None:
        raise ValueError(f"Missing tag: {tag}")
    return float(child.text)


def crop_eggs(image_path: Path, xml_path: Path) -> int:
    image_bytes = np.fromfile(str(image_path), dtype=np.uint8)
    image = cv2.imdecode(image_bytes, cv2.IMREAD_COLOR)
    if image is None:
        return 0

    height, width = image.shape[:2]
    root = ET.parse(xml_path).getroot()
    copied = 0
    for index, box in enumerate(root.findall("bndbox"), start=1):
        x_min = text_float(box, "x_min")
        y_min = text_float(box, "y_min")
        x_max = text_float(box, "x_max")
        y_max = text_float(box, "y_max")

        box_width = x_max - x_min
        box_height = y_max - y_min
        padding = max(12, int(max(box_width, box_height) * 0.08))
        x1 = clamp(x_min - padding, 0, width - 1)
        y1 = clamp(y_min - padding, 0, height - 1)
        x2 = clamp(x_max + padding, x1 + 1, width)
        y2 = clamp(y_max + padding, y1 + 1, height)
        crop = image[y1:y2, x1:x2]
        if crop.size == 0:
            continue

        target_path = unique_target_path(TARGET_DIR, f"{image_path.stem}_egg_{index}.jpg")
        cv2.imwrite(str(target_path), crop)
        copied += 1
    return copied


def extract_zip(zip_path: Path, temp_dir: Path) -> Path:
    with ZipFile(zip_path) as zip_file:
        zip_file.extractall(temp_dir)
    return temp_dir


def import_sample(zip_path: Path) -> int:
    TARGET_DIR.mkdir(parents=True, exist_ok=True)
    if TEMP_IMPORT_DIR.exists():
        for path in sorted(TEMP_IMPORT_DIR.rglob("*"), reverse=True):
            if path.is_file():
                path.unlink()
            elif path.is_dir():
                path.rmdir()
    TEMP_IMPORT_DIR.mkdir(parents=True, exist_ok=True)
    extract_zip(zip_path, TEMP_IMPORT_DIR)

    images = {
        image_path.name: image_path
        for image_path in TEMP_IMPORT_DIR.rglob("*")
        if image_path.is_file() and image_path.suffix.lower() in IMAGE_EXTENSIONS
    }
    copied = 0
    for xml_path in TEMP_IMPORT_DIR.rglob("*.xml"):
        root = ET.parse(xml_path).getroot()
        file_name = root.findtext("file_name")
        if not file_name or file_name not in images:
            continue
        copied += crop_eggs(images[file_name], xml_path)
    return copied


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python backend\\import_aihub_egg_sample.py <Sample.zip>")

    zip_path = Path(sys.argv[1]).resolve()
    if not zip_path.exists():
        raise SystemExit(f"Sample zip was not found: {zip_path}")

    copied = import_sample(zip_path)
    print(f"Imported {copied} egg crops into {TARGET_DIR}")


if __name__ == "__main__":
    main()
