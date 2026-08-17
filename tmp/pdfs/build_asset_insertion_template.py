from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from reportlab.lib.pagesizes import A4, landscape
from reportlab.pdfgen import canvas


ROOT = Path(__file__).resolve().parents[2]
SOURCE_DIR = ROOT / "tmp" / "pdfs" / "official_form_pages"
PAGE_DIR = ROOT / "tmp" / "pdfs" / "asset_insertion_pages"
OUTPUT_PDF = ROOT / "output" / "pdf" / "2026_제작설계서_응용하드웨어_AI스마트냉장고_자료삽입대기본.pdf"
CONTACT_SHEET = ROOT / "tmp" / "pdfs" / "asset_insertion_contact_sheet.jpg"

FONT_REGULAR = Path("C:/Windows/Fonts/malgun.ttf")
FONT_BOLD = Path("C:/Windows/Fonts/malgunbd.ttf")

BLUE = (38, 99, 147)
NAVY = (33, 51, 73)
GREEN = (47, 107, 79)
ORANGE = (194, 91, 42)
BURGUNDY = (143, 53, 48)
MID_GRAY = (205, 216, 230)
TEXT = (63, 75, 91)
LIGHT_BLUE = (238, 246, 252)
LIGHT_GREEN = (236, 247, 241)
LIGHT_ORANGE = (255, 242, 234)
LIGHT_GRAY = (247, 249, 252)
WHITE = (255, 255, 255)
DARK_CODE = (23, 32, 44)


SOURCE_PAGES = [1, 2, 3, 4, *range(7, 37)]


def source_page_path(page_number: int) -> Path:
    return SOURCE_DIR / f"page-{page_number:02d}.jpg"


def font(path: Path, size: int) -> ImageFont.FreeTypeFont:
    if not path.exists():
        raise FileNotFoundError(f"Korean font not found: {path}")
    return ImageFont.truetype(str(path), max(8, size))


def fnt(image: Image.Image, points: float, bold: bool = False) -> ImageFont.FreeTypeFont:
    scale = image.height / 595.0
    return font(FONT_BOLD if bold else FONT_REGULAR, round(points * scale))


def text_width(draw: ImageDraw.ImageDraw, text: str, use_font: ImageFont.FreeTypeFont) -> float:
    box = draw.textbbox((0, 0), text, font=use_font)
    return box[2] - box[0]


def wrap_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    use_font: ImageFont.FreeTypeFont,
    max_width: int,
) -> list[str]:
    lines: list[str] = []
    for paragraph in text.split("\n"):
        if not paragraph:
            lines.append("")
            continue
        words = paragraph.split(" ")
        current = ""
        for word in words:
            candidate = word if not current else f"{current} {word}"
            if text_width(draw, candidate, use_font) <= max_width:
                current = candidate
                continue
            if current:
                lines.append(current)
                current = ""
            if text_width(draw, word, use_font) <= max_width:
                current = word
                continue
            chunk = ""
            for char in word:
                test = chunk + char
                if chunk and text_width(draw, test, use_font) > max_width:
                    lines.append(chunk)
                    chunk = char
                else:
                    chunk = test
            current = chunk
        if current:
            lines.append(current)
    return lines


def draw_wrapped(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int],
    text: str,
    use_font: ImageFont.FreeTypeFont,
    max_width: int,
    fill=TEXT,
    leading: float = 1.35,
    max_lines: int | None = None,
) -> int:
    x, y = xy
    lines = wrap_text(draw, text, use_font, max_width)
    if max_lines is not None:
        lines = lines[:max_lines]
    line_height = round(use_font.size * leading)
    for line in lines:
        draw.text((x, y), line, font=use_font, fill=fill)
        y += line_height
    return y


