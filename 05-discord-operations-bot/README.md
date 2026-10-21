# Discord 서버 운영 봇 / Operations Bot

회원 역할 선택, 비공개 고객 문의, 운영 처리 기록을 하나의 봇으로 제공합니다.
Python · discord.py · SQLite. 작은 커뮤니티나 외주 상담 서버에 맞춘 샘플입니다.

## 제공 기능

- `/setup`: 서버 관리자가 현재 채널에 안내 패널 설치
- 버튼: 지정한 일반 회원 역할 지급·해제
- 버튼: 작성자·운영진·봇만 볼 수 있는 문의 채널 생성
- 사용자당 열린 문의 1개, 연속 클릭·재시작 후에도 기존 문의 재사용
- 운영진 버튼 또는 `/close`: 작성자 접근을 차단하고 채널을 보관
- `/audit`: 서버 관리자에게 최근 처리 기록 10개 표시
- SQLite에 처리자·시간·채널·작업 종류 저장. 대화 본문은 저장하지 않음
- 재시작 후 기존 버튼 유지, 채널 생성 직후 중단된 경우 채널 topic으로 복구

## 실행

Python 3.11 이상. 이 디렉터리에서 실행합니다.

```bash
python -m venv .venv
# Windows: .venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate
python -m pip install -r requirements.txt
# .env.example을 .env로 복사한 뒤 값을 입력
python bot.py
```

1. [Discord Developer Portal](https://discord.com/developers/applications)에서 앱과 봇을 만듭니다.
2. 서버에 `bot`, `applications.commands` 범위로 초대합니다.
3. 봇에 **View Channels, Send Messages, Read Message History, Manage Roles, Manage Channels** 권한을 줍니다. 관리자 권한은 필요하지 않습니다.
4. 권한이 전혀 없는 회원 역할, 별도의 운영진 역할, 문의용 카테고리를 만듭니다.
5. 봇 역할을 회원 역할보다 위에 배치합니다. 문의 카테고리에도 봇의 채널·역할 관리 권한을 허용합니다.
6. Discord 개발자 모드를 켜고 서버·역할·카테고리 ID를 복사해 `.env`에 넣습니다. 토큰도 `.env`에만 입력합니다.
7. 봇을 실행하고 서버 관리 권한으로 `/setup`을 실행합니다. 명령은 설정한 서버에만 동기화됩니다.

Message Content / Server Members 특권 인텐트는 사용하지 않습니다.
자유 텍스트를 읽는 봇이 아니라 버튼과 슬래시 명령으로 작동합니다.

## 확인과 시연

```bash
python -m pytest -q
```

자동 검증은 SQLite와 테스트용 Discord gateway를 사용합니다. 실제 Discord 로그인·채널 생성 영상과 구분합니다.
[촬영 순서](demo/SCENARIO.md)를 따라 테스트 서버에서 역할·문의 생성·권한·재시작을 확인할 수 있습니다.
실제 서버 연동 검증과 녹화는 아직 완료하지 않았습니다. 토큰은 채팅이나 GitHub에 올리지 않습니다.

## 운영 범위

SQLite 파일 하나를 사용하는 **봇 프로세스 1개**를 전제로 합니다. 다중 프로세스 배포나 대규모 서버용 구조는 아닙니다.
서버 소유자와 Administrator 권한 보유자는 Discord 자체 규칙에 따라 비공개 채널에도 접근할 수 있습니다.
회원 역할은 권한 값이 0인 역할만 허용합니다. 운영 권한이 있는 역할은 지급할 수 없습니다.
닫힌 문의 채널은 삭제하지 않으므로 운영진이 보관 기간에 따라 정리해야 합니다.
문의 생성 후 안내 메시지 전송만 실패했다면 채널은 유지됩니다. 운영진은 `/close`로 종료할 수 있습니다.
Discord API와 DB는 하나의 트랜잭션이 아니므로 종료 중 중단되면 운영진이 `/close`를 다시 실행해 마무리합니다.

## English

A configurable Discord operations bot with self-service roles, private support tickets,
staff-only closing, persistent buttons, SQLite audit events and restart recovery.
No privileged intents or Administrator permission required. One bot process per database.
Automated tests use a fake Discord gateway; live Discord verification is pending.
