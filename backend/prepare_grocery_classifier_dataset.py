from __future__ import annotations

import csv
import os
import random
import shutil
from pathlib import Path

import cv2

SOURCE_DATASET_DIR = Path(
    os.environ.get(
        "GROCERY_SOURCE_DATASET_DIR",
        r"C:\Users\dudal\Desktop\GroceryStoreDataset-master\dataset",
    )
)
EGG_SOURCE_DIR = Path(os.environ.get("EGG_SOURCE_DIR", r"C:\Users\dudal\Desktop\Eggs Classification"))
TARGET_DATASET_DIR = Path(__file__).resolve().parent / "datasets" / "grocery_classifier"
CUSTOM_DATASET_DIR = Path(
    os.environ.get("CUSTOM_GROCERY_DATASET_DIR", Path(__file__).resolve().parent / "custom_dataset")
)
LOCAL_BACKGROUND_SOURCES = (
    Path(__file__).resolve().parent / "temp",
    Path(__file__).resolve().parent / "uploads",
)

COARSE_CLASS_TO_APP_LABEL = {
    "Apple": "apple",
    "Avocado": "avocado",
    "Banana": "banana",
    "Broccoli": "broccoli",
    "Cabbage": "cabbage",
    "Carrots": "carrot",
    "Cucumber": "cucumber",
    "Garlic": "garlic",
    "Ginger": "ginger",
    "Kiwi": "kiwi",
    "Leek": "leek",
    "Lemon": "lemon",
    "Lettuce": "lettuce",
    "Lime": "lime",
    "Mango": "mango",
    "Milk": "milk",
    "Mushroom": "mushroom",
    "Onion": "onion",
    "Orange": "orange",
    "Pear": "pear",
    "Peach": "peach",
    "Pepper": "paprika",
    "Pineapple": "pineapple",
    "Potato": "potato",
    "Tomato": "tomato",
    "Zucchini": "zucchini",
}
FINE_CLASS_TO_APP_LABEL = {
    "Aubergine": "eggplant",
    "Bell Pepper": "paprika",
    "Eggplant": "eggplant",
    "Green Bell Pepper": "paprika",
    "Red Bell Pepper": "paprika",
    "Watermelon": "watermelon",
    "Yellow Bell Pepper": "paprika",
}
EXTERNAL_CLASS_SOURCES = {
    "egg": [
        EGG_SOURCE_DIR / "Damaged",
        EGG_SOURCE_DIR / "Not Damaged",
    ],
}
ACTIVE_LABELS = (
    "apple",
    "banana",
    "background",
    "broccoli",
    "cabbage",
    "carrot",
    "cheese",
    "cucumber",
    "egg",
    "eggplant",
    "garlic",
    "lettuce",
    "milk",
    "mushroom",
    "onion",
    "paprika",
    "potato",
    "spinach",
    "tomato",
    "tofu",
    "zucchini",
)
MAX_IMAGES_PER_SPLIT = {
    "apple": {"train": 180, "val": 30, "test": 120},
    "banana": {"train": 45, "val": 6, "test": 44},
    "background": {"train": 140, "val": 25, "test": 25},
    "broccoli": {"train": 120, "val": 20, "test": 80},
    "cabbage": {"train": 120, "val": 20, "test": 80},
    "carrot": {"train": 120, "val": 20, "test": 80},
    "cheese": {"train": 120, "val": 20, "test": 80},
    "cucumber": {"train": 120, "val": 20, "test": 80},
    "egg": {"train": 180, "val": 30, "test": 30},
    "eggplant": {"train": 120, "val": 20, "test": 80},
    "garlic": {"train": 120, "val": 20, "test": 80},
    "lettuce": {"train": 120, "val": 20, "test": 80},
    "milk": {"train": 150, "val": 26, "test": 100},
    "mushroom": {"train": 120, "val": 20, "test": 80},
    "onion": {"train": 38, "val": 5, "test": 37},
    "paprika": {"train": 120, "val": 20, "test": 80},
    "potato": {"train": 75, "val": 10, "test": 70},
    "spinach": {"train": 120, "val": 20, "test": 80},
    "tomato": {"train": 120, "val": 8, "test": 100},
    "tofu": {"train": 120, "val": 20, "test": 80},
    "zucchini": {"train": 120, "val": 20, "test": 80},
}
SPLIT_RATIOS = {
    "train": 0.7,
    "val": 0.15,
    "test": 0.15,
}
RANDOM_SEED = 42
SPLITS = ("train", "val", "test")
SINGLE_OBJECT_AUGMENT_LABELS = tuple(label for label in ACTIVE_LABELS if label != "background")
SINGLE_OBJECT_CROPS_PER_IMAGE = int(os.environ.get("SINGLE_OBJECT_CROPS_PER_IMAGE", "2"))
SINGLE_OBJECT_MIN_SCALE = float(os.environ.get("SINGLE_OBJECT_MIN_SCALE", "0.42"))
SINGLE_OBJECT_MAX_SCALE = float(os.environ.get("SINGLE_OBJECT_MAX_SCALE", "0.72"))
IMAGE_EXTENSIONS = {".bmp", ".jpeg", ".jpg", ".png", ".webp"}


