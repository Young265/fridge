from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path

import pymysql
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_FOLDER = BASE_DIR / "uploads"
CROP_FOLDER = UPLOAD_FOLDER / "crops"

DB_CONFIG = {
    "host": "127.0.0.1",
    "port": 3306,
    "user": "root",
    "password": "root",
    "database": "fridge_db",
    "charset": "utf8mb4",
    "cursorclass": pymysql.cursors.DictCursor,
    "autocommit": False,
}

app = Flask(__name__)
CORS(app)

UPLOAD_FOLDER.mkdir(exist_ok=True)
CROP_FOLDER.mkdir(parents=True, exist_ok=True)

INGREDIENT_ALIASES = {
    "aubergine": "eggplant",
    "bell pepper": "paprika",
    "green onion": "green_onion",
    "green onions": "green_onion",
    "hot dog": "hot_dog",
    "pepper": "paprika",
    "red bell pepper": "paprika",
    "scallion": "green_onion",
    "spring onion": "green_onion",
    "yellow bell pepper": "paprika",
}


def get_connection(include_database: bool = True):
    config = dict(DB_CONFIG)
    if not include_database:
        config.pop("database", None)
    return pymysql.connect(**config)


def now_text() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def public_file_url(filename: str) -> str:
    return f"http://127.0.0.1:5000/uploads/{filename}"


def file_url_from_path(path: str | None) -> str | None:
    if not path:
        return None
    path_obj = Path(path)
    if path_obj.parent.name == "crops":
        return public_file_url(f"crops/{path_obj.name}")
    return public_file_url(path_obj.name)


def normalize_path(path: str | None) -> str | None:
    if not path:
        return None
    return path.replace("\\", "/")


def normalize_ingredient_name(name: str | None) -> str | None:
    if not name:
        return None
    normalized = name.strip().lower().replace("-", " ").replace("_", " ")
    normalized = " ".join(normalized.split())
    normalized = INGREDIENT_ALIASES.get(normalized, normalized)
    return normalized.replace(" ", "_")


def init_db() -> None:
    with get_connection(include_database=False) as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                f"CREATE DATABASE IF NOT EXISTS `{DB_CONFIG['database']}` "
                "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
            )
        conn.commit()

    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    user_id INT PRIMARY KEY AUTO_INCREMENT,
                    name VARCHAR(100) NOT NULL,
                    email VARCHAR(255) NOT NULL UNIQUE,
                    password_hash VARCHAR(255) NOT NULL,
                    current_fridge_id INT NULL,
                    created_at DATETIME NOT NULL,
                    updated_at DATETIME NOT NULL
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS fridges (
                    fridge_id INT PRIMARY KEY AUTO_INCREMENT,
                    user_id INT NOT NULL,
                    fridge_name VARCHAR(100) NOT NULL,
                    created_at DATETIME NOT NULL,
                    updated_at DATETIME NOT NULL,
                    CONSTRAINT fk_fridges_user
                        FOREIGN KEY (user_id) REFERENCES users(user_id)
                        ON DELETE CASCADE
                )
                """
            )
            cursor.execute(
                """
                SELECT COUNT(*) AS count
                FROM information_schema.COLUMNS
                WHERE TABLE_SCHEMA = %s
                  AND TABLE_NAME = 'users'
                  AND COLUMN_NAME = 'current_fridge_id'
                """,
                (DB_CONFIG["database"],),
            )
            column_exists = cursor.fetchone()["count"] > 0
            if not column_exists:
                cursor.execute(
                    """
                    ALTER TABLE users
                    ADD COLUMN current_fridge_id INT NULL
                    """
                )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS ingredients (
                    ingredient_id INT PRIMARY KEY AUTO_INCREMENT,
                    name VARCHAR(100) NOT NULL UNIQUE,
                    category VARCHAR(50) NOT NULL,
                    created_at DATETIME NOT NULL,
                    updated_at DATETIME NOT NULL
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS fridge_items (
                    fridge_item_id INT PRIMARY KEY AUTO_INCREMENT,
                    fridge_id INT NOT NULL,
                    ingredient_id INT NULL,
                    display_name VARCHAR(100) NOT NULL,
                    quantity DOUBLE NOT NULL DEFAULT 1,
                    unit VARCHAR(30) NOT NULL DEFAULT '개',
                    status VARCHAR(30) NOT NULL DEFAULT 'RECOGNIZED',
                    image_path VARCHAR(255) NULL,
                    crop_image_path VARCHAR(255) NULL,
                    confidence DOUBLE NULL,
                    detected_name VARCHAR(100) NULL,
                    note TEXT NULL,
                    created_at DATETIME NOT NULL,
                    updated_at DATETIME NOT NULL,
                    CONSTRAINT fk_items_fridge
                        FOREIGN KEY (fridge_id) REFERENCES fridges(fridge_id)
                        ON DELETE CASCADE,
                    CONSTRAINT fk_items_ingredient
                        FOREIGN KEY (ingredient_id) REFERENCES ingredients(ingredient_id)
                        ON DELETE SET NULL
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS recipes (
                    recipe_id INT PRIMARY KEY AUTO_INCREMENT,
                    name VARCHAR(200) NOT NULL,
                    description TEXT NOT NULL,
                    instructions TEXT NOT NULL,
                    cooking_time INT NOT NULL,
                    difficulty VARCHAR(50) NOT NULL,
                    created_at DATETIME NOT NULL,
                    updated_at DATETIME NOT NULL
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS recipe_ingredients (
                    recipe_id INT NOT NULL,
                    ingredient_id INT NOT NULL,
                    quantity DOUBLE NOT NULL DEFAULT 1,
                    unit VARCHAR(30) NOT NULL DEFAULT '개',
                    PRIMARY KEY (recipe_id, ingredient_id),
                    CONSTRAINT fk_recipe_ingredients_recipe
                        FOREIGN KEY (recipe_id) REFERENCES recipes(recipe_id)
                        ON DELETE CASCADE,
                    CONSTRAINT fk_recipe_ingredients_ingredient
                        FOREIGN KEY (ingredient_id) REFERENCES ingredients(ingredient_id)
                        ON DELETE CASCADE
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS app_state (
                    state_key VARCHAR(100) PRIMARY KEY,
                    state_value VARCHAR(255) NULL,
                    updated_at DATETIME NOT NULL
                )
                """
            )
        conn.commit()
        seed_data(conn)