def dashed_line(
    draw: ImageDraw.ImageDraw,
    start: tuple[int, int],
    end: tuple[int, int],
    fill,
    width: int,
    dash: int,
    gap: int,
) -> None:
    x1, y1 = start
    x2, y2 = end
    length = ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5
    if length == 0:
        return
    dx = (x2 - x1) / length
    dy = (y2 - y1) / length
    pos = 0.0
    while pos < length:
        stop = min(length, pos + dash)
        draw.line(
            (
                round(x1 + dx * pos),
                round(y1 + dy * pos),
                round(x1 + dx * stop),
                round(y1 + dy * stop),
            ),
            fill=fill,
            width=width,
        )
        pos += dash + gap


def dashed_rect(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    fill=BLUE,
    width: int = 4,
    dash: int = 18,
    gap: int = 10,
) -> None:
    x1, y1, x2, y2 = box
    dashed_line(draw, (x1, y1), (x2, y1), fill, width, dash, gap)
    dashed_line(draw, (x2, y1), (x2, y2), fill, width, dash, gap)
    dashed_line(draw, (x2, y2), (x1, y2), fill, width, dash, gap)
    dashed_line(draw, (x1, y2), (x1, y1), fill, width, dash, gap)


def content_bounds(image: Image.Image) -> tuple[int, int, int, int]:
    width, height = image.size
    return (
        round(width * 0.055),
        round(height * 0.205),
        round(width * 0.945),
        round(height * 0.925),
    )


def clear_body(image: Image.Image) -> ImageDraw.ImageDraw:
    draw = ImageDraw.Draw(image)
    width, height = image.size
    draw.rectangle(
        (
            round(width * 0.030),
            round(height * 0.195),
            round(width * 0.985),
            round(height * 0.945),
        ),
        fill=WHITE,
    )
    # Keep the form's narrow left design rail visible.
    draw.rectangle(
        (0, round(height * 0.195), round(width * 0.018), round(height * 0.925)),
        fill=BLUE,
    )
    return draw


