# 상품정보 수집기 — 복사하던 상품 목록을 Excel로

**검색어나 공개 상품 페이지 URL을 입력하면 상품명·가격·링크를 모아 Excel로 저장하는 Python 자동화 도구입니다.**

## 문제와 해결
상품을 하나씩 찾아 Excel에 복사하면 시간이 들고 중복·가격 누락이 생깁니다. 수집 → 상품별 오류 격리 → 중복 제거 → Excel 생성까지 한 번에 처리합니다.

## 주요 기능
- URL 또는 검색어 입력, 최대 5페이지 수집, 진행률 표시
- 상품명·숫자 가격·통화·URL·재고·평점(있을 때) 추출
- 정규화한 URL 기준 중복 제거, 오류 상품·페이지 건너뛰기
- 필터·고정 헤더·상품 링크가 있는 `.xlsx`와 실행 요약
- Books to Scrape 전용 어댑터와 일반 schema.org Product JSON-LD 어댑터 분리
- 승인 도메인 목록, robots.txt 확인, 요청 간격·타임아웃, 로그인/차단 우회 없음

## 데모
`demo/SCENARIO.md`의 25초 시나리오와 스크린샷 포인트를 사용하세요. 샘플 모드는 직접 만든 데이터이며 **실제 웹 수집으로 표시하지 않습니다**. 공개 웹 모드는 실제 Books to Scrape 페이지를 읽습니다. 이 사이트의 가격·평점은 실습용입니다.

## 실행 방법
Python 3.11 이상. 이 폴더에서:

```bash
python -m venv .venv
# Windows PowerShell: .venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate
python -m pip install -r requirements.txt
python -m uvicorn app:app --host 127.0.0.1 --port 8101
```

브라우저에서 http://127.0.0.1:8101 을 여세요. 결과 파일은 이 폴더의 `output/`에 저장됩니다. 검색어는 **수집한 페이지의 상품명 안에서** 찾습니다.

실제 수집: 모드 `실제 공개 웹페이지`, URL `https://books.toscrape.com/`, 최대 페이지 1. 다른 승인 사이트는 `.env.example`을 `.env`로 복사하고 `ALLOWED_HOSTS`에 도메인을 추가하세요. 해당 사이트에 JSON-LD 상품 정보가 없으면 사이트별 어댑터 개발이 필요합니다. 모든 쇼핑몰에 자동 호환된다고 주장하지 않습니다.

```bash
python -m pytest -q
```

## 기술 스택과 구조
Python / FastAPI / HTTPX / BeautifulSoup / openpyxl / HTML·JavaScript

```text
app.py                 작업 API와 백그라운드 실행
collector/network.py   공개 웹 접근 정책
collector/sources.py   사이트별 추출 어댑터
collector/models.py    상품 정규화와 중복 제거
collector/pipeline.py  수집 파이프라인
collector/export.py    Excel 저장
static/                사용자 화면
```

## 활용 사례
협력사 공개 상품 카탈로그 정리, 가격 목록 비교용 자료 수집, 반복적인 상품 등록 자료 작성. 수집 범위·약관·요청량은 대상 사이트에 맞춰 합의합니다.

## 커스텀 개발 문의
업무 자동화, 승인된 웹 데이터 수집, Excel 자동 생성, 사이트별 수집 어댑터, 기존 수집기 오류 수정 작업을 의뢰할 수 있습니다.