def seed_data(conn) -> None:
    created_at = now_text()
    with conn.cursor() as cursor:
        korean_unit_updates = [
            ("ea", "개"),
            ("bowl", "공기"),
            ("slice", "장"),
            ("pack", "팩"),
            ("cup", "컵"),
            ("head", "통"),
        ]
        for english_unit, korean_unit in korean_unit_updates:
            cursor.execute(
                "UPDATE fridge_items SET unit = %s WHERE unit = %s",
                (korean_unit, english_unit),
            )
            cursor.execute(
                "UPDATE recipe_ingredients SET unit = %s WHERE unit = %s",
                (korean_unit, english_unit),
            )

        ingredients = [
            ("egg", "protein"),
            ("milk", "dairy"),
            ("onion", "vegetable"),
            ("carrot", "vegetable"),
            ("potato", "vegetable"),
            ("tomato", "vegetable"),
            ("green_onion", "vegetable"),
            ("cheese", "dairy"),
            ("ham", "protein"),
            ("tofu", "protein"),
            ("cabbage", "vegetable"),
            ("mushroom", "vegetable"),
            ("rice", "grain"),
            ("apple", "fruit"),
            ("banana", "fruit"),
            ("orange", "fruit"),
            ("watermelon", "fruit"),
            ("avocado", "fruit"),
            ("kiwi", "fruit"),
            ("lemon", "fruit"),
            ("lime", "fruit"),
            ("mango", "fruit"),
            ("pear", "fruit"),
            ("peach", "fruit"),
            ("pineapple", "fruit"),
            ("broccoli", "vegetable"),
            ("cucumber", "vegetable"),
            ("eggplant", "vegetable"),
            ("garlic", "vegetable"),
            ("ginger", "vegetable"),
            ("leek", "vegetable"),
            ("lettuce", "vegetable"),
            ("paprika", "vegetable"),
            ("spinach", "vegetable"),
            ("zucchini", "vegetable"),
            ("bottle", "drink"),
            ("cup", "drink"),
            ("hot_dog", "protein"),
            ("sandwich", "meal"),
            ("pizza", "meal"),
            ("donut", "dessert"),
            ("cake", "dessert"),
        ]
        for name, category in ingredients:
            cursor.execute(
                """
                INSERT INTO ingredients (name, category, created_at, updated_at)
                SELECT %s, %s, %s, %s
                FROM DUAL
                WHERE NOT EXISTS (
                    SELECT 1 FROM ingredients WHERE name = %s
                )
                """,
                (name, category, created_at, created_at, name),
            )

        recipes = [
            (
                "Egg Fried Rice",
                "계란 볶음밥",
                "남은 밥과 계란, 간단한 채소로 빠르게 만드는 볶음밥입니다.",
                "1. 양파와 당근을 잘게 썰어 볶습니다.\n2. 계란을 넣고 부드럽게 익힙니다.\n3. 밥을 넣어 고루 볶은 뒤 간을 맞춥니다.",
                15,
                "쉬움",
                [("egg", 2, "개"), ("rice", 1, "공기"), ("onion", 0.5, "개"), ("carrot", 0.5, "개")],
            ),
            (
                "Tomato Omelette",
                "토마토 오믈렛",
                "토마토와 대파를 넣어 산뜻하게 즐기는 부드러운 오믈렛입니다.",
                "1. 계란을 곱게 풀어둡니다.\n2. 토마토와 대파를 살짝 볶습니다.\n3. 계란물을 붓고 가장자리가 익으면 반으로 접습니다.",
                10,
                "쉬움",
                [("egg", 3, "개"), ("tomato", 1, "개"), ("green_onion", 0.5, "개")],
            ),
            (
                "Ham Cheese Toast",
                "햄 치즈 토스트",
                "햄, 치즈, 계란을 겹쳐 바삭하게 구운 간단한 토스트입니다.",
                "1. 빵 위에 햄과 치즈를 올립니다.\n2. 취향에 따라 계란을 더합니다.\n3. 겉면이 바삭해질 때까지 굽습니다.",
                8,
                "쉬움",
                [("ham", 2, "장"), ("cheese", 1, "장"), ("egg", 1, "개")],
            ),
            (
                "Tofu Mushroom Soup",
                "두부 버섯국",
                "두부와 버섯, 양파를 넣어 담백하게 끓이는 국입니다.",
                "1. 냄비에 육수나 물을 끓입니다.\n2. 양파와 버섯을 넣고 익힙니다.\n3. 두부와 대파를 넣고 한소끔 더 끓입니다.",
                20,
                "보통",
                [("tofu", 1, "팩"), ("mushroom", 1, "컵"), ("onion", 0.5, "개"), ("green_onion", 0.5, "개")],
            ),
            (
                "Potato Cabbage Stir Fry",
                "감자 양배추 볶음",
                "감자와 양배추, 양파로 만드는 짭조름한 채소 볶음입니다.",
                "1. 감자, 양배추, 양파를 먹기 좋게 썹니다.\n2. 감자를 먼저 볶아 속까지 익힙니다.\n3. 양배추와 양파를 넣고 간을 맞춰 볶습니다.",
                18,
                "쉬움",
                [("potato", 2, "개"), ("cabbage", 0.25, "통"), ("onion", 0.5, "개")],
            ),
        ]

        cursor.execute("SELECT COUNT(*) AS count FROM recipes")
        if cursor.fetchone()["count"] == 0:
            cursor.execute("SELECT ingredient_id, name FROM ingredients")
            ingredient_map = {row["name"]: row["ingredient_id"] for row in cursor.fetchall()}
            for _english_name, korean_name, description, instructions, cooking_time, difficulty, required in recipes:
                cursor.execute(
                    """
                    INSERT INTO recipes (name, description, instructions, cooking_time, difficulty, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """,
                    (korean_name, description, instructions, cooking_time, difficulty, created_at, created_at),
                )
                recipe_id = cursor.lastrowid
                cursor.executemany(
                    """
                    INSERT INTO recipe_ingredients (recipe_id, ingredient_id, quantity, unit)
                    VALUES (%s, %s, %s, %s)
                    """,
                    [(recipe_id, ingredient_map[item_name], quantity, unit) for item_name, quantity, unit in required],
                )
        else:
            for english_name, korean_name, description, instructions, cooking_time, difficulty, _required in recipes:
                cursor.execute(
                    """
                    UPDATE recipes
                    SET name = %s,
                        description = %s,
                        instructions = %s,
                        cooking_time = %s,
                        difficulty = %s,
                        updated_at = %s
                    WHERE name IN (%s, %s)
                    """,
                    (
                        korean_name,
                        description,
                        instructions,
                        cooking_time,
                        difficulty,
                        created_at,
                        english_name,
                        korean_name,
                    ),
                )
        cursor.execute("SELECT COUNT(*) AS count FROM app_state WHERE state_key = 'active_fridge_id'")
        if cursor.fetchone()["count"] == 0:
            cursor.execute("SELECT fridge_id FROM fridges ORDER BY fridge_id LIMIT 1")
            first_fridge = cursor.fetchone()
            cursor.execute(
                """
                INSERT INTO app_state (state_key, state_value, updated_at)
                VALUES (%s, %s, %s)
                """,
                ("active_fridge_id", str(first_fridge["fridge_id"]) if first_fridge else None, created_at),
            )
    conn.commit()


