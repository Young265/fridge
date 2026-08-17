from __future__ import annotations

import json
import os
import re
from urllib.parse import quote
from urllib.request import urlopen

from app import get_connection, normalize_ingredient_name, normalize_unit, now_text


API_KEY = os.environ.get("MFDS_RECIPE_API_KEY", "sample")
API_HOST = "https://openapi.foodsafetykorea.go.kr/api"
SERVICE = "COOKRCP01"
SOURCE_NAME = "식품의약품안전처 조리식품 레시피 DB"
SOURCE_URL = "https://www.data.go.kr/data/15060073/openapi.do"


def https_url(value: str | None) -> str | None:
    url = (value or "").strip()
    if not url:
        return None
    return re.sub(r"^http://", "https://", url)


def fetch_rows() -> list[dict]:
    rows: list[dict] = []
    start = 1
    page_size = 5 if API_KEY == "sample" else 500
    total = page_size
    while start <= total:
        end = start + page_size - 1
        url = (
            f"{API_HOST}/{quote(API_KEY, safe='')}/{SERVICE}/json/{start}/{end}"
        )
        with urlopen(url, timeout=60) as response:
            payload = json.loads(response.read().decode("utf-8"))
        container = payload.get(SERVICE) or {}
        result = container.get("RESULT") or {}
        if result.get("CODE") not in {None, "INFO-000"}:
            raise RuntimeError(result.get("MSG") or "식약처 레시피 API 호출 실패")
        page_rows = container.get("row") or []
        rows.extend(page_rows)
        total = int(container.get("total_count") or len(rows))
        if not page_rows or API_KEY == "sample":
            break
        start = end + 1
    return rows


def clean_step(value: str | None) -> str:
    text = re.sub(r"^\s*\d+[.)]\s*", "", value or "").strip()
    return re.sub(r"\s+", " ", text)


def parse_amount(value: str) -> tuple[float, str]:
    text = value.strip()
    mixed = re.search(r"(\d+)\s*[½]", text)
    fraction = re.search(r"(\d+)\s*/\s*(\d+)", text)
    decimal = re.search(r"(\d+(?:\.\d+)?)", text)
    if mixed:
        quantity = float(mixed.group(1)) + 0.5
    elif fraction:
        denominator = float(fraction.group(2))
        quantity = float(fraction.group(1)) / denominator if denominator else 1.0
    elif decimal:
        quantity = float(decimal.group(1))
    else:
        quantity = 1.0

    unit_match = re.search(
        r"(kg|g|ml|L|개|마리|모|큰술|작은술|컵|봉지|장|줄기|쪽|알|줌)", text,
        re.IGNORECASE,
    )
    raw_unit = unit_match.group(1) if unit_match else "적당량"
    unit_map = {"마리": "개", "모": "개", "줌": "적당량"}
    unit = normalize_unit(unit_map.get(raw_unit, raw_unit))
    return quantity, unit


def parse_ingredients(value: str | None) -> list[tuple[str, float, str]]:
    text = (value or "").replace("\r", "\n")
    chunks = re.split(r"[,;·]|\n", text)
    merged: dict[str, tuple[float, str]] = {}
    for chunk in chunks:
        clean = re.sub(r"^[●•\-\s]+", "", chunk).strip()
        clean = re.sub(r"^\[[^]]+]\s*", "", clean).strip()
        if not clean or clean.endswith(":") or clean.endswith("장") and not re.search(r"\d", clean):
            continue
        amount_start = re.search(r"\d|약간|적당량|조금", clean)
        if amount_start:
            raw_name = clean[: amount_start.start()].strip(" :")
            amount_text = clean[amount_start.start() :]
        else:
            raw_name = clean.strip(" :")
            amount_text = "적당량"
        raw_name = re.sub(r"\([^)]*$", "", raw_name).strip()
        if not raw_name or len(raw_name) > 100:
            continue
        name = normalize_ingredient_name(raw_name) or raw_name
        quantity, unit = parse_amount(amount_text)
        old_quantity, old_unit = merged.get(name, (0.0, unit))
        merged[name] = (
            old_quantity + quantity if old_unit == unit else max(old_quantity, quantity),
            old_unit,
        )
    return [(name, quantity, unit) for name, (quantity, unit) in merged.items()]


