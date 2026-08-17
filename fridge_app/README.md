# 스마트 냉장고 앱

재고 확인·수정, 보유 재료 기반 레시피 추천, 부족 재료 장보기 목록을 제공하는 앱입니다.

## 실행

로컬 백엔드를 사용할 때:

```powershell
flutter run
```

실제 Android 기기나 다른 PC의 백엔드를 사용할 때는 주소를 빌드 설정으로 전달합니다.

```powershell
flutter run --dart-define=API_BASE_URL=http://192.168.0.10:5000
```

앱과 백엔드 장치가 같은 네트워크에 있어야 하며, 백엔드 장치 방화벽에서 5000번 포트
인바운드 연결을 허용해야 합니다.

## 공공 레시피 가져오기

농림축산식품부 공공데이터 포털에서 `안심 레시피` 인증키를 발급받은 뒤
백엔드 폴더에서 실행합니다. 같은 레시피를 다시 가져와도 중복 생성되지
않고 최신 내용으로 갱신됩니다.

```powershell
$env:MAFRA_RECIPE_API_KEY='발급받은-인증키'
$env:MAFRA_RECIPE_IMPORT_LIMIT='100'
python import_public_recipes.py
```

인증키 없이 실행하면 공공 샘플 5행을 조회하며, 재료와 조리 순서가 모두
존재하는 레시피만 안전하게 저장합니다.