def set_active_fridge(cursor, fridge_id: int | None) -> None:
    cursor.execute(
        """
        INSERT INTO app_state (state_key, state_value, updated_at)
        VALUES (%s, %s, %s)
        ON DUPLICATE KEY UPDATE
            state_value = VALUES(state_value),
            updated_at = VALUES(updated_at)
        """,
        ("active_fridge_id", str(fridge_id) if fridge_id is not None else None, now_text()),
    )


def get_active_fridge_id(cursor) -> int | None:
    cursor.execute("SELECT state_value FROM app_state WHERE state_key = 'active_fridge_id'")
    row = cursor.fetchone()
    if not row or not row["state_value"]:
        return None
    return int(row["state_value"])


def serialize_user(row: dict) -> dict:
    return {
        "user_id": row["user_id"],
        "name": row["name"],
        "email": row["email"],
        "current_fridge_id": row.get("current_fridge_id"),
    }


def serialize_fridge(row: dict) -> dict:
    return {
        "fridge_id": row["fridge_id"],
        "fridge_name": row["fridge_name"],
        "created_at": row["created_at"].strftime("%Y-%m-%d %H:%M:%S"),
    }


def serialize_item(row: dict) -> dict:
    crop_image_path = normalize_path(row["crop_image_path"])
    image_path = normalize_path(row["image_path"])
    return {
        "fridge_item_id": row["fridge_item_id"],
        "fridge_id": row["fridge_id"],
        "ingredient_id": row["ingredient_id"],
        "display_name": row["display_name"],
        "quantity": row["quantity"],
        "unit": row["unit"],
        "status": row["status"],
        "detected_name": row["detected_name"],
        "confidence": row["confidence"],
        "note": row["note"],
        "image_path": image_path,
        "image_url": file_url_from_path(image_path),
        "crop_image_path": crop_image_path,
        "crop_image_url": file_url_from_path(crop_image_path),
        "created_at": row["created_at"].strftime("%Y-%m-%d %H:%M:%S"),
        "updated_at": row["updated_at"].strftime("%Y-%m-%d %H:%M:%S"),
    }


