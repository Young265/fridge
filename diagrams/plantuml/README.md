# 제작설계서 PlantUML 도면

이 폴더의 `.puml`은 제작설계서 페이지 번호에 맞춘 독립형 PlantUML 원본이다. 모든 명령은 프로젝트 루트(`fridge`)에서 Windows PowerShell로 실행한다.

## 도면 목록

| 페이지 | 문서 항목 | 파일 | 용도 |
|---:|---|---|---|
| 07 | 유스케이스 정의도 | [07_usecase.puml](./07_usecase.puml) | 사용자, Raspberry Pi, 운영자의 주요 기능 범위 정의 |
| 08 | 서비스 시나리오 | [08_service_scenario.puml](./08_service_scenario.puml) | 문 열림 등록과 문 닫힘 소비 반영 시나리오 설명 |
| 09 | 서비스 아키텍처 | [09_service_architecture.puml](./09_service_architecture.puml) | 카메라·센서–Pi–Flask/MySQL–Flutter 전체 구성 |
| 10 | 서비스 흐름도 | [10_service_flow.puml](./10_service_flow.puml) | 센서 이벤트부터 앱 재고 표시까지의 처리 흐름 |
| 11 | UI/UX 와이어프레임 | [11_uiux_wireframe.puml](./11_uiux_wireframe.puml) | 주요 앱 화면의 배치와 정보 구조 |
| 12 | H/W 센서 배선 | [12_hw_sensor.puml](./12_hw_sensor.puml) | 카메라, 리드스위치, GPIO17/GND 연결 설명 |
| 13 | 메뉴구성도–화면 트리 | [13_menu_screen_tree.puml](./13_menu_screen_tree.puml) | 로그인 이후 Flutter 화면 계층 |
| 14 | 메뉴구성도–기능 트리 | [14_menu_function_tree.puml](./14_menu_function_tree.puml) | 화면별 조회·등록·수정·삭제 기능 분류 |
| 15 | 화면설계서–대표 화면 | [15_screen_spec.puml](./15_screen_spec.puml) | 로그인, 홈, 재고, 레시피 화면 명세 |
| 16 | 화면설계서–재고 상세 | [16_inventory_detail_screen.puml](./16_inventory_detail_screen.puml) | AI 결과 확인, 수량·상태 수정 및 삭제 UI |
| 17 | UI 흐름도 | [17_ui_flow.puml](./17_ui_flow.puml) | 사용자 화면 이동과 되돌아가기 경로 |
| 18 | 연계도 | [18_interaction_flow.puml](./18_interaction_flow.puml) | 냉장고 H/W–Pi–Flutter–Flask–MySQL 데이터·프로토콜 연계 |
| 19 | 개념 ERD | [19_erd.puml](./19_erd.puml) | 사용자, 냉장고, 재고, 식재료, 레시피 관계 |
| 20 | 기능 처리도 | [20_function_flow.puml](./20_function_flow.puml) | 문 이벤트 기반 인식·재고 반영 기능 처리 |
| 21 | 순차 다이어그램 | [21_sequence.puml](./21_sequence.puml) | 입고 등록과 문 닫힘 소비 처리 호출 순서 |
| 22 | 알고리즘 흐름도 | [22_algorithm_flow.puml](./22_algorithm_flow.puml) | 후보 생성, 분류, 안정 프레임 판정 과정 |
| 24 | H/W 모듈 설계 | [24_hardware_design.puml](./24_hardware_design.puml) | 냉장고 내부 부품과 외부 Pi 제어부 배치 |
| 26 | 물리 테이블 ERD | [26_table_erd.puml](./26_table_erd.puml) | 실제 MySQL 컬럼, PK/FK/UQ 및 삭제 규칙 |

## Windows PowerShell 렌더

먼저 Java와 PlantUML JAR을 확인한다.

```powershell
java -version
Test-Path .\tmp\plantuml\plantuml.jar
```

렌더 전 전체 문법 검사:

```powershell
java "-Dfile.encoding=UTF-8" -jar .\tmp\plantuml\plantuml.jar -charset UTF-8 -checkonly .\diagrams\plantuml
```

PNG 전체 렌더:

```powershell
New-Item -ItemType Directory -Force -Path .\diagrams\rendered\png | Out-Null
java "-Dfile.encoding=UTF-8" "-DPLANTUML_LIMIT_SIZE=8192" -jar .\tmp\plantuml\plantuml.jar -charset UTF-8 -tpng -o ..\rendered\png .\diagrams\plantuml
```

SVG 전체 렌더:

```powershell
New-Item -ItemType Directory -Force -Path .\diagrams\rendered\svg | Out-Null
java "-Dfile.encoding=UTF-8" -jar .\tmp\plantuml\plantuml.jar -charset UTF-8 -tsvg -o ..\rendered\svg .\diagrams\plantuml
```

## 편집·삽입 규칙

- 소스는 UTF-8로 저장하고 파일의 `@start...`/`@end...` 쌍을 유지한다.
- Windows 한글 폰트는 `Malgun Gothic`을 사용한다. 다른 OS에서는 `Noto Sans CJK KR` 등 설치된 한글 폰트로 교체한다.
- 파일 번호는 제작설계서 페이지와 연결되므로 임의로 변경하지 않는다. 개인정보, 실제 이메일·IP·비밀번호는 넣지 않는다.
- 미확정 H/W 모델·치수·전원·기구 사양은 `실물 제작 후 확정`으로 표기한다.
- 제작설계서에는 **A4 가로** 기준으로 여백을 유지하고 종횡비를 고정해 삽입한다.
- 선명한 확대·PDF 출력을 위해 **SVG를 우선** 사용한다. Word/PDF 도구가 SVG 또는 한글 폰트를 올바르게 처리하지 못하면 **PNG를 사용**한다.
- 삽입 후 PDF로 내보내 한글 깨짐, 잘린 선·범례, 작은 글자를 최종 확인한다.
