# 브랜드 포스트 스튜디오

브랜드커넥트 상품 정보를 바탕으로 가격 비교표, 네이버 블로그 원고, 대표 이미지를 만드는 Streamlit 앱입니다.

## 주요 기능

- 상품 및 경쟁상품 정보 입력
- 사실 기반 블로그 초안 생성
- 경제적 이해관계 표시문구 자동 포함
- 대표 이미지 생성 및 내려받기
- 발행 전 확인 체크리스트

## Streamlit Community Cloud 배포

1. 이 저장소를 Streamlit Community Cloud에 연결합니다.
2. 진입 파일로 `streamlit_app.py`를 선택합니다.
3. App settings의 Secrets에 아래 내용을 등록합니다.

```toml
OPENAI_API_KEY = "발급받은 키"
TEXT_MODEL = "gpt-5.6-luna"
IMAGE_ORCHESTRATOR_MODEL = "gpt-5.6-luna"
IMAGE_MODEL = "gpt-image-2.5-flare"
```

API 키를 저장소 파일에 직접 넣지 마세요.

## 주의사항

- 가격과 상품 정보는 게시 직전에 다시 확인해야 합니다.
- 실제로 사용하지 않은 상품을 사용한 것처럼 작성하지 마세요.
- 브랜드커넥트 서비스 화면에서 안내하는 최신 경제적 이해관계 표시문구를 우선 적용하세요.
- 생성 이미지는 실제 상품 사진을 대체하는 증빙으로 사용하지 마세요.


