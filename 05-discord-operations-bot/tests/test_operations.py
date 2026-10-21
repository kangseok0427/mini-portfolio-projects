import asyncio
from types import SimpleNamespace as NS
from unittest.mock import AsyncMock
import pytest
import discord
from operations.store import Store
from operations.service import TicketService, UserError
from operations.config import Config
from operations.discord_app import (Panel, ClosePanel, Gateway, OperationsClient,
                                    validate_member_role)


class FakeGateway:
    def __init__(self):
        self.channels = {}
        self.count = 100
        self.fail_fetch = False
        self.fail_archive = False

    async def fetch(self, channel_id):
        if self.fail_fetch:
            raise TimeoutError('temporary REST failure')
        return self.channels.get(channel_id)

    async def find_orphan(self, guild_id, owner_id):
        return next((c for c in self.channels.values()
                     if c.guild_id == guild_id and c.owner_id == owner_id and not c.closed), None)

    async def create(self, guild_id, owner_id):
        await asyncio.sleep(0)  # force overlapping requests to interleave
        self.count += 1
        channel = NS(id=self.count, guild_id=guild_id, owner_id=owner_id, closed=False)
        self.channels[channel.id] = channel
        return channel

    async def archive(self, channel_id, owner_id):
        if self.fail_archive:
            raise TimeoutError('Discord unavailable')
        self.channels[channel_id].closed = True


@pytest.fixture
def setup(tmp_path):
    store = Store(tmp_path / 'ops.sqlite3')
    gateway = FakeGateway()
    yield store, gateway, TicketService(store, gateway)
    store.close()


async def test_concurrent_clicks_create_one_channel(setup):
    store, gateway, service = setup
    results = await asyncio.gather(*(service.open(1, 2) for _ in range(12)))
    assert len(gateway.channels) == 1
    assert sum(created for _, created in results) == 1
    assert len(store.recent(1)) == 1


async def test_restart_reuses_existing_channel(setup, tmp_path):
    store, gateway, service = setup
    channel, _ = await service.open(1, 2)
    reopened = Store(tmp_path / 'ops.sqlite3')
    try:
        recovered, created = await TicketService(reopened, gateway).open(1, 2)
        assert recovered.id == channel.id and not created
    finally:
        reopened.close()


async def test_orphan_channel_is_adopted(setup):
    store, gateway, service = setup
    orphan = await gateway.create(1, 2)
    channel, _ = await service.open(1, 2)
    assert channel.id == orphan.id and len(gateway.channels) == 1
    assert store.active(1, 2)['channel_id'] == orphan.id


async def test_deleted_channel_can_be_replaced(setup):
    store, gateway, service = setup
    old, _ = await service.open(1, 2)
    del gateway.channels[old.id]
    new, _ = await service.open(1, 2)
    assert new.id != old.id
    assert store.recent(1)[1]['action'] == 'ticket_missing'


async def test_network_failure_does_not_discard_ticket(setup):
    store, gateway, service = setup
    old, _ = await service.open(1, 2)
    gateway.fail_fetch = True
    with pytest.raises(TimeoutError):
        await service.open(1, 2)
    assert store.active(1, 2)['channel_id'] == old.id
    assert len(gateway.channels) == 1


async def test_only_staff_can_close(setup):
    store, gateway, service = setup
    channel, _ = await service.open(1, 2)
    with pytest.raises(UserError):
        await service.close(1, 2, channel.id, False)
    assert not channel.closed
    assert store.active(1, 2)


async def test_close_is_scoped_to_guild(setup):
    _, gateway, service = setup
    channel, _ = await service.open(1, 2)
    with pytest.raises(UserError):
        await service.close(99, 3, channel.id, True)
    assert not channel.closed


async def test_failed_close_is_retryable(setup):
    store, gateway, service = setup
    channel, _ = await service.open(1, 2)
    gateway.fail_archive = True
    with pytest.raises(TimeoutError):
        await service.close(1, 3, channel.id, True)
    assert store.active(1, 2)
    gateway.fail_archive = False
    await service.close(1, 3, channel.id, True)
    assert not store.active(1, 2)
    assert channel.closed
    new, _ = await service.open(1, 2)
    assert new.id != channel.id
    assert store.recent(1)[1]['actor_id'] == 3