def main() -> None:
    rows = fetch_rows()
    imported = 0
    skipped = 0
    with get_connection() as conn:
        with conn.cursor() as cursor:
            for row in rows:
                external_id = str(row.get("RCP_SEQ") or "").strip()
                name = str(row.get("RCP_NM") or "").strip()
                ingredients = parse_ingredients(row.get("RCP_PARTS_DTLS"))
                steps = []
                for number in range(1, 21):
                    description = clean_step(row.get(f"MANUAL{number:02d}"))
                    if description:
                        steps.append(
                            (
                                number,
                                description,
                                https_url(row.get(f"MANUAL_IMG{number:02d}")),
                            )
                        )
                if not external_id or not name or not ingredients or not steps:
                    skipped += 1
                    continue

                instructions = "\n".join(
                    f"{index}. {description}"
                    for index, (_, description, _) in enumerate(steps, 1)
                )
                description = str(row.get("RCP_NA_TIP") or "").strip()
                if not description:
                    description = (
                        f"{row.get('RCP_PAT2') or '요리'} · "
                        f"{row.get('RCP_WAY2') or '조리'} 레시피입니다."
                    )
                calories = str(row.get("INFO_ENG") or "").strip()
                calories = f"{calories}킬로칼로리" if calories else None
                now = now_text()
                values = (
                    name[:200], description, instructions, 30, "보통",
                    https_url(row.get("ATT_FILE_NO_MAIN") or row.get("ATT_FILE_NO_MK")),
                    SOURCE_NAME, SOURCE_URL, external_id, calories,
                )
                cursor.execute(
                    "SELECT recipe_id FROM recipes WHERE source_name=%s AND external_id=%s",
                    (SOURCE_NAME, external_id),
                )
                current = cursor.fetchone()
                if current:
                    recipe_id = current["recipe_id"]
                    cursor.execute(
                        """
                        UPDATE recipes SET name=%s, description=%s, instructions=%s,
                            cooking_time=%s, difficulty=%s, image_url=%s,
                            source_name=%s, source_url=%s, external_id=%s,
                            calories=%s, updated_at=%s WHERE recipe_id=%s
                        """,
                        values + (now, recipe_id),
                    )
                    cursor.execute("DELETE FROM recipe_ingredients WHERE recipe_id=%s", (recipe_id,))
                    cursor.execute("DELETE FROM recipe_steps WHERE recipe_id=%s", (recipe_id,))
                else:
                    cursor.execute(
                        """
                        INSERT INTO recipes (
                            name, description, instructions, cooking_time, difficulty,
                            image_url, source_name, source_url, external_id, calories,
                            created_at, updated_at
                        ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                        """,
                        values + (now, now),
                    )
                    recipe_id = cursor.lastrowid

                for raw_name, quantity, unit in ingredients:
                    cursor.execute(
                        """
                        INSERT INTO ingredients (name, category, created_at, updated_at)
                        VALUES (%s, '기타', %s, %s)
                        ON DUPLICATE KEY UPDATE updated_at=VALUES(updated_at)
                        """,
                        (raw_name, now, now),
                    )
                    cursor.execute("SELECT ingredient_id FROM ingredients WHERE name=%s", (raw_name,))
                    ingredient_id = cursor.fetchone()["ingredient_id"]
                    cursor.execute(
                        """
                        INSERT INTO recipe_ingredients (recipe_id, ingredient_id, quantity, unit)
                        VALUES (%s,%s,%s,%s)
                        ON DUPLICATE KEY UPDATE quantity=VALUES(quantity), unit=VALUES(unit)
                        """,
                        (recipe_id, ingredient_id, quantity, unit),
                    )
                for step_number, step_description, image_url in steps:
                    cursor.execute(
                        """
                        INSERT INTO recipe_steps
                            (recipe_id, step_number, description, image_url)
                        VALUES (%s,%s,%s,%s)
                        """,
                        (recipe_id, step_number, step_description, image_url),
                    )
                imported += 1
                if imported % 200 == 0:
                    conn.commit()
                    print(f"{imported:,}/{len(rows):,}개 처리")
        conn.commit()
    print(f"식약처 레시피 가져오기 완료: {imported:,}개, 건너뜀: {skipped:,}개")


if __name__ == "__main__":
    main()
