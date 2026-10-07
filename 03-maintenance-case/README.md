# 기존 프로그램 FIX — 멈추던 주문 동기화를 복구하다

**API 오류에 중단되고 중복을 저장하던 주문 수집 프로그램을 수정하고 Excel 저장을 추가한 BEFORE/AFTER 데모입니다.**

## 문제
실제 외주에서 볼 수 있는 “주문 API → 파일 저장” 구조에 일시적 503, 중복 주문, 잘못된 금액, 페이지별 덮어쓰기 문제가 있습니다. **직접 제작한 오류 주입 사례이며 실제 고객 사례로 주장하지 않습니다.**

## 해결 방법과 기능
| BEFORE | AFTER |
|---|---|
| 503 한 번에 전체 중단 | 일시 오류 재시도, 실패 페이지 격리 |
| 중복 주문 저장 | 주문번호 기준 중복 제거 |
| 금액을 바로 float 변환 | Decimal 검증, 잘못된 행만 제외 |
| 페이지마다 불완전 파일 저장 | 검증한 행을 SQLite 트랜잭션 저장 |
| CSV만 지원 | CSV + Excel + SQLite |
| API URL 하드코딩 | 환경변수로 설정 분리 |

작업 로그·저장 건수·중복 수·재시도·실제 처리 시간을 보여줍니다. 처리 시간이 더 빠르다는 주장은 하지 않습니다. 안정성과 데이터 완성도 개선이 핵심입니다.

## 데모
`demo/SCENARIO.md`를 따라 같은 데이터를 두 버전에 입력하세요. BEFORE는 3행(중복 포함)을 저장하고 503에서 멈춥니다. AFTER는 503을 재시도해 정상 주문 5건을 저장하고 중복 2건·잘못된 가격 1건을 처리합니다.

## 실행 방법
Python 3.11 이상. 이 폴더에서:

```bash
python -m venv .venv
# Windows: .venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate
python -m pip install -r requirements.txt
python -m uvicorn app:app --host 127.0.0.1 --port 8103
```

http://127.0.0.1:8103 에서 BEFORE/AFTER를 실행합니다. 기본 로컬 API도 이 앱이 제공하므로 데모는 **8103 포트**로 실행하세요. AFTER의 API URL·타임아웃·재시도는 `.env.example`을 복사해 변경할 수 있습니다. 외부 API의 인증·응답 필드는 별도 어댑터를 적용해야 합니다.

```bash
python -m pytest -q
```

## 기술 스택과 구조
Python / FastAPI / HTTPX / SQLite / Decimal / openpyxl

```text
before/legacy.py  의도적인 오류가 있는 기존 코드
after/sync.py    재시도·검증·중복 제거·저장
after/export.py  CSV와 Excel
dataset.py       가상 주문 샘플
app.py           오류 주입 API·실행 비교 화면
```

## 활용 사례
API 연동 오류 수정, 기존 자동화 도구 유지보수, 파일 저장 오류 복구, CSV 프로그램에 Excel 기능 추가. BEFORE는 문제를 설명하기 위한 코드이므로 실제 운영에 사용하지 마세요.

## 커스텀 개발 문의
현재 사용 중인 프로그램의 오류 수정, API 연결 문제 해결, 예외처리 보강, 코드 정리와 기능 추가 작업을 의뢰할 수 있습니다.