def resolve_ingredient(cursor, name: str | None):
    normalized_name = normalize_ingredient_name(name)
    if not normalized_name:
        return None
    cursor.execute(
        "SELECT ingredient_id, name FROM ingredients WHERE LOWER(name) = LOWER(%s)",
        (normalized_name,),
    )
    return cursor.fetchone()


def parse_float_value(value, default: float | None = None) -> float | None:
    if value is None or value == "":
        return default
    return float(value)


def resolve_target_fridge_id(cursor, fridge_id: int | None) -> int | None:
    if fridge_id:
        return fridge_id
    fridge_id = get_active_fridge_id(cursor)
    if fridge_id:
        return fridge_id
    cursor.execute("SELECT fridge_id FROM fridges ORDER BY fridge_id LIMIT 1")
    first_fridge = cursor.fetchone()
    return first_fridge["fridge_id"] if first_fridge else None


def save_detection_files(image, crop_image=None) -> tuple[Path | None, Path | None]:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    image_path = None
    if image and image.filename:
        image_filename = f"{timestamp}_{secure_filename(image.filename)}"
        image_path = UPLOAD_FOLDER / image_filename
        image.save(image_path)

    crop_path = None
    if crop_image and crop_image.filename:
        crop_filename = f"{timestamp}_crop_{secure_filename(crop_image.filename)}"
        crop_path = CROP_FOLDER / crop_filename
        crop_image.save(crop_path)

    return image_path, crop_path


def find_consumable_item(cursor, fridge_id: int, display_name: str, ingredient: dict | None):
    if ingredient:
        cursor.execute(
            """
            SELECT *
            FROM fridge_items
            WHERE fridge_id = %s
              AND ingredient_id = %s
              AND quantity > 0
            ORDER BY updated_at DESC, fridge_item_id DESC
            LIMIT 1
            """,
            (fridge_id, ingredient["ingredient_id"]),
        )
        row = cursor.fetchone()
        if row:
            return row

    normalized_name = normalize_ingredient_name(display_name)
    if not normalized_name:
        return None

    human_name = normalized_name.replace("_", " ")
    cursor.execute(
        """
        SELECT *
        FROM fridge_items
        WHERE fridge_id = %s
          AND quantity > 0
          AND (
              LOWER(display_name) IN (%s, %s)
              OR LOWER(REPLACE(REPLACE(display_name, '-', ' '), ' ', '_')) = %s
              OR LOWER(detected_name) IN (%s, %s)
              OR LOWER(REPLACE(REPLACE(detected_name, '-', ' '), ' ', '_')) = %s
          )
        ORDER BY updated_at DESC, fridge_item_id DESC
        LIMIT 1
        """,
        (
            fridge_id,
            normalized_name,
            human_name,
            normalized_name,
            normalized_name,
            human_name,
            normalized_name,
        ),
    )
    return cursor.fetchone()


@app.route("/health", methods=["GET"])
def health_check():
    return jsonify({"status": "ok"})