def make_role(permissions=0, managed=False, role_id=10, position=1):
    class Role:
        id = role_id
        def __init__(self):
            self.managed = managed
            self.permissions = discord.Permissions(permissions)
        def is_default(self):
            return self.id == 1
        def __ge__(self, other):
            return position >= other
    return Role()


@pytest.mark.parametrize('role', [make_role(permissions=8), make_role(managed=True),
    make_role(role_id=1), make_role(role_id=20), make_role(position=10), None])
def test_unsafe_role_is_rejected(role):
    bot = NS(top_role=5, guild_permissions=NS(manage_roles=True))
    with pytest.raises(UserError):
        validate_member_role(role, 20, bot)


def test_plain_role_is_allowed():
    validate_member_role(make_role(), 20, NS(top_role=5, guild_permissions=NS(manage_roles=True)))


async def test_persistent_views_and_commands_construct(tmp_path):
    cfg = Config('not-a-real-token', 1, 20, 10, 30, str(tmp_path / 'ops.sqlite3'))
    client = OperationsClient(cfg)
    try:
        panel, close = Panel(client), ClosePanel(client)
        assert panel.is_persistent() and close.is_persistent()
        assert len(panel.children) == 2 and len(close.children) == 1
        assert {c.name for c in client.tree.get_commands(guild=discord.Object(id=1))} == {'setup','audit','close'}
        assert not client.intents.message_content and not client.intents.members
    finally:
        await client.close()


async def test_wrong_guild_is_rejected():
    interaction = NS(guild_id=99, user=NS(), response=NS(send_message=AsyncMock()))
    assert not await Panel(NS(cfg=NS(guild_id=1))).interaction_check(interaction)
    interaction.response.send_message.assert_awaited_once()


async def test_private_channel_has_explicit_overwrites():
    everyone, staff, bot, member = object(), object(), object(), object()
    category = NS(permissions_for=lambda who: NS(manage_channels=True))
    guild = NS(id=1, default_role=everyone, me=bot,
               fetch_member=AsyncMock(return_value=member), create_text_channel=AsyncMock())
    gateway = Gateway(NS())
    gateway.resources = lambda _: (guild, staff, category)
    await gateway.create(1, 2)
    kwargs = guild.create_text_channel.call_args.kwargs
    overwrites = kwargs['overwrites']
    assert set(overwrites) == {everyone, staff, bot, member}
    assert overwrites[everyone].view_channel is False
    assert overwrites[member].view_channel is True
    assert kwargs['topic'] == 'portfolio-ticket:1:2'


async def test_errors_are_ephemeral_and_deferred():
    interaction = NS(response=NS(defer=AsyncMock()), followup=NS(send=AsyncMock()))
    async def failure():
        raise UserError('expected')
    await Panel(NS()).perform(interaction, failure)
    interaction.response.defer.assert_awaited_once_with(ephemeral=True, thinking=True)
    interaction.followup.send.assert_awaited_once_with('expected', ephemeral=True)


async def test_archive_denies_departed_owner_and_preserves_other_permissions():
    everyone = discord.Object(id=1, type=discord.Role)
    owner = discord.Object(id=2, type=discord.Member)
    staff = discord.Object(id=3, type=discord.Role)
    channel = NS(guild=NS(id=1), edit=AsyncMock(), overwrites={
        everyone: discord.PermissionOverwrite(view_channel=False),
        owner: discord.PermissionOverwrite(view_channel=True),
        staff: discord.PermissionOverwrite(view_channel=True)})
    gateway = Gateway(NS(fetch_channel=AsyncMock(return_value=channel)))
    await gateway.archive(100, 2)
    kwargs = channel.edit.call_args.kwargs
    assert kwargs['topic'] == 'closed-ticket:1:2'
    permissions = {key.id: value for key, value in kwargs['overwrites'].items()}
    assert permissions[1].view_channel is False
    assert permissions[2].view_channel is False
    assert permissions[3].view_channel is True
