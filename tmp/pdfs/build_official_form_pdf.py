from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from reportlab.lib.pagesizes import A4, landscape
from reportlab.pdfgen import canvas


ROOT = Path(__file__).resolve().parents[2]
TEMPLATE_DIR = ROOT / "tmp" / "pdfs" / "template_pages_180"
CONTENT_DIR = ROOT / "tmp" / "pdfs" / "generated_pages_180"
PAGE_DIR = ROOT / "tmp" / "pdfs" / "official_form_pages"
OUTPUT_PDF = ROOT / "output" / "pdf" / "2026_제작설계서_응용하드웨어_AI스마트냉장고_원본양식형.pdf"
CONTACT_SHEET = ROOT / "tmp" / "pdfs" / "official_form_contact_sheet.jpg"

PROJECT_TITLE = "독거노인의 식생활 관리를 위한 AI 기반 스마트 냉장고"
DOCUMENT_DATE = "2026. 07. 11"
TEAM_LABEL = "(팀명) 프로젝트팀"
PRIVACY_NOTE = "* 팀원 이름 및 소속 본문 내 기입 불가"

FONT_REGULAR = Path("C:/Windows/Fonts/malgun.ttf")
FONT_BOLD = Path("C:/Windows/Fonts/malgunbd.ttf")


def page_path(directory: Path, page_number: int) -> Path:
    return directory / f"page-{page_number:02d}.png"


def font(path: Path, size: int) -> ImageFont.FreeTypeFont:
    if not path.exists():
        raise FileNotFoundError(f"Required Korean font not found: {path}")
    return ImageFont.truetype(str(path), size=size)


def draw_cover_fields(image: Image.Image) -> None:
    draw = ImageDraw.Draw(image)
    width, height = image.size
    sx = width / 841.0
    sy = height / 595.0

    title_font = font(FONT_BOLD, round(18 * sy))
    date_font = font(FONT_REGULAR, round(18 * sy))
    team_font = font(FONT_REGULAR, round(13 * sy))
    note_font = font(FONT_REGULAR, round(10.5 * sy))

    # Project title is the only blank field on the white portion of the cover.
    draw.text(
        (round(340 * sx), round(345 * sy)),
        PROJECT_TITLE,
        font=title_font,
        fill=(55, 63, 74),
        anchor="la",
    )

    gray = (226, 230, 235)
    # Replace the date and team placeholders while keeping the original form's
    # gray information panel and privacy instruction.
    draw.rectangle(
        (round(330 * sx), round(414 * sy), round(515 * sx), round(448 * sy)),
        fill=gray,
    )
    draw.text(
        (round(420.5 * sx), round(429 * sy)),
        DOCUMENT_DATE,
        font=date_font,
        fill=(55, 59, 66),
        anchor="mm",
    )

    draw.rectangle(
        (round(235 * sx), round(448 * sy), round(625 * sx), round(482 * sy)),
        fill=gray,
    )
    draw.text(
        (round(245 * sx), round(463 * sy)),
        TEAM_LABEL,
        font=team_font,
        fill=(55, 59, 66),
        anchor="lm",
    )
    draw.text(
        (round(370 * sx), round(463 * sy)),
        PRIVACY_NOTE,
        font=note_font,
        fill=(245, 0, 0),
        anchor="lm",
    )


def compose_body(template: Image.Image, content: Image.Image) -> Image.Image:
    template = template.convert("RGB")
    content = content.convert("RGB")
    width, height = template.size
    source_width, source_height = content.size

    # Retain the supplied form's blue title tab and official logo. The custom
    # project body begins below it and replaces every sample table, chart,
    # red sample marker, and red example footer.
    source_top = round(source_height * 0.166)
    source_bottom = round(source_height * 0.953)
    destination_top = round(height * 0.195)
    destination_bottom = round(height * 0.943)

    # Some supplied sample pages place tables or pictures unusually high. Clear
    # those remnants without touching the blue title tab or official logo.
    pre_draw = ImageDraw.Draw(template)
    pre_draw.rectangle(
        (
            round(width * 0.360),
            round(height * 0.105),
            width,
            destination_top,
        ),
        fill=(255, 255, 255),
    )
    pre_draw.rectangle(
        (
            round(width * 0.028),
            round(height * 0.172),
            round(width * 0.360),
            destination_top,
        ),
        fill=(255, 255, 255),
    )

    body = content.crop((0, source_top, source_width, source_bottom))
    body = body.resize(
        (width, destination_bottom - destination_top),
        Image.Resampling.LANCZOS,
    )
    template.paste(body, (0, destination_top))

    # The sample marker is above the body replacement area. Cover only that
    # marker while preserving the official logo directly above it.
    draw = ImageDraw.Draw(template)
    draw.rectangle(
        (
            round(width * 0.835),
            round(height * 0.070),
            width,
            round(height * 0.155),
        ),
        fill=(255, 255, 255),
    )
    # Remove the supplied sample's red instruction footer. The narrow left
    # design rail is intentionally retained.
    draw.rectangle(
        (
            round(width * 0.028),
            round(height * 0.948),
            round(width * 0.985),
            round(height * 0.985),
        ),
        fill=(255, 255, 255),
    )
    return template


def build_pages() -> list[Path]:
    PAGE_DIR.mkdir(parents=True, exist_ok=True)
    page_files: list[Path] = []
    for page_number in range(1, 37):
        template_file = page_path(TEMPLATE_DIR, page_number)
        content_file = page_path(CONTENT_DIR, page_number)
        if not template_file.exists() or not content_file.exists():
            raise FileNotFoundError(
                f"Rendered page missing for page {page_number}: "
                f"{template_file} / {content_file}"
            )

        template = Image.open(template_file).convert("RGB")
        if page_number == 1:
            composed = template.copy()
            draw_cover_fields(composed)
        elif page_number == 36:
            composed = template.copy()
        else:
            content = Image.open(content_file)
            composed = compose_body(template, content)

        output_file = PAGE_DIR / f"page-{page_number:02d}.jpg"
        composed.save(output_file, "JPEG", quality=94, subsampling=0, optimize=True)
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
        "white",
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
        draw.text(
            (x, y + thumb_height + 2),
            f"page {index + 1:02d}",
            font=label_font,
            fill=(60, 68, 78),
        )
    sheet.save(CONTACT_SHEET, "JPEG", quality=90, optimize=True)
    return CONTACT_SHEET


if __name__ == "__main__":
    pages = build_pages()
    print(build_pdf(pages))
    print(build_contact_sheet(pages))