@app.route("/auth/register", methods=["POST"])
def register():
    payload = request.get_json(silent=True) or {}
    name = (payload.get("name") or "").strip()
    email = (payload.get("email") or "").strip().lower()
    password = payload.get("password") or ""

    if not name or not email or not password:
        return jsonify({"error": "Name, email and password are required."}), 400

    created_at = now_text()
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT user_id FROM users WHERE email = %s", (email,))
            if cursor.fetchone():
                return jsonify({"error": "This email is already registered."}), 409

            cursor.execute(
                """
                INSERT INTO users (name, email, password_hash, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (name, email, generate_password_hash(password), created_at, created_at),
            )
            user_id = cursor.lastrowid
            cursor.execute(
                """
                INSERT INTO fridges (user_id, fridge_name, created_at, updated_at)
                VALUES (%s, %s, %s, %s)
                """,
                (user_id, f"{name}'s Fridge", created_at, created_at),
            )
            fridge_id = cursor.lastrowid
            cursor.execute(
                "UPDATE users SET current_fridge_id = %s WHERE user_id = %s",
                (fridge_id, user_id),
            )
            set_active_fridge(cursor, fridge_id)
            conn.commit()

            cursor.execute("SELECT user_id, name, email, current_fridge_id FROM users WHERE user_id = %s", (user_id,))
            user_row = cursor.fetchone()
            cursor.execute(
                "SELECT fridge_id, fridge_name, created_at FROM fridges WHERE fridge_id = %s",
                (fridge_id,),
            )
            fridge_row = cursor.fetchone()

    return jsonify({"user": serialize_user(user_row), "fridges": [serialize_fridge(fridge_row)]}), 201


@app.route("/auth/login", methods=["POST"])
def login():
    payload = request.get_json(silent=True) or {}
    email = (payload.get("email") or "").strip().lower()
    password = payload.get("password") or ""

    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
            user_row = cursor.fetchone()
            if not user_row or not check_password_hash(user_row["password_hash"], password):
                return jsonify({"error": "Invalid email or password."}), 401

            cursor.execute(
                "SELECT fridge_id, fridge_name, created_at FROM fridges WHERE user_id = %s ORDER BY fridge_id",
                (user_row["user_id"],),
            )
            fridges = cursor.fetchall()

            current_fridge_id = user_row.get("current_fridge_id")
            if current_fridge_id is None and fridges:
                current_fridge_id = fridges[0]["fridge_id"]
                cursor.execute(
                    "UPDATE users SET current_fridge_id = %s, updated_at = %s WHERE user_id = %s",
                    (current_fridge_id, now_text(), user_row["user_id"]),
                )
            if current_fridge_id is not None:
                set_active_fridge(cursor, current_fridge_id)
            conn.commit()

            cursor.execute(
                "SELECT user_id, name, email, current_fridge_id FROM users WHERE user_id = %s",
                (user_row["user_id"],),
            )
            user_row = cursor.fetchone()

    return jsonify({"user": serialize_user(user_row), "fridges": [serialize_fridge(row) for row in fridges]})


@app.route("/fridges", methods=["GET"])
def list_fridges():
    user_id = request.args.get("user_id", type=int)
    if not user_id:
        return jsonify({"error": "user_id is required."}), 400

    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT fridge_id, fridge_name, created_at FROM fridges WHERE user_id = %s ORDER BY fridge_id",
                (user_id,),
            )
            rows = cursor.fetchall()
    return jsonify([serialize_fridge(row) for row in rows])


@app.route("/fridges", methods=["POST"])
def create_fridge():
    payload = request.get_json(silent=True) or {}
    user_id = payload.get("user_id")
    fridge_name = (payload.get("fridge_name") or "").strip()
    if not user_id or not fridge_name:
        return jsonify({"error": "user_id and fridge_name are required."}), 400

    created_at = now_text()
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT current_fridge_id FROM users WHERE user_id = %s", (user_id,))
            user_row = cursor.fetchone()
            cursor.execute(
                """
                INSERT INTO fridges (user_id, fridge_name, created_at, updated_at)
                VALUES (%s, %s, %s, %s)
                """,
                (user_id, fridge_name, created_at, created_at),
            )
            fridge_id = cursor.lastrowid
            if user_row and not user_row["current_fridge_id"]:
                cursor.execute(
                    "UPDATE users SET current_fridge_id = %s WHERE user_id = %s",
                    (fridge_id, user_id),
                )
                set_active_fridge(cursor, fridge_id)
            conn.commit()
            cursor.execute(
                "SELECT fridge_id, fridge_name, created_at FROM fridges WHERE fridge_id = %s",
                (fridge_id,),
            )
            row = cursor.fetchone()
    return jsonify(serialize_fridge(row)), 201


@app.route("/fridges/<int:fridge_id>", methods=["DELETE"])
def delete_fridge(fridge_id: int):
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT fridge_id, user_id FROM fridges WHERE fridge_id = %s", (fridge_id,))
            fridge_row = cursor.fetchone()
            if not fridge_row:
                return jsonify({"error": "Fridge not found."}), 404
            cursor.execute("SELECT current_fridge_id FROM users WHERE user_id = %s", (fridge_row["user_id"],))
            user_row = cursor.fetchone()
            cursor.execute("DELETE FROM fridges WHERE fridge_id = %s", (fridge_id,))
            if user_row and user_row["current_fridge_id"] == fridge_id:
                cursor.execute(
                    "SELECT fridge_id FROM fridges WHERE user_id = %s ORDER BY fridge_id LIMIT 1",
                    (fridge_row["user_id"],),
                )
                next_fridge = cursor.fetchone()
                cursor.execute(
                    "UPDATE users SET current_fridge_id = %s WHERE user_id = %s",
                    (next_fridge["fridge_id"] if next_fridge else None, fridge_row["user_id"]),
                )
                set_active_fridge(cursor, next_fridge["fridge_id"] if next_fridge else None)
        conn.commit()
    return jsonify({"message": "Fridge deleted."})


@app.route("/users/<int:user_id>/current-fridge", methods=["PUT"])
def update_current_fridge(user_id: int):
    payload = request.get_json(silent=True) or {}
    fridge_id = payload.get("fridge_id")
    if not fridge_id:
        return jsonify({"error": "fridge_id is required."}), 400

    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT user_id FROM users WHERE user_id = %s", (user_id,))
            if not cursor.fetchone():
                return jsonify({"error": "User not found."}), 404
            cursor.execute(
                "SELECT fridge_id FROM fridges WHERE fridge_id = %s AND user_id = %s",
                (fridge_id, user_id),
            )
            if not cursor.fetchone():
                return jsonify({"error": "Fridge does not belong to this user."}), 400
            cursor.execute(
                "UPDATE users SET current_fridge_id = %s, updated_at = %s WHERE user_id = %s",
                (fridge_id, now_text(), user_id),
            )
            set_active_fridge(cursor, fridge_id)
            conn.commit()
    return jsonify({"message": "Current fridge updated.", "fridge_id": fridge_id})


@app.route("/inventory", methods=["GET"])
def list_inventory():
    fridge_id = request.args.get("fridge_id", type=int)
    if not fridge_id:
        return jsonify({"error": "fridge_id is required."}), 400

    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT *
                FROM fridge_items
                WHERE fridge_id = %s
                ORDER BY CASE status WHEN 'UNRECOGNIZED' THEN 0 ELSE 1 END, updated_at DESC, fridge_item_id DESC
                """,
                (fridge_id,),
            )
            rows = cursor.fetchall()
    return jsonify([serialize_item(row) for row in rows])


