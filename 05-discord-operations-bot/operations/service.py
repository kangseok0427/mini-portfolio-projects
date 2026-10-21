"""Discord-independent ticket orchestration; gateway owns Discord API calls."""
import asyncio


class UserError(Exception):
    pass


class TicketService:
    def __init__(self, store, gateway):
        self.store = store
        self.gateway = gateway
        # Keep read/API/write sequences serialized in this small single-process bot.
        self.lock = asyncio.Lock()

    async def open(self, guild_id, owner_id):
        async with self.lock:
            ticket = self.store.active(guild_id, owner_id)
            if ticket:
                channel = await self.gateway.fetch(ticket['channel_id'])
                if channel is not None:
                    return channel, False
                self.store.closed(guild_id, owner_id, ticket['channel_id'], 'ticket_missing')
            # Recover creation interrupted between Discord success and SQLite commit.
            channel = await self.gateway.find_orphan(guild_id, owner_id)
            if channel is None:
                channel = await self.gateway.create(guild_id, owner_id)
            self.store.opened(guild_id, owner_id, channel.id)
            return channel, True

    async def close(self, guild_id, actor_id, channel_id, is_staff):
        async with self.lock:
            if not is_staff:
                raise UserError('문의 종료는 담당 운영진만 할 수 있습니다.')
            ticket = self.store.ticket(guild_id, channel_id)
            if ticket is None:
                raise UserError('열린 문의 티켓이 아닙니다.')
            # Archive access first. A failed API call leaves the DB open for retry.
            await self.gateway.archive(channel_id, ticket['owner_id'])
            self.store.closed(guild_id, actor_id, channel_id)