def load_class_maps(classes_csv_path: Path) -> tuple[dict[int, str], dict[int, str]]:
    coarse_label_map: dict[int, str] = {}
    fine_label_map: dict[int, str] = {}
    with classes_csv_path.open("r", encoding="utf-8") as csv_file:
        reader = csv.DictReader(csv_file)
        for row in reader:
            fine_id = int(row["Class ID (int)"])
            fine_name = row["Class Name (str)"].strip()
            coarse_id = int(row["Coarse Class ID (int)"])
            coarse_name = row["Coarse Class Name (str)"].strip()
            fine_label_map[fine_id] = fine_name
            coarse_label_map[coarse_id] = coarse_name
    return coarse_label_map, fine_label_map


def reset_target_directories() -> None:
    if TARGET_DATASET_DIR.exists():
        shutil.rmtree(TARGET_DATASET_DIR)

    for split in SPLITS:
        for label in ACTIVE_LABELS:
            (TARGET_DATASET_DIR / split / label).mkdir(parents=True, exist_ok=True)


def get_limit(label: str, split: str) -> int | None:
    return MAX_IMAGES_PER_SPLIT.get(label, {}).get(split)


def trim_paths(label: str, split: str, image_paths: list[Path], random_generator: random.Random) -> list[Path]:
    limit = get_limit(label, split)
    if limit is None or len(image_paths) <= limit:
        return image_paths
    shuffled = list(image_paths)
    random_generator.shuffle(shuffled)
    return shuffled[:limit]


def copy_paths_to_split(label: str, split: str, image_paths: list[Path], random_generator: random.Random) -> None:
    if label not in ACTIVE_LABELS:
        return
    selected_paths = trim_paths(label, split, image_paths, random_generator)
    for image_source in selected_paths:
        image_target = unique_target_path(TARGET_DATASET_DIR / split / label, image_source.name)
        shutil.copy2(image_source, image_target)


def safe_image_paths(paths: list[Path]) -> list[Path]:
    return [path for path in paths if path.suffix.lower() in IMAGE_EXTENSIONS and path.exists()]


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