@app.route("/inventory/<int:fridge_item_id>", methods=["GET"])
def get_inventory_item(fridge_item_id: int):
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM fridge_items WHERE fridge_item_id = %s", (fridge_item_id,))
            row = cursor.fetchone()
    if not row:
        return jsonify({"error": "Inventory item not found."}), 404
    return jsonify(serialize_item(row))


@app.route("/inventory", methods=["POST"])
def create_inventory_item():
    payload = request.get_json(silent=True) or {}
    fridge_id = payload.get("fridge_id")
    display_name = (payload.get("display_name") or "").strip()
    quantity = float(payload.get("quantity") or 1)
    unit = (payload.get("unit") or "개").strip()
    status = (payload.get("status") or "USER_CONFIRMED").strip().upper()
    note = (payload.get("note") or "").strip() or None

    if not fridge_id or not display_name:
        return jsonify({"error": "fridge_id and display_name are required."}), 400

    created_at = now_text()
    with get_connection() as conn:
        with conn.cursor() as cursor:
            ingredient = resolve_ingredient(cursor, display_name)
            cursor.execute(
                """
                INSERT INTO fridge_items (
                    fridge_id, ingredient_id, display_name, quantity, unit, status,
                    note, created_at, updated_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    fridge_id,
                    ingredient["ingredient_id"] if ingredient else None,
                    display_name,
                    quantity,
                    unit,
                    status,
                    note,
                    created_at,
                    created_at,
                ),
            )
            item_id = cursor.lastrowid
            conn.commit()
            cursor.execute("SELECT * FROM fridge_items WHERE fridge_item_id = %s", (item_id,))
            row = cursor.fetchone()
    return jsonify(serialize_item(row)), 201


@app.route("/inventory/<int:fridge_item_id>", methods=["PUT"])
def update_inventory_item(fridge_item_id: int):
    payload = request.get_json(silent=True) or {}
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM fridge_items WHERE fridge_item_id = %s", (fridge_item_id,))
            current = cursor.fetchone()
            if not current:
                return jsonify({"error": "Inventory item not found."}), 404

            display_name = (payload.get("display_name") or current["display_name"]).strip()
            quantity = float(payload.get("quantity") if payload.get("quantity") is not None else current["quantity"])
            unit = (payload.get("unit") or current["unit"]).strip()
            note = payload.get("note")
            note = current["note"] if note is None else (note.strip() or None)
            status = (payload.get("status") or current["status"]).strip().upper()
            ingredient = resolve_ingredient(cursor, display_name)

            cursor.execute(
                """
                UPDATE fridge_items
                SET ingredient_id = %s, display_name = %s, quantity = %s, unit = %s,
                    status = %s, note = %s, updated_at = %s
                WHERE fridge_item_id = %s
                """,
                (
                    ingredient["ingredient_id"] if ingredient else None,
                    display_name,
                    quantity,
                    unit,
                    status,
                    note,
                    now_text(),
                    fridge_item_id,
                ),
            )
            conn.commit()
            cursor.execute("SELECT * FROM fridge_items WHERE fridge_item_id = %s", (fridge_item_id,))
            row = cursor.fetchone()
    return jsonify(serialize_item(row))


@app.route("/inventory/<int:fridge_item_id>", methods=["DELETE"])
def delete_inventory_item(fridge_item_id: int):
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT fridge_item_id FROM fridge_items WHERE fridge_item_id = %s", (fridge_item_id,))
            if not cursor.fetchone():
                return jsonify({"error": "Inventory item not found."}), 404
            cursor.execute("DELETE FROM fridge_items WHERE fridge_item_id = %s", (fridge_item_id,))
        conn.commit()
    return jsonify({"message": "Inventory item deleted."})


@app.route("/consume", methods=["POST"])
def consume_detection():
    payload = request.get_json(silent=True) or {}
    fridge_id = request.form.get("fridge_id", type=int)
    if fridge_id is None and payload.get("fridge_id") is not None:
        try:
            fridge_id = int(payload["fridge_id"])
        except (TypeError, ValueError):
            return jsonify({"error": "fridge_id must be a number."}), 400

    display_name = (
        request.form.get("label")
        or request.form.get("display_name")
        or payload.get("label")
        or payload.get("display_name")
        or ""
    ).strip()
    detected_name = (
        request.form.get("detected_name")
        or payload.get("detected_name")
        or display_name
    ).strip() or None

    try:
        quantity = parse_float_value(
            request.form.get("quantity")
            if request.form.get("quantity") is not None
            else payload.get("quantity"),
            1,
        )
        confidence = parse_float_value(
            request.form.get("confidence")
            if request.form.get("confidence") is not None
            else payload.get("confidence"),
        )
    except (TypeError, ValueError):
        return jsonify({"error": "quantity and confidence must be numbers."}), 400

    if not display_name:
        return jsonify({"error": "label or display_name is required."}), 400
    if quantity is None or quantity <= 0:
        return jsonify({"error": "quantity must be greater than 0."}), 400

    image = request.files.get("image")
    crop_image = request.files.get("crop_image")

    with get_connection() as conn:
        with conn.cursor() as cursor:
            fridge_id = resolve_target_fridge_id(cursor, fridge_id)
            if not fridge_id:
                return jsonify({"error": "No fridge is available for consume."}), 400

            ingredient = resolve_ingredient(cursor, display_name)
            current = find_consumable_item(cursor, fridge_id, display_name, ingredient)
            if not current:
                return jsonify(
                    {
                        "consumed": False,
                        "reason": "not_found",
                        "display_name": display_name,
                        "detected_name": detected_name,
                        "quantity": quantity,
                        "fridge_id": fridge_id,
                    }
                )

            remaining_quantity = float(current["quantity"]) - quantity
            if remaining_quantity <= 0:
                cursor.execute(
                    "DELETE FROM fridge_items WHERE fridge_item_id = %s",
                    (current["fridge_item_id"],),
                )
                conn.commit()
                return jsonify(
                    {
                        "consumed": True,
                        "deleted": True,
                        "remaining_quantity": 0,
                        "quantity": quantity,
                        "item": serialize_item(current),
                    }
                )

            image_path, crop_path = save_detection_files(image, crop_image)
            cursor.execute(
                """
                UPDATE fridge_items
                SET quantity = %s,
                    image_path = %s,
                    crop_image_path = %s,
                    confidence = %s,
                    detected_name = %s,
                    updated_at = %s
                WHERE fridge_item_id = %s
                """,
                (
                    remaining_quantity,
                    str(image_path) if image_path else current["image_path"],
                    str(crop_path) if crop_path else current["crop_image_path"],
                    confidence if confidence is not None else current["confidence"],
                    detected_name or current["detected_name"],
                    now_text(),
                    current["fridge_item_id"],
                ),
            )
            conn.commit()
            cursor.execute(
                "SELECT * FROM fridge_items WHERE fridge_item_id = %s",
                (current["fridge_item_id"],),
            )
            row = cursor.fetchone()

    return jsonify(
        {
            "consumed": True,
            "deleted": False,
            "remaining_quantity": row["quantity"],
            "quantity": quantity,
            "item": serialize_item(row),
        }
    )


@app.route("/recipes", methods=["GET"])
def list_recipes():
    fridge_id = request.args.get("fridge_id", type=int)
    query = (request.args.get("q") or "").strip().lower()

    with get_connection() as conn:
        with conn.cursor() as cursor:
            owned_names = set()
            if fridge_id:
                cursor.execute(
                    """
                    SELECT COALESCE(i.name, LOWER(fi.display_name)) AS normalized_name
                    FROM fridge_items fi
                    LEFT JOIN ingredients i ON i.ingredient_id = fi.ingredient_id
                    WHERE fi.fridge_id = %s
                    """,
                    (fridge_id,),
                )
                owned_names = {row["normalized_name"] for row in cursor.fetchall()}

            cursor.execute(
                """
                SELECT recipe_id, name, description, cooking_time, difficulty
                FROM recipes
                WHERE LOWER(name) LIKE %s
                ORDER BY name
                """,
                (f"%{query}%",),
            )
            recipe_rows = cursor.fetchall()

            results = []
            for recipe in recipe_rows:
                cursor.execute(
                    """
                    SELECT ri.quantity, ri.unit, ing.name
                    FROM recipe_ingredients ri
                    JOIN ingredients ing ON ing.ingredient_id = ri.ingredient_id
                    WHERE ri.recipe_id = %s
                    ORDER BY ing.name
                    """,
                    (recipe["recipe_id"],),
                )
                required_rows = cursor.fetchall()
                missing = [
                    {"name": row["name"], "quantity": row["quantity"], "unit": row["unit"]}
                    for row in required_rows
                    if row["name"] not in owned_names
                ]
                matched_count = len(required_rows) - len(missing)
                results.append(
                    {
                        "recipe_id": recipe["recipe_id"],
                        "name": recipe["name"],
                        "description": recipe["description"],
                        "cooking_time": recipe["cooking_time"],
                        "difficulty": recipe["difficulty"],
                        "matched_count": matched_count,
                        "required_count": len(required_rows),
                        "missing_count": len(missing),
                        "missing_ingredients": missing,
                    }
                )

    results.sort(key=lambda item: (item["missing_count"], -item["matched_count"], item["name"].lower()))
    return jsonify(results)


@app.route("/recipes/<int:recipe_id>", methods=["GET"])
def get_recipe(recipe_id: int):
    fridge_id = request.args.get("fridge_id", type=int)

    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM recipes WHERE recipe_id = %s", (recipe_id,))
            recipe = cursor.fetchone()
            if not recipe:
                return jsonify({"error": "Recipe not found."}), 404

            cursor.execute(
                """
                SELECT ing.name, ri.quantity, ri.unit
                FROM recipe_ingredients ri
                JOIN ingredients ing ON ing.ingredient_id = ri.ingredient_id
                WHERE ri.recipe_id = %s
                ORDER BY ing.name
                """,
                (recipe_id,),
            )
            required_rows = cursor.fetchall()

            owned_names = set()
            if fridge_id:
                cursor.execute(
                    """
                    SELECT COALESCE(i.name, LOWER(fi.display_name)) AS normalized_name
                    FROM fridge_items fi
                    LEFT JOIN ingredients i ON i.ingredient_id = fi.ingredient_id
                    WHERE fi.fridge_id = %s
                    """,
                    (fridge_id,),
                )
                owned_names = {row["normalized_name"] for row in cursor.fetchall()}

    required = []
    missing = []
    for row in required_rows:
        item = {"name": row["name"], "quantity": row["quantity"], "unit": row["unit"]}
        required.append(item)
        if row["name"] not in owned_names:
            missing.append(item)

    return jsonify(
        {
            "recipe_id": recipe["recipe_id"],
            "name": recipe["name"],
            "description": recipe["description"],
            "instructions": recipe["instructions"],
            "cooking_time": recipe["cooking_time"],
            "difficulty": recipe["difficulty"],
            "required_ingredients": required,
            "missing_ingredients": missing,
        }
    )


@app.route("/upload", methods=["POST"])
def upload_detection():
    if "image" not in request.files:
        return jsonify({"error": "image file is required."}), 400

    image = request.files["image"]
    crop_image = request.files.get("crop_image")
    fridge_id = request.form.get("fridge_id", type=int)
    display_name = (request.form.get("label") or request.form.get("display_name") or "").strip()
    detected_name = (request.form.get("detected_name") or display_name).strip() or None
    confidence = request.form.get("confidence", type=float)
    quantity = request.form.get("quantity", type=float) or 1
    unit = (request.form.get("unit") or "개").strip()

    if image.filename == "":
        return jsonify({"error": "image filename is empty."}), 400
    image_path, crop_path = save_detection_files(image, crop_image)

    created_at = now_text()
    with get_connection() as conn:
        with conn.cursor() as cursor:
            fridge_id = resolve_target_fridge_id(cursor, fridge_id)
            if not fridge_id:
                return jsonify({"error": "No fridge is available for upload."}), 400

            ingredient = resolve_ingredient(cursor, display_name)
            status = "RECOGNIZED" if ingredient else "UNRECOGNIZED"
            if not display_name:
                display_name = "Unknown Item"

            cursor.execute(
                """
                INSERT INTO fridge_items (
                    fridge_id, ingredient_id, display_name, quantity, unit, status,
                    image_path, crop_image_path, confidence, detected_name, created_at, updated_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    fridge_id,
                    ingredient["ingredient_id"] if ingredient else None,
                    display_name,
                    quantity,
                    unit,
                    status,
                    str(image_path),
                    str(crop_path) if crop_path else None,
                    confidence,
                    detected_name,
                    created_at,
                    created_at,
                ),
            )
            item_id = cursor.lastrowid
            conn.commit()
            cursor.execute("SELECT * FROM fridge_items WHERE fridge_item_id = %s", (item_id,))
            row = cursor.fetchone()

    return jsonify(serialize_item(row)), 201


@app.route("/uploads/<path:filename>", methods=["GET"])
def serve_uploaded_file(filename: str):
    filename_path = Path(filename)
    if filename_path.parts and filename_path.parts[0] == "crops":
        return send_from_directory(CROP_FOLDER, os.path.basename(filename))
    return send_from_directory(UPLOAD_FOLDER, os.path.basename(filename))


init_db()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
