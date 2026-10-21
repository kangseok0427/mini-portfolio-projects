from dataclasses import dataclass
import os


@dataclass(frozen=True)
class Config:
    token: str
    guild_id: int
    staff_role_id: int
    member_role_id: int
    ticket_category_id: int
    database_path: str

    @classmethod
    def from_env(cls):
        names = ('GUILD_ID', 'STAFF_ROLE_ID', 'MEMBER_ROLE_ID', 'TICKET_CATEGORY_ID')
        values = [int(os.environ.get(name, '0')) for name in names]
        if any(value <= 0 for value in values):
            raise ValueError('서버·역할·카테고리 ID를 .env에 설정해 주세요.')
        if len(set(values[1:3])) != 2 or values[0] in values[1:3]:
            raise ValueError('운영진·회원 역할은 서로 다르고 @everyone 역할이 아니어야 합니다.')
        token = os.environ.get('DISCORD_TOKEN', '').strip()
        if not token:
            raise ValueError('DISCORD_TOKEN이 필요합니다. 토큰을 GitHub에 올리지 마세요.')
        return cls(token, *values, os.environ.get('DATABASE_PATH', 'data/operations.sqlite3'))
