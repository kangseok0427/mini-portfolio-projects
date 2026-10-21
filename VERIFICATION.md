# 실행·검증 기록

갱신: 2026-10-21. Windows / Python 3.12 / Chrome / Java 25에서 확인했습니다.
Python 자동 테스트 **38개 통과**. 웹앱 3개의 실제 브라우저 녹화와 스크린샷을 추가했습니다.

| 프로젝트 | 이번에 직접 확인한 내용 | 남은 확인 |
| --- | --- | --- |
| 01 상품 수집 | pytest 6개, 실제 웹 버튼 → 상품 5개·중복 1개 제거 → Excel 다운로드, 다운로드 파일 6행과 헤더 고정 확인 | 고객 대상 사이트별 어댑터, 이번 녹화의 실제 외부 사이트 수집 |
| 02 문서 검색 | pytest 6개, TXT 2개·PDF 1개 실제 업로드 → 질문 → 원문 출처 2개, 브라우저 오류 없음 | 유료 LLM API 연결·생성 답변 품질 |
| 03 유지보수 | pytest 6개, 실제 로컬 HTTP API에서 BEFORE 3행 후 중단, AFTER 정상 주문 5개·중복 2개 제거·재시도 1회, 다운로드 Excel 6행 확인 | 고객 API별 연결·실제 업무 데이터 검증 |
| 04 AI NPC | 기존 배포 JAR의 Java 대화 코어 실행: 플레이어·NPC별 기억 분리, 재시작 후 4개 메시지 복원, 초기화 후 0개 | Paper 서버·Minecraft 클라이언트에서 NPC 클릭·채팅·재시작·다중 플레이어, 실제 LLM |
| 05 Discord 봇 | pytest 20개: 동시 클릭, 재시작, 고아 채널 복구, 삭제 채널 재생성, 일시 오류 시 상태 보존, 운영진 종료 권한, 서버 격리, 안전한 역할 검사, 비공개 권한, 탈퇴한 작성자 접근 차단, 영구 버튼·명령 등록 | 실제 봇 로그인, 서버 권한, 두 계정 가시성 확인, 재시작 후 버튼, 실제 Discord 영상 |

## 녹화 근거

- 각 웹 프로젝트 `demo/demo.mp4`: 실제 앱을 실행한 Chrome 화면 녹화. 무음 MP4이며 각 10MB 미만입니다.
- 각 `demo/01-*.png` ~ `03-*.png`: 실제 녹화 중 저장한 스크린샷입니다.
- 각 `demo/evidence.json`: 브라우저 시연 중 검사한 행 수·출처 수·파일 크기·브라우저 오류 기록입니다.
- `tools/record_demos.py`: 같은 시연을 재현하는 소스입니다. 네트워크 응답을 mock하지 않습니다. 서버 종료·영상 인코딩도 포함합니다.
- 녹화에 사용한 샘플은 자체 제작했습니다. 02 검색 모드는 LLM 호출이 아니며 03은 고객 납품 사례가 아닙니다.

## 재현

각 Python 프로젝트 디렉터리에서 의존성을 설치하고 `python -m pytest -q`를 실행합니다.
전체 녹화는 루트 README의 시연 자료 재생성 안내를 따릅니다.

Java 코어는 저장소 루트에서 실행합니다.

```bash
java -jar 04-minecraft-ai-npc/dist/ai-npc-1.0.0.jar --demo
```

이번 제한된 Windows 환경에서는 기본 임시 폴더 접근 오류가 있어, 쓰기 가능한 `tmp` 폴더를 만든 뒤
`java -Djava.io.tmpdir=tmp -jar 04-minecraft-ai-npc/dist/ai-npc-1.0.0.jar --demo`로 정상 종료를 확인했습니다.
Java 소스를 이번에 변경하지 않았으며 Maven/JUnit 재실행은 하지 않았습니다.
이전 저장소 기록의 Paper API 컴파일·JUnit 6개·shaded JAR 생성 결과와 이번 실행을 구분합니다.

## 환경 메모

검증 설치 버전: discord.py 2.7.1, pytest 9.1.1, pytest-asyncio 1.4.0,
FastAPI 0.156.4, Playwright 1.64.0. Python 3.12에서 discord.py의 audioop 사용에 관한
DeprecationWarning 1개가 출력되며 봇 테스트 20개는 통과했습니다.

Discord 테스트는 실제 SQLite와 테스트용 Discord gateway를 사용합니다. 실제 Discord 서버 연결 성공을 의미하지 않습니다.
외부 계정이나 유료 API를 사용하는 검증은 수행하지 않았습니다. 토큰·API 키는 포함하지 않았습니다.
