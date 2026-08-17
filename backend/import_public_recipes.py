from __future__ import annotations

import json
import os
import re
from collections import defaultdict
from urllib.parse import quote
from urllib.request import urlopen

from app import get_connection, normalize_ingredient_name, normalize_unit, now_text

API_HOST = os.environ.get("MAFRA_RECIPE_API_HOST", "http://211.237.50.150:7080")
API_KEY = os.environ.get("MAFRA_RECIPE_API_KEY", "sample")
IMPORT_LIMIT = int(os.environ.get("MAFRA_RECIPE_IMPORT_LIMIT", "50"))
MAX_RELATED_ROWS = int(os.environ.get("MAFRA_RECIPE_MAX_RELATED_ROWS", "5000"))
SOURCE_NAME = "농림축산식품 공공데이터 안심 레시피"
SOURCE_URL = "https://data.mafra.go.kr/opendata/data/indexOpenDataDetail.do?data_id=20150827000000000464"

INFO_SERVICE = "Grid_20150827000000000226_1"
INGREDIENT_SERVICE = "Grid_20150827000000000227_1"
STEP_SERVICE = "Grid_20150827000000000228_1"

INGREDIENT_ALIASES = {
    "달걀": "egg",
    "계란": "egg",
    "쌀": "rice",
    "밥": "rice",
    "쇠고기": "beef",
    "소고기": "beef",
    "돼지고기": "pork",
    "닭고기": "chicken",
    "양송이버섯": "mushroom",
    "표고버섯": "mushroom",
    "청양고추": "고추",
    "홍고추": "고추",
}


def fetch_rows(service: str, end_index: int) -> list[dict]:
    page_size = 5 if API_KEY == "sample" else 1000
    rows: list[dict] = []
    start = 1
    while start <= end_index:
        end = min(end_index, start + page_size - 1)
        url = (
            f"{API_HOST}/openapi/{quote(API_KEY, safe='')}/json/"
            f"{service}/{start}/{end}"
        )
        with urlopen(url, timeout=30) as response:
            payload = json.loads(response.read().decode("utf-8"))
        top_level_result = payload.get("result") or {}
        if top_level_result:
            code = top_level_result.get("code")
            message = top_level_result.get("message") or "공공 레시피 API 호출에 실패했습니다."
            raise RuntimeError(f"{code or '알 수 없는 오류'}: {message}")
        container = payload.get(service) or {}
        if not container:
            raise RuntimeError(
                f"공공 레시피 API 응답에 {service} 데이터가 없습니다."
            )
        result = container.get("result") or {}
        if result.get("code") not in {None, "INFO-000"}:
            raise RuntimeError(result.get("message") or "공공 레시피 API 호출에 실패했습니다.")
        page_rows = container.get("row") or []
        rows.extend(page_rows)
        total = int(container.get("totalCnt") or len(rows))
        if end >= total or not page_rows or API_KEY == "sample":
            break
        start = end + 1
    return rows


def first_number(value: str | None, default: int) -> int:
    match = re.search(r"\d+", value or "")
    return int(match.group()) if match else default


def normalize_difficulty(value: str | None) -> str:
    text = (value or "").strip()
    if text in {"초보환영", "매우 쉬움", "쉬움"}:
        return "쉬움"
    if text in {"어려움", "매우 어려움"}:
        return "어려움"
    return "보통"


def parse_quantity(value: str | None) -> tuple[float, str]:
    text = (value or "").strip().replace(" ", "")
    fraction = re.match(r"(\d+)\s*/\s*(\d+)", text)
    decimal = re.match(r"(\d+(?:\.\d+)?)", text)
    if fraction:
        denominator = float(fraction.group(2))
        quantity = float(fraction.group(1)) / denominator if denominator else 1.0
        remainder = text[fraction.end() :]
    elif decimal:
        quantity = float(decimal.group(1))
        remainder = text[decimal.end() :]
    else:
        quantity = 1.0
        remainder = text

    unit_text = remainder.strip("()[]") or "적당량"
    unit_text = re.sub(r"^약", "", unit_text) or "적당량"
    return quantity, normalize_unit(unit_text)


def canonical_ingredient_name(raw_name: str) -> str:
    clean_name = re.sub(r"\([^)]*\)", "", raw_name).strip()
    clean_name = INGREDIENT_ALIASES.get(clean_name, clean_name)
    return normalize_ingredient_name(clean_name) or clean_name


