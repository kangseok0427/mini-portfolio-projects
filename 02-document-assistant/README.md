# AI 문서 분석 도우미 — 회사 문서에서 답과 근거 찾기

**PDF·TXT를 올리고 자연어로 질문하면 관련 문장을 검색하고 출처와 함께 답변하는 업무용 문서 도우미입니다.**

## 문제와 해결
계약서·제안서·업무 지침에서 기간·비용을 찾느라 파일을 반복해서 열어야 합니다. 문서를 검색 가능한 구간으로 나누고, 관련 근거와 답변을 한 화면에서 확인합니다.

## 주요 기능
복수 PDF/TXT 업로드, 페이지를 유지한 텍스트 추출, 겹치는 chunk, 한글 검색이 가능한 문자 TF-IDF 벡터 검색, 문서 비교를 위한 출처 분산 검색, LLM 질의응답, 문서명·페이지·원문 출처, SQLite 대화 기록, 새 문서 추가, 중복 파일 감지, 문서 삭제·초기화.

## 데모
`demo/SCENARIO.md`의 35초 흐름을 사용하세요. 가상 계약서·변경 제안서·비용 정책 PDF를 제공합니다. 핵심은 **계약서와 제안서를 혼동하지 않고 근거를 확인하는 모습**입니다.

기본 `demo` 모드는 **원문을 보여주는 검색 데모**이며 LLM을 호출하지 않습니다. AI 생성 답변 영상은 반드시 `api` 모드에서 실제 모델을 연결한 뒤 촬영하세요. API 키가 없는 상태를 실제 AI 호출처럼 꾸미지 않습니다.

## 실행 방법
Python 3.11 이상. 이 폴더에서:

```bash
python -m venv .venv
# Windows: .venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate
python -m pip install -r requirements.txt
python -m uvicorn app:app --host 127.0.0.1 --port 8102
```

http://127.0.0.1:8102 → `샘플 문서 넣기` → 질문. 문서와 대화는 `data/documents.sqlite3`에 남습니다. 문서 삭제는 오래된 근거가 답변에 남지 않도록 모든 대화 기록도 지웁니다.

### 실제 LLM 연결
`.env.example`을 `.env`로 복사합니다.

```dotenv
LLM_PROVIDER=api
LLM_BASE_URL=https://api.openai.com/v1
LLM_MODEL=사용할_모델_ID
LLM_API_KEY=발급받은_키
```

서버를 재시작하세요. OpenAI-compatible Chat Completions API 제공자는 base URL·model·key를 바꿔 연결할 수 있습니다. 다른 API 형식은 `rag/providers.py`에 어댑터를 추가하세요. 키는 서버 환경변수에만 보관하며 브라우저로 전달하지 않습니다.

```bash
python -m pytest -q
```

## 기술 스택과 구조
Python / FastAPI / pypdf / scikit-learn TF-IDF / HTTPX / SQLite / HTML·JavaScript

```text
rag/documents.py  PDF/TXT 추출과 chunk
rag/store.py      문서·근거·대화 저장
rag/search.py     로컬 벡터 검색
rag/providers.py  LLM 및 검색 데모 어댑터
app.py            업로드·검색·대화 API
static/           질문·답변·출처 화면
```

## 활용 사례와 한계
사내 매뉴얼 검색, 계약 자료 질의응답, 제안서 비교, 고객 상담용 지식 검색. TXT는 UTF-8, PDF는 텍스트 추출 가능한 파일을 지원합니다. 스캔본 OCR은 포함하지 않습니다. 파일당 10MB·200페이지, 문서 30개 한도입니다. 검색은 임베딩 API 대신 문자 TF-IDF를 사용하므로 매우 다른 표현의 의미 검색에는 추가 모델이 필요할 수 있습니다. LLM 답변 정확도를 보장하지 않으며 표시된 원문과 대조할 수 있습니다.

이 앱은 한 사람이 로컬에서 시연하는 구성입니다. 다중 사용자 서비스에는 로그인·조직별 문서 격리·업로드 검사 등을 추가해야 합니다. API 모드에서 검색 근거 일부는 설정된 모델 제공자에게 전달됩니다.

## 커스텀 개발 문의
회사 문서 검색, RAG 챗봇, LLM API 연동, PDF 처리, 업무용 AI 기능 추가, 기존 AI 서비스 오류 수정 작업을 의뢰할 수 있습니다.
