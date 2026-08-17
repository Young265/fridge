from pathlib import Path

from pypdf import PdfReader, PdfWriter
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas


ROOT = Path(r"C:\Users\dudal\Desktop\DaS\2026\fridge")
OUT = ROOT / "output" / "pdf"
OUT.mkdir(parents=True, exist_ok=True)

FONT_PATH = Path(r"C:\Windows\Fonts\batang.ttc")
pdfmetrics.registerFont(TTFont("Batang", str(FONT_PATH), subfontIndex=0))
FONT = "Batang"

MEETINGS = [
    {
        "date": "2026-04-16",
        "time": "11시 00분~12시 00분",
        "activity": [
            ("프로젝트 목표 및 요구사항 구체화", "카메라로 냉장고에 들어오고 나가는 식재료를 인식해 재고를 자동 관리하고, 보유 재료를 바탕으로 레시피를 추천하는 서비스의 핵심 범위를 정리했습니다."),
            ("서비스 구조 및 기술 스택 설계", "Flutter 앱, Flask 백엔드, MySQL 데이터베이스, Raspberry Pi 5와 카메라를 연동하는 전체 구조를 설계하고 사용자, 냉장고, 식재료 재고, 레시피 데이터를 중심으로 API와 DB 구성을 검토했습니다."),
            ("화면 구성 및 역할 분담", "로그인·회원가입, 냉장고 선택, 재고 목록·상세, 레시피 목록·상세 화면의 흐름을 정리하고 앱, 서버, AI·하드웨어 영역으로 개발 업무를 나누었습니다."),
        ],
        "plan": [
            "우선 Flutter 앱의 주요 화면과 데이터 모델을 구현하고, 백엔드의 사용자·냉장고·재고·레시피 API를 연결할 예정입니다.",
            "식재료 인식을 위해 공개 이미지 데이터와 AI Hub 자료를 수집·정제하고, YOLO 기반 분류 모델의 기초 학습 환경을 구축할 계획입니다.",
            "라즈베리파이 카메라와 서버 간 이미지 전송 방식, 냉장고 문 열림 감지를 위한 리드 스위치 적용 방법도 함께 검토하기로 했습니다.",
        ],
    },
    {
        "date": "2026-05-28",
        "time": "11시 00분~12시 00분",
        "activity": [
            ("모바일 앱 및 백엔드 기본 기능 구현", "Flutter에서 로그인·회원가입, 냉장고 선택, 재고 조회·수정, 레시피 조회 화면을 구현하고 Flask 백엔드 및 MySQL 데이터베이스와 연동되는 기본 흐름을 점검했습니다."),
            ("식재료 이미지 분류 모델 구축", "수집한 식재료 이미지를 학습용 데이터셋으로 정리하고 YOLO 분류 모델을 학습했습니다. 이미지와 카메라 입력을 받아 품목명과 신뢰도를 확인하는 테스트 코드를 구성했습니다."),
            ("Raspberry Pi 카메라 연동 방향 확정", "라즈베리파이에서 촬영한 이미지와 인식 결과를 백엔드 업로드 API로 전송하는 카메라 브리지 구조를 검토하고, 리드 스위치로 문 열림을 감지해 촬영을 시작하는 방식으로 구현하기로 했습니다."),
        ],
        "plan": [
            "라즈베리파이 GPIO17에 리드 스위치를 연결하고 문 열림 신호가 발생했을 때만 카메라와 인식 파이프라인이 동작하도록 구현할 예정입니다.",
            "고정된 중앙 영역만 분류하면 식재료 위치에 따라 누락될 수 있으므로, 화면 안의 후보 물체를 동적으로 찾고 잘라내는 검출 방식을 추가로 검토할 계획입니다.",
            "PC와 라즈베리파이의 촬영 해상도와 프레임 설정을 맞추고, 동일 식재료의 반복 등록을 막기 위한 안정 프레임 및 대기시간 기준을 정하기로 했습니다.",
        ],
    },
    {
        "date": "2026-06-12",
        "time": "11시 00분~12시 00분",
        "activity": [
            ("동적 식재료 후보 검출 구현", "고정된 중앙 박스 대신 YOLO 객체 검출 결과와 윤곽선 분석을 이용해 화면 내 식재료 후보 영역을 찾도록 개선했습니다. 검출이 어려운 경우에만 중앙 영역을 보조 수단으로 사용하도록 구성했습니다."),
            ("분류 정확도 및 촬영 조건 개선", "후보 영역에 여백을 포함해 분류 모델로 전달하고, 일반 객체 검출기가 신뢰할 수 있게 인식한 사과·바나나 등은 해당 결과를 활용하도록 했습니다. PC와 라즈베리파이의 기본 촬영 조건도 640×480, 30 FPS로 통일했습니다."),
            ("인식 결과 업로드 안정화", "연속 프레임에서 동일한 품목 조합이 일정 횟수 확인된 경우에만 전체 이미지, 잘라낸 식재료 이미지, 품목명과 신뢰도를 서버로 전송하도록 하여 오인식과 중복 등록을 줄였습니다."),
        ],
        "plan": [
            "실제 냉장고 환경에서 조명, 배경, 식재료 위치를 바꾸어 테스트하고 검출 신뢰도, 후보 개수, 잘라내기 여백과 안정 프레임 값을 조정할 예정입니다.",
            "리드 스위치 신호와 카메라 시작 시점을 연결해 문을 열었을 때 빠르게 인식하고, 문이 닫히면 다음 동작을 기다리는 반복 실행 흐름을 완성할 계획입니다.",
            "재고 추가뿐 아니라 식재료가 밖으로 나간 경우 수량을 차감할 수 있도록 백엔드 처리 방식과 카메라 동작 시점을 검토하기로 했습니다.",
        ],
    },
    {
        "date": "2026-07-10",
        "time": "13시 00분~14시 00분",
        "activity": [
            ("리드 스위치 기반 재고 반영 흐름 구현", "냉장고 문 열림 시 카메라가 식재료를 인식해 재고를 추가하고, 문 닫힘 전후의 인식 결과를 이용해 반출 품목의 수량을 차감하는 처리 흐름을 구현했습니다. 수량이 0이 되면 해당 재고를 삭제하도록 백엔드 기능도 보완했습니다."),
            ("카메라 지연 및 미리보기 개선", "카메라를 준비 상태로 유지하면서 문이 열릴 때만 검출·분류를 수행하는 저지연 방식을 적용하고, 브라우저에서 카메라 화면과 최신 검출 박스를 확인할 수 있는 실시간 미리보기 기능을 추가했습니다."),
            ("Raspberry Pi 실환경 점검", "촬영 화면과 AI 검출 주기를 분리해 미리보기가 끊기는 현상을 줄였으며, 식재료 등록·차감 API, 반복 인식 방지, 네트워크 연결과 실행 설정을 점검했습니다."),
        ],
        "plan": [
            "문이 닫힌 뒤 반출 품목을 확인하는 방식은 식재료가 화면에서 사라져 누락될 수 있으므로, 문이 열린 동안 이동 방향을 판단하는 방식으로 개선할 예정입니다.",
            "카메라 화면에 냉장고 안쪽과 바깥쪽을 구분하는 기준 영역을 설정하고, 동일 식재료의 위치 변화를 추적해 입고와 출고를 구분하는 기능을 다음 단계에서 개발할 계획입니다.",
            "실제 장착 위치에 맞춰 카메라 방향, 검출 간격, 신뢰도와 추적 안정 조건을 조정하고 전체 앱·서버·하드웨어 통합 테스트를 진행하기로 했습니다.",
        ],
    },
]


