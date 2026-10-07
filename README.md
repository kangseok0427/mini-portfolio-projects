# 업무 자동화·AI·유지보수·Minecraft 외주 포트폴리오

**반복 작업을 줄이고, 문서에서 답을 찾고, 기존 프로그램을 고치고, 게임에 AI 대화를 붙이는 4개의 실행 가능한 미니 프로젝트입니다.**

UI 디자인보다 실제 업무 흐름과 결과물을 보여주는 데 집중했습니다. 각 폴더는 독립적으로 설치·실행할 수 있으며 자신의 GitHub 저장소로 분리할 수 있습니다. 실행 파일·의존성·환경 설정 예제·README·20~45초 촬영 시나리오·최소 3개의 스크린샷 포인트를 포함합니다.

## 무엇을 만들 수 있는지 바로 보여주는 구성

| 프로젝트 | 고객이 보는 결과 | 실행 | 데모 길이 |
| --- | --- | --- | --- |
| [01 상품정보 수집기](01-product-collector/README.md) | URL 입력 → 상품 목록 → Excel | Python, 8101 포트 | 25초 |
| [02 AI 문서 분석](02-document-assistant/README.md) | 문서 업로드 → 질문 → 답변·원문 근거 | Python, 8102 포트 | 35초 |
| [03 프로그램 FIX](03-maintenance-case/README.md) | API 오류로 중단 → 재시도·정상 저장 | Python, 8103 포트 | 30초 |
| [04 Minecraft AI NPC](04-minecraft-ai-npc/README.md) | 상인에게 질문 → 이전 대화 기억 | Paper 26.2 / Java 25 | 40초 |

## 빠른 시작
Python 프로젝트는 Python 3.11 이상입니다. 프로젝트마다 아래처럼 별도 가상환경을 만들어 실행하세요.

```bash
cd 01-product-collector
python -m venv .venv
# Windows: .venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate
python -m pip install -r requirements.txt
python -m uvicorn app:app --host 127.0.0.1 --port 8101
```

2번은 해당 폴더에서 8102, 3번은 해당 폴더에서 8103으로 실행합니다. Minecraft는 `04-minecraft-ai-npc/dist/ai-npc-1.0.0.jar`을 Paper 서버의 `plugins/`에 넣거나 Maven으로 다시 빌드합니다. 상세 설정은 각 README에 있습니다.

키 없이도 1번 공개 웹·샘플 수집, 2번 문서 검색·원문 근거 데모, 3번 유지보수 비교, 4번 대본 대화·기억 데모를 볼 수 있습니다. **2번·4번의 실제 LLM 생성 답변은 자신의 API 키와 모델 설정이 필요합니다.** 키·기존 가온 DB·기존 가온 앱 설정은 이 패키지에 포함하지 않았습니다.

## 결과 확인과 촬영
각 `demo/SCENARIO.md`는 첫 3초 자막, 전체 장면 구성, 촬영할 화면 3장 이상을 설명합니다. 실제 웹 화면·게임 화면·영상 파일은 포함하지 않았습니다. 실행 후 해당 포인트를 촬영하세요. 이 환경에서는 브라우저 실행 제한과 Minecraft 클라이언트 부재로 실제 촬영을 수행하지 못했습니다.

1번은 Excel 파일까지 열어 보여주세요. 2번은 문서명·페이지·원문 출처가 보이게 촬영하세요. 3번은 BEFORE/AFTER를 동시에 보여주세요. 4번은 첫 질문과 기억 회상을 이어서 보여주세요. API 키·다른 고객의 파일·개인 정보는 촬영 화면에 올리지 마세요.

샘플 데이터는 직접 만든 가상 자료입니다. 3번은 오류를 주입한 자체 데모이며 실제 고객 작업 사례가 아닙니다. 2번 검색 데모와 4번 대본 데모를 실제 LLM 호출처럼 홍보하지 않습니다.

## 검증
`VERIFICATION.md`에 수행한 검증과 남은 실제 환경 확인을 기록했습니다. Python 18개·Java 6개 핵심 자동 테스트를 통과했고 Paper API 컴파일과 플러그인 JAR 생성까지 확인했습니다. 실제 유료 LLM 호출과 Minecraft 클라이언트 접속은 미검증입니다.

```bash
# 각 Python 프로젝트 폴더에서
python -m pytest -q
# Minecraft 프로젝트 폴더에서
mvn clean verify
java -jar dist/ai-npc-1.0.0.jar --demo
```

## 크몽·위시켓 소개 문구

**제목:** 반복 업무 자동화·AI 기능 연동·기존 프로그램 수정해드립니다

**소개:** 상품 목록을 Excel로 정리하는 자동화, PDF·문서 검색 AI, API 오류 처리와 기존 프로그램 수정 작업을 제작합니다. 현재 사용하는 프로그램이나 작업 과정을 알려주시면 필요한 범위와 결과물을 먼저 정리해드립니다. 대규모 신규 개발뿐 아니라 작은 버그 수정·기능 추가도 문의할 수 있습니다.

**상품별 한 줄:**
- 업무 자동화: “매번 복사하던 상품정보, 클릭 한 번으로 Excel까지 정리합니다.”
- 문서 AI: “회사 문서에서 답을 찾고, 어느 부분을 근거로 했는지 보여드립니다.”
- 유지보수: “멈추던 프로그램의 오류를 고치고, 필요한 저장 기능도 추가합니다.”
- Minecraft: “NPC마다 다른 성격과 플레이어별 대화 기억을 붙입니다.”

소개는 자신이 실제로 제공할 수 있는 범위·응답 시간·가격에 맞춰 등록하세요. 위시켓에는 해당 업무와 가까운 프로젝트 링크와 구체적인 작업 범위를 제시하세요.

## Fiverr introduction

**Title:** I will build Python automation, AI tools, or fix your existing program

**Description:** I build practical tools for repetitive tasks, document Q&A with sources, and reliable API integrations. I can also fix bugs and add features to existing Python applications. Share your current workflow, sample data, and expected output so we can define a clear scope.

**Minecraft title:** I will create or fix a Minecraft Paper plugin with AI NPC dialogue

**Minecraft description:** Give your NPCs distinct personalities and separate memories for each player. This portfolio demonstrates NPC management, asynchronous LLM integration, configurable prompts, and persistent dialogue memory. Custom Paper plugin development and existing plugin maintenance are available.

## 가온 SNS 홍보 자막
각 영상 마지막 3초에 **“우리 업무에 맞춘 자동화·AI·프로그램 수정 문의”**를 표시하세요. Minecraft 영상은 **“Minecraft 플러그인 제작·수정 / Custom Paper plugins”**을 사용하세요. 자신의 실제 문의 채널을 설명란·프로필에 연결하면 됩니다.

## GitHub 공개
폴더 하나씩 분리하거나 이 묶음을 하나의 저장소로 사용할 수 있습니다. `.gitignore`가 `.env`·실행 중 생성되는 문서 DB·결과 파일·가상환경·빌드 임시 파일을 제외합니다. 공개 전 본인 소개·문의 주소와 라이선스를 결정하고 `.env`가 추적되지 않는지 확인하세요. README는 실습용 샘플과 실제 API 기능의 차이를 그대로 유지하세요.