def guide_badge(image: Image.Image, draw: ImageDraw.ImageDraw, text: str = "사용자 제작 자료 삽입") -> None:
    x1, y1, x2, _ = content_bounds(image)
    use_font = fnt(image, 8.2, bold=True)
    width = round(image.width * 0.145)
    height = round(image.height * 0.036)
    bx1 = x2 - width
    by1 = y1 - round(image.height * 0.005)
    draw.rounded_rectangle((bx1, by1, x2, by1 + height), radius=12, fill=LIGHT_ORANGE, outline=ORANGE, width=2)
    draw.text(((bx1 + x2) // 2, by1 + height // 2), text, font=use_font, fill=ORANGE, anchor="mm")


def insertion_box(
    image: Image.Image,
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    title: str,
    instructions: str,
    filename: str,
    accent=BLUE,
    fill=LIGHT_BLUE,
) -> None:
    x1, y1, x2, y2 = box
    draw.rounded_rectangle(box, radius=18, fill=fill, outline=MID_GRAY, width=2)
    dashed_rect(draw, (x1 + 4, y1 + 4, x2 - 4, y2 - 4), fill=accent, width=3)
    header_h = max(48, round((y2 - y1) * 0.16))
    draw.rounded_rectangle((x1, y1, x2, y1 + header_h), radius=18, fill=accent)
    draw.rectangle((x1, y1 + header_h - 18, x2, y1 + header_h), fill=accent)
    title_font = fnt(image, 10.5, bold=True)
    body_font = fnt(image, 8.2)
    file_font = fnt(image, 7.5, bold=True)
    draw.text((x1 + 22, y1 + header_h // 2), title, font=title_font, fill=WHITE, anchor="lm")
    body_y = y1 + header_h + 20
    draw_wrapped(draw, (x1 + 24, body_y), instructions, body_font, x2 - x1 - 48, fill=TEXT, leading=1.42)
    draw.text((x1 + 24, y2 - file_font.size - 22), f"권장 파일명: {filename}", font=file_font, fill=accent)


def draw_note_footer(image: Image.Image, draw: ImageDraw.ImageDraw) -> None:
    x1, _, x2, y2 = content_bounds(image)
    use_font = fnt(image, 7.3)
    draw.text(
        (x1, y2 + round(image.height * 0.012)),
        "※ 상세 제작법·출처·코드 줄번호는 함께 제공한 '시각자료 제작 가이드' 참조",
        font=use_font,
        fill=ORANGE,
    )


def draw_updated_output_table(image: Image.Image) -> None:
    draw = clear_body(image)
    x1, y1, x2, y2 = content_bounds(image)
    table_top = y1 + 34
    table_bottom = y2 - 70
    rows = [
        ("환경분석", "시장/기술 환경 분석서", "선택 포함", "3-4p"),
        ("요구사항분석", "요구사항 정의서, 유즈케이스 정의서", "필수/선택 포함", "5-7p"),
        ("아키텍처설계", "서비스 구성도, 서비스 흐름도, UI/UX, H/W·센서 구성도", "필수 포함", "8-12p"),
        ("기능설계", "메뉴, 화면, ERD, 기능처리도, 알고리즘 명세", "필수 포함", "13-23p"),
        ("개발/구현", "H/W 설계도, 프로그램 목록, 테이블 정의서, 핵심 소스", "필수 포함", "24-28p"),
        ("참조", "개발환경, S/W·H/W 실사, 동영상 콘티, 프로젝트 관리", "참조 포함", "29-33p"),
    ]
    widths = [0.18, 0.57, 0.16, 0.09]
    xs = [x1]
    for fraction in widths:
        xs.append(xs[-1] + round((x2 - x1) * fraction))
    header_h = 64
    row_h = (table_bottom - table_top - header_h) // len(rows)
    headers = ["단계", "산출물", "적용", "수록"]
    head_font = fnt(image, 9.2, bold=True)
    body_font = fnt(image, 8.3)
    for column in range(4):
        draw.rectangle((xs[column], table_top, xs[column + 1], table_top + header_h), fill=BLUE, outline=MID_GRAY, width=2)
        draw.text((xs[column] + 16, table_top + header_h // 2), headers[column], font=head_font, fill=WHITE, anchor="lm")
    for row_index, row in enumerate(rows):
        top = table_top + header_h + row_index * row_h
        bottom = top + row_h
        fill = WHITE if row_index % 2 == 0 else LIGHT_GRAY
        for column, value in enumerate(row):
            draw.rectangle((xs[column], top, xs[column + 1], bottom), fill=fill, outline=MID_GRAY, width=2)
            draw_wrapped(draw, (xs[column] + 16, top + 18), value, body_font, xs[column + 1] - xs[column] - 32, max_lines=3)
    note_font = fnt(image, 8.2)
    draw.text((x1, table_bottom + 28), "설문조사 결과서와 인터뷰 결과서는 미실시이므로 최종 문서에서 제외함.", font=note_font, fill=ORANGE)
    draw.text((x1, table_bottom + 66), "○ 필수 · △ 선택 / 최종 문서 34쪽", font=note_font, fill=TEXT)


def draw_market_page(image: Image.Image, variant: int) -> None:
    draw = clear_body(image)
    guide_badge(image, draw)
    x1, y1, x2, y2 = content_bounds(image)
    gap = 34
    mid = (x1 + x2) // 2
    if variant == 1:
        insertion_box(
            image,
            draw,
            (x1, y1 + 58, mid - gap // 2, y2 - 200),
            "그림 1-1. 고령인구 또는 1인가구 추이",
            "통계청 2025 고령자 통계 또는 KOSIS 차트를 캡처한다. 그래프 제목·축·범례가 읽히게 하고 아래에 기관/자료명/연도를 표기한다.",
            "03_market_elderly.png",
            GREEN,
            LIGHT_GREEN,
        )
        insertion_box(
            image,
            draw,
            (mid + gap // 2, y1 + 58, x2, y2 - 200),
            "그림 1-2. 고령 1인가구 또는 음식물 폐기",
            "통계청 1인가구 자료를 우선 사용한다. 음식물류 폐기 자료를 쓰면 최신 조사연도와 단위를 명확히 적는다.",
            "03_market_single_household.png",
            ORANGE,
            LIGHT_ORANGE,
        )
        insertion_box(
            image,
            draw,
            (x1, y2 - 170, x2, y2),
            "핵심 해설 3~4줄",
            "고령인구·1인가구 증가 → 수동 재고관리 부담 → 자동 촬영·인식 서비스 필요성의 순서로 쓴다. 수치의 과장이나 임의 추정은 금지한다.",
            "PDF 본문 입력",
            BLUE,
            LIGHT_BLUE,
        )
    else:
        insertion_box(
            image,
            draw,
            (x1, y1 + 58, mid - gap // 2, y2),
            "관련 기술·서비스 비교표",
            "열: 기존 수기/앱 입력, 상용 스마트 냉장고, 본 프로젝트. 행: 입력 방식, 인식, 재고 반영, 사용자 검수, 레시피, 고령층 접근성.",
            "04_competitor_comparison.png",
            BLUE,
            LIGHT_BLUE,
        )
        insertion_box(
            image,
            draw,
            (mid + gap // 2, y1 + 58, x2, y2),
            "IoT·엣지 AI 기술 동향 그림",
            "IITP ICT R&D 기술로드맵의 IoT/엣지 AI 구성도를 참고한다. 원본 이미지를 그대로 쓸 경우 출처와 이용조건을 적고, 가능하면 핵심 구조만 재작성한다.",
            "04_technology_trend.png",
            ORANGE,
            LIGHT_ORANGE,
        )
    draw_note_footer(image, draw)


def draw_generic_split(
    image: Image.Image,
    left_title: str,
    left_text: str,
    left_file: str,
    right_title: str,
    right_text: str,
    right_file: str,
    ratio: float = 0.5,
) -> None:
    draw = clear_body(image)
    guide_badge(image, draw)
    x1, y1, x2, y2 = content_bounds(image)
    gap = 34
    split = x1 + round((x2 - x1) * ratio)
    insertion_box(image, draw, (x1, y1 + 58, split - gap // 2, y2), left_title, left_text, left_file, BLUE, LIGHT_BLUE)
    insertion_box(image, draw, (split + gap // 2, y1 + 58, x2, y2), right_title, right_text, right_file, GREEN, LIGHT_GREEN)
    draw_note_footer(image, draw)


def draw_single_diagram(image: Image.Image, title: str, text: str, filename: str, accent=BLUE) -> None:
    draw = clear_body(image)
    guide_badge(image, draw)
    x1, y1, x2, y2 = content_bounds(image)
    insertion_box(image, draw, (x1, y1 + 58, x2, y2), title, text, filename, accent, LIGHT_BLUE if accent == BLUE else LIGHT_GREEN)
    draw_note_footer(image, draw)


def draw_screen_grid(image: Image.Image, titles: list[str], filename: str, columns: int = 4) -> None:
    draw = clear_body(image)
    guide_badge(image, draw, "화면 캡처/와이어프레임 삽입")
    x1, y1, x2, y2 = content_bounds(image)
    top = y1 + 72
    gap = 28
    rows = (len(titles) + columns - 1) // columns
    cell_w = (x2 - x1 - gap * (columns - 1)) // columns
    cell_h = (y2 - top - gap * (rows - 1) - 52) // rows
    title_font = fnt(image, 8.6, bold=True)
    for index, title in enumerate(titles):
        row, column = divmod(index, columns)
        bx1 = x1 + column * (cell_w + gap)
        by1 = top + row * (cell_h + gap)
        bx2 = bx1 + cell_w
        by2 = by1 + cell_h
        draw.rounded_rectangle((bx1, by1, bx2, by2), radius=18, fill=LIGHT_GRAY, outline=MID_GRAY, width=2)
        dashed_rect(draw, (bx1 + 5, by1 + 5, bx2 - 5, by2 - 5), fill=BLUE, width=3)
        draw.text(((bx1 + bx2) // 2, (by1 + by2) // 2), title, font=title_font, fill=BLUE, anchor="mm")
    file_font = fnt(image, 7.6, bold=True)
    draw.text((x1, y2 - 10), f"권장 파일명: {filename}", font=file_font, fill=BLUE, anchor="ls")
    draw_note_footer(image, draw)


def draw_code_capture_page(image: Image.Image, panels: list[tuple[str, str, str]]) -> None:
    draw = clear_body(image)
    guide_badge(image, draw, "실제 소스코드 캡처 삽입")
    x1, y1, x2, y2 = content_bounds(image)
    gap = 34
    top = y1 + 64
    panel_w = (x2 - x1 - gap * (len(panels) - 1)) // len(panels)
    for index, (title, lines, filename) in enumerate(panels):
        bx1 = x1 + index * (panel_w + gap)
        bx2 = bx1 + panel_w
        draw.rounded_rectangle((bx1, top, bx2, y2), radius=18, fill=DARK_CODE, outline=(36, 50, 70), width=3)
        draw.rounded_rectangle((bx1, top, bx2, top + 78), radius=18, fill=(36, 50, 70))
        draw.rectangle((bx1, top + 60, bx2, top + 78), fill=(36, 50, 70))
        draw.text((bx1 + 24, top + 39), title, font=fnt(image, 9.2, bold=True), fill=WHITE, anchor="lm")
        draw_wrapped(draw, (bx1 + 28, top + 112), lines, fnt(image, 8.3), panel_w - 56, fill=(221, 231, 240), leading=1.45)
        dashed_rect(draw, (bx1 + 18, top + 92, bx2 - 18, y2 - 54), fill=(112, 146, 180), width=3)
        draw.text((bx1 + 26, y2 - 36), f"권장 파일명: {filename}", font=fnt(image, 7.4, bold=True), fill=(180, 205, 229))
    draw_note_footer(image, draw)


def draw_storyboard(image: Image.Image) -> None:
    draw = clear_body(image)
    guide_badge(image, draw, "시연 영상 장면 이미지 삽입")
    x1, y1, x2, y2 = content_bounds(image)
    titles = ["#1 문제 제시", "#2 하드웨어 소개", "#3 자동 인식·저장", "#4 앱 확인·레시피"]
    gap = 30
    top = y1 + 64
    cell_w = (x2 - x1 - gap) // 2
    cell_h = (y2 - top - gap) // 2
    for index, title in enumerate(titles):
        row, column = divmod(index, 2)
        bx1 = x1 + column * (cell_w + gap)
        by1 = top + row * (cell_h + gap)
        bx2 = bx1 + cell_w
        by2 = by1 + cell_h
        insertion_box(
            image,
            draw,
            (bx1, by1, bx2, by2),
            title,
            "사진 또는 대표 프레임을 넣고, 아래에 촬영 내용과 자막을 1~2줄로 쓴다.",
            f"32_story_{index + 1}.png",
            [BLUE, GREEN, ORANGE, BURGUNDY][index],
            [LIGHT_BLUE, LIGHT_GREEN, LIGHT_ORANGE, LIGHT_GRAY][index],
        )
    draw_note_footer(image, draw)


def draw_project_management(image: Image.Image) -> None:
    draw = clear_body(image)
    guide_badge(image, draw, "관리 증빙 캡처 삽입")
    x1, y1, x2, y2 = content_bounds(image)
    gap = 28
    width = (x2 - x1 - gap * 2) // 3
    items = [
        ("프로젝트 관리", "월별 일정 또는 칸반 보드", "33_project_board.png", GREEN, LIGHT_GREEN),
        ("형상관리", "Git 커밋/브랜치 화면. 계정명은 가린다.", "33_git_history.png", BLUE, LIGHT_BLUE),
        ("이슈관리", "오류·해결내역 표 또는 이슈 화면", "33_issue_log.png", ORANGE, LIGHT_ORANGE),
    ]
    for index, item in enumerate(items):
        bx1 = x1 + index * (width + gap)
        insertion_box(image, draw, (bx1, y1 + 58, bx1 + width, y2), *item)
    draw_note_footer(image, draw)


def replace_visual_body(image: Image.Image, source_page: int) -> None:
    if source_page == 2:
        draw_updated_output_table(image)
    elif source_page == 3:
        draw_market_page(image, 1)
    elif source_page == 4:
        draw_market_page(image, 2)
    elif source_page == 9:
        draw_generic_split(
            image,
            "유즈케이스 다이어그램",
            "시스템 경계 안에 로그인·냉장고 선택·재고 확인/수정·레시피·촬영·인식·저장을 배치하고 사용자/Pi/서버 Actor와 연결한다.",
            "07_usecase.svg",
            "유즈케이스 정의 표",
            "개요, Actor, 우선순위, 선행/후행조건, 기본·대안 시나리오, 비기능 요구사항을 세로 표로 정리한다.",
            "07_usecase_definition.png",
            0.42,
        )
    elif source_page == 10:
        draw_generic_split(
            image,
            "사용자 중심 서비스 시나리오",
            "문 열림 → 촬영 → AI 인식 → 서버 저장 → 앱 확인의 5단계를 그림과 번호로 표현한다.",
            "08_service_scenario.svg",
            "단계별 설명",
            "그림의 1~5번과 동일한 번호로 입력·처리·출력·예외를 1~2줄씩 쓴다.",
            "08_service_steps.png",
        )
    elif source_page == 11:
        draw_generic_split(
            image,
            "서비스 아키텍처",
            "리드스위치/카메라 → Raspberry Pi → YOLO·분류 → Flask → MySQL → Flutter를 좌→우로 연결한다.",
            "09_service_architecture.svg",
            "구성요소 역할·데이터 흐름",
            "GPIO17, Frame, HTTP multipart, SQL, REST JSON 라벨과 각 컴포넌트 역할을 번호로 설명한다.",
            "09_service_roles.png",
        )
    elif source_page == 12:
        draw_generic_split(
            image,
            "서비스 흐름도",
            "문 열림부터 촬영·후보추출·분류·stable frame·업로드·앱 표시까지 그린다. 판단은 마름모와 Yes/No를 사용한다.",
            "10_service_flow.svg",
            "처리 단계 설명",
            "confidence 미달, stable frame 미달, 네트워크 오류, /consume 소비 분기를 흐름도 번호와 맞춰 설명한다.",
            "10_flow_steps.png",
        )
    elif source_page == 13:
        draw_screen_grid(image, ["대표 화면", "상태 팝업", "오류 팝업", "UI 규칙/주석"], "11_uiux_board.png", 4)
    elif source_page == 14:
        draw_generic_split(
            image,
            "H/W·센서 배선/블록도",
            "Pi 중앙, 카메라·리드스위치·자석·전원·서버를 주변에 둔다. GND와 GPIO17(물리 핀 11)을 정확히 표시한다.",
            "12_hw_sensor.svg",
            "부품·연결 표",
            "부품/센서, 연결 핀, 역할, 비고를 작성한다. 미확정 모델과 전원 사양은 '실물 제작 후 확정'으로 표시한다.",
            "12_hw_connection_table.png",
            0.64,
        )
    elif source_page == 15:
        draw_single_diagram(
            image,
            "화면 중심 메뉴 트리",
            "로그인/회원가입 → 냉장고 선택 → 홈 → 재고 관리/레시피 추천/냉장고 변경/로그아웃. 재고와 레시피의 상세·수정·검색 하위 화면까지 연결한다.",
            "13_menu_screen_tree.svg",
            GREEN,
        )
    elif source_page == 16:
        draw_single_diagram(
            image,
            "기능 중심 메뉴 트리",
            "루트 'AI 스마트 냉장고'에서 계정, 냉장고, 재고, AI 인식, 레시피 기능군으로 분기하고 하위 기능을 동일 크기 노드로 정리한다.",
            "14_menu_function_tree.svg",
            GREEN,
        )
    elif source_page == 17:
        draw_generic_split(
            image,
            "대표 화면 목업/캡처",
            "재고 목록 또는 재고 상세 화면 1장을 넣는다. 번호 주석으로 버튼·필드·상태 표시를 연결한다.",
            "15_screen_spec.png",
            "기능 정의 표",
            "기능번호, 기능명, 기능설명, 처리내용, 비고, 관련 요구사항명을 표로 작성한다.",
            "15_screen_table.png",
            0.32,
        )
    elif source_page == 18:
        draw_screen_grid(image, ["기능정보", "화면 캡처", "입력값/설명", "입출력 데이터", "선행기능/예외"], "16_screen_detail.png", 3)
    elif source_page == 19:
        draw_screen_grid(image, ["냉장고 선택", "홈", "재고 목록", "재고 상세", "레시피 목록"], "17_ui_flow.png", 5)
    elif source_page == 20:
        draw_screen_grid(image, ["1. 식재료 투입", "2. 자동 촬영", "3. 인식 박스", "4. 재고 반영", "5. 사용자 수정"], "18_interaction_photos.png", 3)
    elif source_page == 21:
        draw_single_diagram(
            image,
            "엔티티 관계도(ERD)",
            "users, fridges, fridge_items, ingredients, recipes, recipe_ingredients, app_state를 배치한다. PK/FK와 Crow's Foot 카디널리티가 읽히게 만든다.",
            "19_erd.svg",
            BLUE,
        )
    elif source_page == 22:
        draw_single_diagram(
            image,
            "기능 처리도 - 식재료 자동 등록",
            "상단에 프로그램ID/명/작성일/Page, 그 아래 개요를 두고 중앙에 센서·Pi·AI·API·DB·앱 수영레인 흐름도를 넣는다. 하단에 번호별 설명을 추가한다.",
            "20_function_flow.svg",
            ORANGE,
        )
    elif source_page == 23:
        draw_single_diagram(
            image,
            "연계도·순차다이어그램",
            "Reed Sensor, Pi Camera, Detector/Classifier, Flask, MySQL, Flutter를 상단에 놓고 생명선을 내린다. alt 블록으로 문 열림 /upload와 문 닫힘 /consume을 분리한다.",
            "21_sequence.svg",
            ORANGE,
        )
    elif source_page == 24:
        draw_generic_split(
            image,
            "알고리즘 흐름도",
            "YOLO → contour → center fallback → padding → trusted label/분류기 → confidence → stable frame → cooldown → 업로드 순서로 그린다.",
            "22_algorithm_flow.svg",
            "단계별 시나리오",
            "흐름도의 번호와 같은 번호로 입력, 판단 기준, 출력, 예외 처리를 설명한다.",
            "22_algorithm_steps.png",
        )
    elif source_page == 25:
        draw_generic_split(
            image,
            "정상 인식 결과",
            "검출 박스, label, confidence가 보이는 실제 프레임 또는 캡처를 넣는다.",
            "23_algorithm_success.png",
            "낮은 confidence/오인식 결과",
            "확인 필요 상태나 재촬영 예시를 넣고, 상단에는 목적·입력·임계값·처리논리를 표로 덧붙인다.",
            "23_algorithm_exception.png",
        )
    elif source_page == 26:
        draw_single_diagram(
            image,
            "냉장고 장착 하드웨어 설계도",
            "냉장고 단면, 카메라 화각, 리드스위치·자석 위치, 외부 Pi·전원, 케이블 경로를 그린다. CSI/USB, GPIO17/GND, USB-C, Wi-Fi/LAN 라벨을 표시한다.",
            "24_hardware_design.svg",
            ORANGE,
        )
    elif source_page == 28:
        draw_generic_split(
            image,
            "ERD 축약본",
            "19쪽 ERD를 축약해 넣고 핵심 관계만 보이게 한다.",
            "26_table_erd.svg",
            "테이블 데이터사전",
            "항목명, Type, PK/FK, NULL, 기본값, 설명을 표로 만든다. fridge_items를 가장 크게 배치한다.",
            "26_table_definition.svg",
            0.55,
        )
    elif source_page == 29:
        draw_code_capture_page(
            image,
            [
                ("backend/app.py - upload_detection()", "캡처: 1143~1155, 1161~1180, 1195~1200\n파일명·줄번호 표시 / 민감정보 가림", "27_code_upload.png"),
                ("backend/app.py - list_recipes()", "캡처: 1017~1020, 1048~1082\n1061~1066 계산식과 1081 정렬식 포함", "27_code_recipes.png"),
            ],
        )
    elif source_page == 30:
        draw_code_capture_page(
            image,
            [
                ("pi_fridge_camera.py", "collect_crop_candidates(): 319~329\nscan_until_action(): 931~947\n두 구간 사이에 ... 표시", "28_code_pi.png"),
                ("api_service.dart", "fetchInventory(): 91~95\nfetchRecipes(): 147~156\n선택: fetchRecipeDetail(): 158~166", "28_code_flutter.png"),
            ],
        )
    elif source_page == 32:
        draw_screen_grid(image, ["재고 목록", "재고 상세", "레시피 목록", "레시피 상세"], "30_sw_*.png", 4)
    elif source_page == 33:
        draw_screen_grid(image, ["전체 장착", "Pi-카메라 연결", "GPIO17/GND", "문 열림/닫힘", "MJPEG 인식", "앱 재고 반영"], "31_hw_*.jpg", 3)
    elif source_page == 34:
        draw_storyboard(image)
    elif source_page == 35:
        draw_project_management(image)


def build_pages() -> list[Path]:
    PAGE_DIR.mkdir(parents=True, exist_ok=True)
    page_files: list[Path] = []
    for final_page, source_page in enumerate(SOURCE_PAGES, start=1):
        source_file = source_page_path(source_page)
        if not source_file.exists():
            raise FileNotFoundError(source_file)
        image = Image.open(source_file).convert("RGB")
        replace_visual_body(image, source_page)
        output_file = PAGE_DIR / f"page-{final_page:02d}.jpg"
        image.save(output_file, "JPEG", quality=94, subsampling=0, optimize=True)
        page_files.append(output_file)
    return page_files


def build_pdf(page_files: list[Path]) -> Path:
    OUTPUT_PDF.parent.mkdir(parents=True, exist_ok=True)
    page_width, page_height = landscape(A4)
    pdf = canvas.Canvas(str(OUTPUT_PDF), pagesize=(page_width, page_height), pageCompression=1)
    for page_file in page_files:
        pdf.drawImage(str(page_file), 0, 0, width=page_width, height=page_height)
        pdf.showPage()
    pdf.save()
    return OUTPUT_PDF


def build_contact_sheet(page_files: list[Path]) -> Path:
    columns = 6
    thumb_width = 280
    thumb_height = 198
    gutter = 12
    label_height = 18
    rows = (len(page_files) + columns - 1) // columns
    sheet = Image.new(
        "RGB",
        (
            columns * thumb_width + (columns + 1) * gutter,
            rows * (thumb_height + label_height) + (rows + 1) * gutter,
        ),
        WHITE,
    )
    draw = ImageDraw.Draw(sheet)
    label_font = font(FONT_REGULAR, 13)
    for index, page_file in enumerate(page_files):
        row, column = divmod(index, columns)
        x = gutter + column * (thumb_width + gutter)
        y = gutter + row * (thumb_height + label_height + gutter)
        thumb = Image.open(page_file).convert("RGB")
        thumb.thumbnail((thumb_width, thumb_height), Image.Resampling.LANCZOS)
        sheet.paste(thumb, (x, y))
        draw.text((x, y + thumb_height + 1), f"page {index + 1:02d}", font=label_font, fill=TEXT)
    sheet.save(CONTACT_SHEET, "JPEG", quality=90, optimize=True)
    return CONTACT_SHEET


if __name__ == "__main__":
    pages = build_pages()
    print(build_pdf(pages))
    print(build_contact_sheet(pages))
