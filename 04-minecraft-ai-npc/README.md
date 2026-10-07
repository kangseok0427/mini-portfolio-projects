# Minecraft AI NPC — 성격과 기억을 가진 게임 속 주민

**플레이어가 NPC를 우클릭해 대화하면, NPC가 자신의 성격과 그 플레이어의 이전 대화를 바탕으로 답하는 Paper 플러그인입니다.**

## English introduction
An AI dialogue plugin for Paper Minecraft servers. Create villagers with distinct personalities, interact to start a private conversation, and give each player a separate memory for each NPC. LLM requests run off the server thread. Supports configurable OpenAI-compatible APIs and a clearly labelled, scripted offline demonstration.

Custom work available: Minecraft plugins, AI NPC dialogue, API integrations, existing plugin fixes, and gameplay features.

## 문제와 해결
고정 문장만 반복하는 NPC는 플레이어의 이전 질문을 기억하지 못합니다. 주민 NPC에 성격 프롬프트와 플레이어별 대화 기억을 붙여, “철 어디서 구해?” 다음에 “내가 아까 뭐 찾았지?”라고 물으면 이전 대화를 이어갈 수 있게 합니다.

## 주요 기능

- NPC 생성·삭제·표시 이름 변경, 상인·안내인·사용자 지정 성격
- 우클릭으로 대화 대상 선택 → 일반 채팅으로 질문 → `/ainpc exit`로 종료
- `/ainpc talk` 명령으로 직접 질문, 플레이어와 NPC 조합별 기억 격리
- NPC별 기억 켜기·끄기·초기화, 최근 6회 대화 기억과 재시작 후 보존
- 환경변수 API 키, 제공자 교체 인터페이스, 설정 재로딩
- API 타임아웃·입력 길이 제한·쿨다운·작업 큐 제한·요청 실패 안내
- HTTP와 대화 기억 저장은 작업 스레드, 엔티티·플레이어 처리는 서버 스레드
- 삭제·기억 초기화 뒤 늦게 도착한 답변이 기억을 되살리지 않도록 버전 검사
- NPC 등록 파일, 엔티티 태그, 청크 로드 후 기존 주민 재사용

이 프로젝트의 NPC는 **주민 엔티티**입니다. Citizens, 플레이어 스킨, 자동 거래·아이템 지급, AI 명령 실행 기능은 포함하지 않습니다.

## 데모
`demo/SCENARIO.md`의 40초 영상과 스크린샷 3장 포인트를 사용하세요. `demo/IN_GAME_CHECKLIST.md`에는 실제 서버에서 확인할 항목이 있습니다.

기본 `provider: demo`는 **대본 기반 로컬 대화이며 LLM 호출이 없습니다**. 표시를 숨기고 실제 생성형 AI처럼 홍보하지 마세요. `provider: api`와 실제 키·모델로 전환하면 실제 LLM이 답변합니다. 북쪽 광산은 샘플 세계관 설정이며 실제 지형을 자동으로 찾지 않습니다.

## 실행 방법

### 1. 준비와 빌드
기준: **Paper 26.2 build 132 STABLE / JDK 25 / Maven 3.9+**. 2026-10-07 공식 다운로드 API에서 확인했으며, 26.3은 BETA여서 제외했습니다. Paper는 별도로 설치합니다.

```bash
java -version
mvn clean verify
```

빌드 결과: `target/ai-npc-1.0.0.jar`. 패키지에는 편의를 위해 같은 결과물인 `dist/ai-npc-1.0.0.jar`도 제공합니다. **Paper API는 서버에서 제공**하고 Gson은 충돌을 피하도록 패키지 이름을 바꿔 JAR에 포함합니다.