def text_width(text: str, size: float) -> float:
    return pdfmetrics.stringWidth(text, FONT, size)


def wrap(text: str, max_width: float, size: float):
    lines = []
    current = ""
    for word in text.split():
        candidate = word if not current else current + " " + word
        if current and text_width(candidate, size) > max_width:
            lines.append(current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(current)
    return lines


def draw_wrapped(c, text, x, y, width, size=10.5, leading=16.2):
    c.setFont(FONT, size)
    for line in wrap(text, width, size):
        c.drawString(x, y, line)
        y -= leading
    return y


def draw_right(c, text, x_right, y, size=11.2):
    c.setFont(FONT, size)
    c.drawRightString(x_right, y, text)


def build_pdf(meeting):
    filename = f"{meeting['date']}_한이음_미팅_회의록.pdf"
    path = OUT / filename
    c = canvas.Canvas(str(path), pagesize=A4, pageCompression=1)
    width, height = A4

    c.setTitle(f"{meeting['date']} 한이음 미팅 회의록")
    c.setAuthor("한이음 드림업 AI 스마트 냉장고 팀")

    c.setFont(FONT, 24)
    c.drawCentredString(width / 2, 721, "한이음 회의록")

    meta_right = 510
    meta_y = 662
    meta_leading = 17.6
    metadata = [
        "활동방법:  오프라인",
        "활동장소: 서원대학교 제1자연관 405호",
        f"활동일자: {meeting['date']}",
        f"활동시간: {meeting['time']}",
        "참여인원: 민영기 이글루 코퍼레이션/멘토",
        "육영민 서원대학교/멘티",
        "이찬민 서원대학교/멘티",
        "윤종하 서원대학교/멘티",
    ]
    for line in metadata:
        draw_right(c, line, meta_right, meta_y)
        meta_y -= meta_leading

    left = 85
    body_width = 430
    y = 500
    c.setFont(FONT, 11.5)
    c.drawString(left, y, "활동내용(회의내용)")
    y -= 19
    for title, paragraph in meeting["activity"]:
        c.setFont(FONT, 11.1)
        c.drawString(left, y, title)
        y -= 17
        y = draw_wrapped(c, paragraph, left, y, body_width)
        y -= 1.5

    y -= 8
    c.setFont(FONT, 11.5)
    c.drawString(left, y, "향후계획 및 기타사항")
    y -= 19
    for paragraph in meeting["plan"]:
        y = draw_wrapped(c, paragraph, left, y, body_width)
        y -= 2

    if y < 55:
        raise RuntimeError(f"Page overflow for {meeting['date']}: final y={y}")

    c.showPage()
    c.save()
    return path


def combine(paths):
    combined = OUT / "2026_한이음_미팅_회의록_4회분.pdf"
    writer = PdfWriter()
    for path in paths:
        reader = PdfReader(str(path))
        writer.add_page(reader.pages[0])
    writer.add_metadata({
        "/Title": "2026 한이음 미팅 회의록 4회분",
        "/Author": "한이음 드림업 AI 스마트 냉장고 팀",
    })
    with combined.open("wb") as stream:
        writer.write(stream)
    return combined


if __name__ == "__main__":
    generated = [build_pdf(meeting) for meeting in MEETINGS]
    generated.append(combine(generated))
    for path in generated:
        print(path)