def create_single_object_crop(image_source: Path, image_target: Path, random_generator: random.Random) -> bool:
    image = cv2.imread(str(image_source))
    if image is None:
        return False

    height, width = image.shape[:2]
    if height < 32 or width < 32:
        return False

    crop_size = int(min(height, width) * random_generator.uniform(SINGLE_OBJECT_MIN_SCALE, SINGLE_OBJECT_MAX_SCALE))
    crop_size = max(32, min(crop_size, height, width))
    center_x = width // 2 + random_generator.randint(-width // 8, width // 8)
    center_y = height // 2 + random_generator.randint(-height // 8, height // 8)
    x1 = max(0, min(width - crop_size, center_x - crop_size // 2))
    y1 = max(0, min(height - crop_size, center_y - crop_size // 2))
    crop = image[y1 : y1 + crop_size, x1 : x1 + crop_size]

    if random_generator.random() < 0.5:
        crop = cv2.flip(crop, 1)
    if random_generator.random() < 0.35:
        crop = cv2.convertScaleAbs(
            crop,
            alpha=random_generator.uniform(0.9, 1.12),
            beta=random_generator.randint(-10, 10),
        )

    return cv2.imwrite(str(image_target), crop)


def create_single_object_augments() -> None:
    if SINGLE_OBJECT_CROPS_PER_IMAGE <= 0:
        return

    random_generator = random.Random(RANDOM_SEED + 17)
    for label in SINGLE_OBJECT_AUGMENT_LABELS:
        train_dir = TARGET_DATASET_DIR / "train" / label
        if not train_dir.exists():
            continue

        source_paths = safe_image_paths([path for path in train_dir.iterdir() if path.is_file()])
        for image_source in source_paths:
            for crop_index in range(SINGLE_OBJECT_CROPS_PER_IMAGE):
                image_target = train_dir / f"{image_source.stem}_single_{crop_index}{image_source.suffix}"
                create_single_object_crop(image_source, image_target, random_generator)


def collect_split_images(
    split: str,
    coarse_label_map: dict[int, str],
    fine_label_map: dict[int, str],
) -> dict[str, list[Path]]:
    grouped_paths: dict[str, list[Path]] = {label: [] for label in ACTIVE_LABELS}
    split_file = SOURCE_DATASET_DIR / f"{split}.txt"
    with split_file.open("r", encoding="utf-8") as input_file:
        for raw_line in input_file:
            line = raw_line.strip()
            if not line:
                continue

            image_rel_path, fine_id_text, coarse_id_text = line.split(",")
            fine_id = int(fine_id_text)
            coarse_id = int(coarse_id_text)
            fine_name = fine_label_map[fine_id]
            coarse_name = coarse_label_map[coarse_id]
            app_label = FINE_CLASS_TO_APP_LABEL.get(fine_name) or COARSE_CLASS_TO_APP_LABEL.get(coarse_name)
            if app_label not in ACTIVE_LABELS:
                continue

            image_source = SOURCE_DATASET_DIR / image_rel_path.lstrip("/\\")
            grouped_paths.setdefault(app_label, []).append(image_source)
    return grouped_paths


def copy_grocery_dataset(coarse_label_map: dict[int, str], fine_label_map: dict[int, str]) -> None:
    random_generator = random.Random(RANDOM_SEED)
    for split in SPLITS:
        grouped_paths = collect_split_images(split, coarse_label_map, fine_label_map)
        for label, image_paths in grouped_paths.items():
            copy_paths_to_split(label, split, image_paths, random_generator)


def split_custom_images(image_paths: list[Path], random_generator: random.Random) -> dict[str, list[Path]]:
    shuffled = list(image_paths)
    random_generator.shuffle(shuffled)
    split_groups = {"train": [], "val": [], "test": []}
    if not shuffled:
        return split_groups

    cumulative_train = SPLIT_RATIOS["train"]
    cumulative_val = cumulative_train + SPLIT_RATIOS["val"]
    for index, image_source in enumerate(shuffled):
        position = (index + 1) / len(shuffled)
        if position <= cumulative_train:
            split_groups["train"].append(image_source)
        elif position <= cumulative_val:
            split_groups["val"].append(image_source)
        else:
            split_groups["test"].append(image_source)
    return split_groups


def copy_custom_dataset() -> None:
    if not CUSTOM_DATASET_DIR.exists():
        return

    random_generator = random.Random(RANDOM_SEED + 31)
    for class_dir in CUSTOM_DATASET_DIR.iterdir():
        if not class_dir.is_dir():
            continue

        label = normalize_custom_label(class_dir.name)
        if label not in ACTIVE_LABELS:
            print(f"Skipped custom class '{class_dir.name}' because it is not in ACTIVE_LABELS.")
            continue

        image_paths = safe_image_paths([path for path in class_dir.rglob("*") if path.is_file()])
        split_groups = split_custom_images(image_paths, random_generator)
        for split, split_paths in split_groups.items():
            copy_paths_to_split(label, split, split_paths, random_generator)


def has_custom_images() -> bool:
    if not CUSTOM_DATASET_DIR.exists():
        return False
    return any(path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS for path in CUSTOM_DATASET_DIR.rglob("*"))


def normalize_custom_label(label: str) -> str:
    normalized = label.strip().lower().replace("-", " ").replace("_", " ")
    aliases = {
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
        "fruit_and_vegetable_cabbage": "cabbage",
        "fruit_and_vegetable_eggplant": "eggplant",
        "fruit_and_vegetable_garlic": "garlic",
        "fruit_and_vegetable_lettuce": "lettuce",
        "fruit_and_vegetable_onion": "onion",
        "fruit_and_vegetable_potato": "potato",
        "fruit_and_vegetable_spinach": "spinach",
        "fruit_and_vegetable_tomato": "tomato",
        "green onion": "green_onion",
        "green onions": "green_onion",
        "red bell pepper": "paprika",
        "scallion": "green_onion",
        "spring onion": "green_onion",
        "yellow bell pepper": "paprika",
    }
    normalized = aliases.get(normalized, normalized)
    return normalized.replace(" ", "_")


def copy_external_class_images() -> None:
    random_generator = random.Random(RANDOM_SEED)
    cumulative_train = SPLIT_RATIOS["train"]
    cumulative_val = cumulative_train + SPLIT_RATIOS["val"]

    for app_label, source_dirs in EXTERNAL_CLASS_SOURCES.items():
        if app_label not in ACTIVE_LABELS:
            continue

        image_paths: list[Path] = []
        for source_dir in source_dirs:
            if not source_dir.exists():
                continue
            image_paths.extend(path for path in source_dir.iterdir() if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS)

        if not image_paths:
            continue

        random_generator.shuffle(image_paths)
        split_groups = {"train": [], "val": [], "test": []}
        for index, image_source in enumerate(image_paths):
            position = (index + 1) / len(image_paths)
            if position <= cumulative_train:
                split_groups["train"].append(image_source)
            elif position <= cumulative_val:
                split_groups["val"].append(image_source)
            else:
                split_groups["test"].append(image_source)

        for split, split_paths in split_groups.items():
            copy_paths_to_split(app_label, split, split_paths, random_generator)


def copy_background_images() -> None:
    random_generator = random.Random(RANDOM_SEED)
    split_groups = {"train": [], "val": [], "test": []}

    image_paths: list[Path] = []
    for source_dir in LOCAL_BACKGROUND_SOURCES:
        if not source_dir.exists():
            continue
        image_paths.extend(path for path in source_dir.iterdir() if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS)

    if not image_paths:
        return

    random_generator.shuffle(image_paths)
    cumulative_train = SPLIT_RATIOS["train"]
    cumulative_val = cumulative_train + SPLIT_RATIOS["val"]

    for index, image_source in enumerate(image_paths):
        position = (index + 1) / len(image_paths)
        if position <= cumulative_train:
            split_groups["train"].append(image_source)
        elif position <= cumulative_val:
            split_groups["val"].append(image_source)
        else:
            split_groups["test"].append(image_source)

    for split, split_paths in split_groups.items():
        copy_paths_to_split("background", split, split_paths, random_generator)


def count_images() -> dict[str, dict[str, int]]:
    counts: dict[str, dict[str, int]] = {}
    for split in SPLITS:
        counts[split] = {}
        for label in ACTIVE_LABELS:
            counts[split][label] = len(list((TARGET_DATASET_DIR / split / label).glob("*")))
    return counts


def prune_empty_label_directories() -> None:
    counts = count_images()
    for label in ACTIVE_LABELS:
        total = sum(split_counts[label] for split_counts in counts.values())
        if total > 0:
            continue
        for split in SPLITS:
            label_dir = TARGET_DATASET_DIR / split / label
            if label_dir.exists():
                label_dir.rmdir()


def main() -> None:
    classes_csv_path = SOURCE_DATASET_DIR / "classes.csv"
    has_grocery_dataset = classes_csv_path.exists()
    has_custom_dataset_images = has_custom_images()
    if not has_grocery_dataset and not has_custom_dataset_images:
        raise SystemExit(
            "No training image source was found.\n"
            f"- Grocery dataset path: {classes_csv_path}\n"
            f"- Custom dataset path: {CUSTOM_DATASET_DIR}\n"
            "Either set GROCERY_SOURCE_DATASET_DIR or add your own photos under backend\\custom_dataset\\<label>."
        )

    reset_target_directories()
    if has_grocery_dataset:
        coarse_label_map, fine_label_map = load_class_maps(classes_csv_path)
        copy_grocery_dataset(coarse_label_map, fine_label_map)
    copy_custom_dataset()
    copy_external_class_images()
    copy_background_images()
    create_single_object_augments()
    prune_empty_label_directories()

    print(f"Prepared dataset at: {TARGET_DATASET_DIR}")
    print("Active labels:", ", ".join(ACTIVE_LABELS))
    counts = count_images()
    for split, labels in counts.items():
        print(f"[{split}]")
        for label, image_count in labels.items():
            print(f"  {label}: {image_count}")


if __name__ == "__main__":
    main()