def main() -> None:
    info_limit = min(5, IMPORT_LIMIT) if API_KEY == "sample" else IMPORT_LIMIT
    info_rows = fetch_rows(INFO_SERVICE, info_limit)
    ingredient_rows = fetch_rows(INGREDIENT_SERVICE, MAX_RELATED_ROWS)
    step_rows = fetch_rows(STEP_SERVICE, MAX_RELATED_ROWS)

    ingredients_by_recipe: dict[str, list[dict]] = defaultdict(list)
    steps_by_recipe: dict[str, list[dict]] = defaultdict(list)
    for row in ingredient_rows:
        ingredients_by_recipe[str(row.get("RECIPE_ID"))].append(row)
    for row in step_rows:
        steps_by_recipe[str(row.get("RECIPE_ID"))].append(row)

    imported = 0
    skipped = 0
    with get_connection() as conn:
        with conn.cursor() as cursor:
            for info in info_rows:
                external_id = str(info.get("RECIPE_ID") or "").strip()
                recipe_ingredients = ingredients_by_recipe.get(external_id, [])
                recipe_steps = steps_by_recipe.get(external_id, [])
                if not external_id or not recipe_ingredients or not recipe_steps:
                    skipped += 1
                    continue

                recipe_steps.sort(key=lambda row: int(row.get("COOKING_NO") or 0))
                instructions = "\n".join(
                    f"{index}. {(row.get('COOKING_DC') or '').strip()}"
                    for index, row in enumerate(recipe_steps, 1)
                    if (row.get("COOKING_DC") or "").strip()
                )
                now = now_text()
                values = (
                    str(info.get("RECIPE_NM_KO") or "이름 없는 레시피").strip(),
                    str(info.get("SUMRY") or "공공데이터에서 제공한 레시피입니다.").strip(),
                    instructions,
                    first_number(info.get("COOKING_TIME"), 30),
                    normalize_difficulty(info.get("LEVEL_NM")),
                    None if info.get("IMG_URL") in {None, "", "null"} else info.get("IMG_URL"),
                    SOURCE_NAME,
                    SOURCE_URL,
                    external_id,
                    str(info.get("CALORIE") or "").strip() or None,
                    now,
                )
                cursor.execute(
                    """
                    SELECT recipe_id FROM recipes
                    WHERE source_name = %s AND external_id = %s
                    """,
                    (SOURCE_NAME, external_id),
                )
                current = cursor.fetchone()
                if current:
                    recipe_id = current["recipe_id"]
                    cursor.execute(
                        """
                        UPDATE recipes
                        SET name=%s, description=%s, instructions=%s, cooking_time=%s,
                            difficulty=%s, image_url=%s, source_name=%s, source_url=%s,
                            external_id=%s, calories=%s, updated_at=%s
                        WHERE recipe_id=%s
                        """,
                        values + (recipe_id,),
                    )
                    cursor.execute(
                        "DELETE FROM recipe_ingredients WHERE recipe_id = %s",
                        (recipe_id,),
                    )
                else:
                    cursor.execute(
                        """
                        INSERT INTO recipes (
                            name, description, instructions, cooking_time, difficulty,
                            image_url, source_name, source_url, external_id, calories,
                            created_at, updated_at
                        ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                        """,
                        values + (now,),
                    )
                    recipe_id = cursor.lastrowid

                merged: dict[str, tuple[float, str]] = {}
                for item in recipe_ingredients:
                    raw_name = str(item.get("IRDNT_NM") or "").strip()
                    if not raw_name:
                        continue
                    name = canonical_ingredient_name(raw_name)
                    quantity, unit = parse_quantity(item.get("IRDNT_CPCTY"))
                    existing_quantity, existing_unit = merged.get(name, (0.0, unit))
                    merged[name] = (
                        existing_quantity + quantity if existing_unit == unit else max(existing_quantity, quantity),
                        existing_unit,
                    )

                for name, (quantity, unit) in merged.items():
                    cursor.execute(
                        """
                        INSERT INTO ingredients (name, category, created_at, updated_at)
                        VALUES (%s, '기타', %s, %s)
                        ON DUPLICATE KEY UPDATE updated_at = VALUES(updated_at)
                        """,
                        (name, now, now),
                    )
                    cursor.execute(
                        "SELECT ingredient_id FROM ingredients WHERE name = %s",
                        (name,),
                    )
                    ingredient_id = cursor.fetchone()["ingredient_id"]
                    cursor.execute(
                        """
                        INSERT INTO recipe_ingredients (recipe_id, ingredient_id, quantity, unit)
                        VALUES (%s, %s, %s, %s)
                        """,
                        (recipe_id, ingredient_id, quantity, unit),
                    )
                imported += 1
        conn.commit()

    print(f"공공 레시피 가져오기 완료: {imported}개, 건너뜀: {skipped}개")
    if API_KEY == "sample":
        print("현재 sample 키는 5행만 제공됩니다. 전체 가져오기는 MAFRA_RECIPE_API_KEY를 설정하세요.")


if __name__ == "__main__":
    main()