### 2. 서버 설치
1. [Paper 공식 다운로드](https://papermc.io/downloads/paper)에서 기준 버전 서버를 준비합니다.
2. 서버를 한 번 실행하고 Minecraft EULA를 직접 읽어 동의 여부를 결정합니다. 이 프로젝트는 동의를 자동 설정하지 않습니다.
3. 서버가 정지된 상태에서 JAR을 서버의 `plugins/` 폴더에 넣습니다.
4. Java 25로 서버를 시작합니다. 설정은 `plugins/GaonAINPC/config.yml`에 생성됩니다.
5. OP 또는 `ainpc.admin` 권한을 가진 플레이어로 접속합니다.

```text
/ainpc create merchant 상인 가온
/ainpc personality merchant merchant
/ainpc memory merchant on
```

생성한 주민을 우클릭한 뒤 채팅에 `철 어디서 구해?`를 입력합니다. 쿨다운 3초가 지난 뒤 `내가 아까 뭐 찾는다고 했지?`를 입력하면 앞선 질문을 기억합니다. `/ainpc exit`로 대화를 종료합니다.

### 3. 실제 LLM 연결
`config.yml`을 수정합니다.

```yaml
provider: api
api:
  base-url: https://api.openai.com/v1
  model: YOUR_MODEL_ID
  key-env: AINPC_API_KEY
  timeout-seconds: 20
  max-tokens: 220
```

서버를 시작하는 프로세스에 키를 넣습니다. `.env.example`은 설명용이며 플러그인이 `.env`를 자동으로 읽지는 않습니다.

```bash
# macOS/Linux: 현재 터미널에만 적용
export AINPC_API_KEY='YOUR_API_KEY'
java -Xms2G -Xmx2G -jar paper.jar --nogui
```

```powershell
# Windows PowerShell: 현재 터미널에만 적용
$env:AINPC_API_KEY = 'YOUR_API_KEY'
java -Xms2G -Xmx2G -jar paper.jar --nogui
```

키 환경변수 변경은 서버 재시작이 필요합니다. 모델·프롬프트·쿨다운·거리·provider 설정은 `/ainpc reload`로 다시 읽습니다. 메모리 용량 설정은 재시작 시 적용됩니다. HTTP는 localhost 로컬 모델만 허용하고 원격 API에는 HTTPS를 사용합니다. 다른 API 형식은 `DialogueProvider` 구현을 추가하면 됩니다.

### 명령과 권한

| 명령 | 용도 | 권한 |
| --- | --- | --- |
| `/ainpc create <id> [표시 이름]` | 현재 위치에 NPC 생성 | admin |
| `/ainpc remove <id>` | 주민·등록·기억 삭제 | admin |
| `/ainpc name <id> <이름>` | 표시 이름 변경 | admin |
| `/ainpc personality <id> merchant\|guide` | 설정 프리셋 사용 | admin |
| `/ainpc personality <id> custom <프롬프트>` | 개별 성격 지정 | admin |
| `/ainpc memory <id> on\|off\|clear` | 기억 설정·초기화 | admin |
| `/ainpc talk <id> <질문>` | 가까운 NPC에 질문 | use |
| `/ainpc exit` | 채팅 대상 해제 | 플레이어 |
| `/ainpc list` / `/ainpc help` | 목록·사용법 | 전체 |
| `/ainpc reload` | 설정 재로딩 | admin |

`ainpc.use`는 기본 허용, `ainpc.admin`은 기본 OP입니다. 성격 변경·기억 on/off 전환은 기존 기억을 지웁니다. NPC 50개, 동시 작업 스레드 2개·대기 큐 16개, 기억 조합 500개가 기본 범위입니다. 대화 상대는 가까이 있어야 합니다.

### 서버 없이 핵심 기능 확인

```bash
java -jar dist/ai-npc-1.0.0.jar --demo
```

같은 Java 대화·메모리 코드로 상인의 기억, 다른 플레이어·NPC 격리, 파일 저장 후 복원, 기억 삭제를 출력합니다. **이 출력은 Minecraft 실행 화면이 아닙니다.** 자동 테스트는 `mvn test`입니다.

## 기술 스택과 구조
Java 25 / Paper API / Adventure / Java HttpClient / Gson / Maven / JUnit 5

```text
src/main/java/dev/gaon/ainpc/
  AiNpcPlugin.java       명령·이벤트·엔티티·비동기 작업 조율
  Npc.java               NPC 등록 정보
  core/
    DialogueProvider.java 제공자 인터페이스
    CompatibleProvider.java HTTP API 어댑터
    DemoProvider.java    대본 기반 대화
    MemoryStore.java     격리·제한·원자적 파일 저장
    DemoConsole.java     서버 없이 핵심 데모
src/main/resources/      plugin.yml, config.yml
src/test/                핵심 기능 자동 테스트
dist/                    빌드된 플러그인 JAR
```

## 데이터와 활용 사례
스토리 서버의 상인·안내인, RPG 퀘스트 대화, 이벤트 NPC, 서버 FAQ 안내에 활용할 수 있습니다. 기억은 서버의 `memory.json`에 플레이어 UUID·NPC ID·대화 내용으로 저장됩니다. API 모드에서는 NPC 프롬프트와 해당 대화 기록을 설정한 모델 제공자에게 전송합니다. 운영 서버에 넣기 전 이용자에게 안내하고 보관 정책을 정하세요. 키·사용자 대화·운영 서버 파일은 Git에 올리지 않습니다.

플러그인은 요청 실패를 처리하지만 LLM의 답변 내용이 정확함을 보장하지 않습니다. 거래나 서버 관리 같은 동작으로 답변을 실행하지 않습니다. Folia 지원은 포함하지 않습니다. 새 Paper 버전으로 변경할 때 다시 빌드하고 게임 안에서 검증하세요.

## 검증 범위
최신 안정 Paper API에 대한 실제 컴파일, JAR 생성, 핵심 메모리·API 요청 구조 자동 테스트, 독립 콘솔 데모를 수행했습니다. 실제 유료 LLM 요청과 Minecraft 클라이언트 접속·우클릭 장면은 이 환경에서 검증하지 않았습니다. 게임 촬영·설치 확인에는 `demo/IN_GAME_CHECKLIST.md`를 사용하세요.

기준 자료: [Paper 프로젝트 설정](https://docs.papermc.io/paper/dev/project-setup/), [Java 요구사항](https://docs.papermc.io/paper/getting-started/), [26.2 빌드 채널](https://fill.papermc.io/v3/projects/paper/versions/26.2/builds).

## 커스텀 개발 문의
Minecraft Plugin 제작, 기존 Plugin 오류 수정·기능 추가, AI NPC, 게임용 API 연동, NPC별 성격·기억 시스템, 서버 업무 자동화를 의뢰할 수 있습니다. Custom Minecraft plugin development, plugin maintenance, AI NPC systems, and API integration available.
