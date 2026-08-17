from pathlib import Path
import subprocess

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(r"C:\Users\dudal\Desktop\DaS\2026\fridge")
OUT = ROOT / "output" / "meeting_captures"
GIT = Path(r"C:\Users\dudal\.cache\codex-runtimes\codex-primary-runtime\dependencies\native\git\cmd\git.exe")

FONT_REG = r"C:\Windows\Fonts\malgun.ttf"
FONT_BOLD = r"C:\Windows\Fonts\malgunbd.ttf"
FONT_CODE = r"C:\Windows\Fonts\consola.ttf"

W, H = 1600, 1000
HEADER_H = 112


def font(path, size):
    return ImageFont.truetype(path, size)


def contain(image, box):
    x, y, w, h = box
    scale = min(w / image.width, h / image.height)
    new_size = (max(1, int(image.width * scale)), max(1, int(image.height * scale)))
    resized = image.resize(new_size, Image.Resampling.LANCZOS)
    return resized, (x + (w - new_size[0]) // 2, y + (h - new_size[1]) // 2)


def add_header(draw, date, title, note=None, dark=False):
    fg = "#F8FAFC" if dark else "#172033"
    sub = "#A9B7C6" if dark else "#64748B"
    draw.text((58, 25), date, font=font(FONT_BOLD, 30), fill="#287A52" if not dark else "#69D39D")
    draw.text((265, 22), title, font=font(FONT_BOLD, 36), fill=fg)
    if note:
        draw.text((265, 70), note, font=font(FONT_REG, 18), fill=sub)


def make_image_capture(src, date, title, filename, note=None, bg="#F4F7F3"):
    folder = OUT / date
    folder.mkdir(parents=True, exist_ok=True)
    canvas = Image.new("RGB", (W, H), bg)
    draw = ImageDraw.Draw(canvas)
    add_header(draw, date, title, note)
    image = Image.open(src).convert("RGB")
    fitted, pos = contain(image, (55, HEADER_H + 25, W - 110, H - HEADER_H - 75))
    shadow_pos = (pos[0] + 10, pos[1] + 12)
    draw.rounded_rectangle(
        (shadow_pos[0] - 8, shadow_pos[1] - 8, shadow_pos[0] + fitted.width + 8, shadow_pos[1] + fitted.height + 8),
        radius=18,
        fill="#DDE5DF",
    )
    canvas.paste(fitted, pos)
    out = folder / filename
    canvas.save(out, quality=95)
    return out


def git_file(commit, path):
    result = subprocess.run(
        [str(GIT), "show", f"{commit}:{path}"],
        cwd=ROOT,
        check=True,
        capture_output=True,
    )
    return result.stdout.decode("utf-8")


def snippet(source, anchor, before=0, count=23):
    lines = source.splitlines()
    start = next(i for i, line in enumerate(lines) if anchor in line)
    start = max(0, start - before)
    return start + 1, lines[start:start + count]


def code_color(line):
    stripped = line.lstrip()
    if stripped.startswith("#"):
        return "#78A06A"
    if stripped.startswith(("def ", "class ")):
        return "#5CCFE6"
    if stripped.startswith(("if ", "for ", "while ", "return ", "with ", "try:", "except ")):
        return "#C792EA"
    return "#D8DEE9"


def make_code_capture(commit, date, title, filename, anchor, note, path="backend/pi_fridge_camera.py", count=23):
    source = git_file(commit, path)
    first_line, lines = snippet(source, anchor, count=count)
    folder = OUT / date
    folder.mkdir(parents=True, exist_ok=True)

    canvas = Image.new("RGB", (W, H), "#111827")
    draw = ImageDraw.Draw(canvas)
    add_header(draw, date, title, note, dark=True)

    draw.rounded_rectangle((40, 118, W - 40, H - 38), radius=18, fill="#1B2432")
    draw.ellipse((66, 144, 86, 164), fill="#FF5F57")
    draw.ellipse((98, 144, 118, 164), fill="#FFBD2E")
    draw.ellipse((130, 144, 150, 164), fill="#28C840")
    draw.text((180, 139), path, font=font(FONT_CODE, 21), fill="#94A3B8")
    draw.line((118, 187, 118, H - 60), fill="#374151", width=2)

    code_font = font(FONT_CODE, 25)
    y = 205
    for offset, line in enumerate(lines):
        number = str(first_line + offset)
        draw.text((62, y), number.rjust(3), font=code_font, fill="#64748B")
        visible = line.expandtabs(4)
        if len(visible) > 98:
            visible = visible[:95] + "..."
        draw.text((142, y), visible, font=code_font, fill=code_color(line))
        y += 32

    out = folder / filename
    canvas.save(out, quality=95)
    return out


def main():
    outputs = []
    outputs.append(make_image_capture(
        ROOT / "diagrams" / "rendered" / "png" / "09_service_architecture.png",
        "2026-04-16", "서비스 구성 및 기술 스택 설계", "01_서비스_구성도.png",
        "Flutter 앱 · Flask API · MySQL · Raspberry Pi 5 연동 구조",
    ))
    outputs.append(make_image_capture(
        ROOT / "diagrams" / "rendered" / "png" / "11_uiux_wireframe.png",
        "2026-04-16", "주요 화면 흐름 정의", "02_UIUX_주요화면.png",
        "로그인부터 냉장고 재고 및 레시피 상세 화면까지의 사용자 흐름",
    ))
    outputs.append(make_image_capture(
        ROOT / "output" / "pptx" / "review_assets" / "inventory.png",
        "2026-05-28", "냉장고 재고 관리 화면 구현", "01_재고관리_화면.png",
        "재고 상태·수량·인식 결과를 한 화면에서 확인하는 Flutter UI",
    ))
    outputs.append(make_image_capture(
        ROOT / "output" / "pptx" / "review_assets" / "recipe_detail.png",
        "2026-05-28", "보유 재료 기반 레시피 상세 화면", "02_레시피_상세화면.png",
        "보유·부족 재료와 조리 방법을 표시하는 Flutter UI",
    ))
    outputs.append(make_image_capture(
        ROOT / "backend" / "egg_dataset_preview.jpg",
        "2026-06-12", "식재료 분류 데이터셋 구축", "01_식재료_학습데이터.png",
        "AI Hub 및 공개 이미지 자료를 정제한 달걀 클래스 학습 샘플",
    ))
    outputs.append(make_code_capture(
        "db1a3d0", "2026-06-12", "동적 식재료 후보 검출 구현", "02_동적_후보검출_코드.png",
        "def detector_crop_candidates(", "Git 커밋 db1a3d0 · YOLO 검출 박스를 분류 후보 영역으로 변환",
        count=24,
    ))
    outputs.append(make_code_capture(
        "8866311", "2026-07-10", "인식 결과 기반 재고 차감 구현", "01_재고차감_코드.png",
        "def consume_candidates(", "Git 커밋 8866311 · 문 닫힘 전후 반출 품목을 /consume API에 반영",
        count=24,
    ))
    outputs.append(make_code_capture(
        "24c0356", "2026-07-10", "카메라 실시간 미리보기 개선", "02_미리보기_스트림_코드.png",
        "class PreviewStreamer:", "Git 커밋 24c0356 · 촬영 화면과 AI 검출 주기를 분리한 미리보기 스트림",
        count=24,
    ))

    for output in outputs:
        print(output)


if __name__ == "__main__":
    main()
