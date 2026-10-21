import asyncio
import logging
import discord
from discord import app_commands
from .service import TicketService, UserError
from .store import Store

log = logging.getLogger(__name__)


def validate_member_role(role, staff_role_id, bot_member):
    if (role is None or role.is_default() or role.managed
            or role.id == staff_role_id or role.permissions.value != 0):
        raise UserError('회원 역할은 권한이 없는 일반 역할이어야 합니다.')
    if role >= bot_member.top_role or not bot_member.guild_permissions.manage_roles:
        raise UserError('봇 역할을 회원 역할 위로 이동하고 역할 관리 권한을 주세요.')


class Gateway:
    def __init__(self, client):
        self.client = client

    def resources(self, guild_id):
        guild = self.client.get_guild(guild_id)
        cfg = self.client.cfg
        if guild is None or guild_id != cfg.guild_id:
            raise UserError('설정된 서버에서만 사용할 수 있습니다.')
        staff = guild.get_role(cfg.staff_role_id)
        category = guild.get_channel(cfg.ticket_category_id)
        if (staff is None or staff.is_default()
                or not isinstance(category, discord.CategoryChannel)):
            raise UserError('운영진 역할과 문의 카테고리 설정을 확인해 주세요.')
        return guild, staff, category

    async def fetch(self, channel_id):
        try:
            return await self.client.fetch_channel(channel_id)
        except discord.NotFound:
            return None

    async def find_orphan(self, guild_id, owner_id):
        guild, _, _ = self.resources(guild_id)
        marker = f'portfolio-ticket:{guild_id}:{owner_id}'
        # REST list also covers a crash before the channel gateway event arrived.
        return next((c for c in await guild.fetch_channels()
                     if isinstance(c, discord.TextChannel) and c.topic == marker), None)

    async def create(self, guild_id, owner_id):
        guild, staff, category = self.resources(guild_id)
        member = await guild.fetch_member(owner_id)
        if not category.permissions_for(guild.me).manage_channels:
            raise UserError('문의 카테고리에 봇의 채널 관리 권한이 필요합니다.')
        return await guild.create_text_channel(
            f'ticket-{owner_id}', category=category,
            topic=f'portfolio-ticket:{guild_id}:{owner_id}',
            overwrites={
                guild.default_role: discord.PermissionOverwrite(view_channel=False),
                guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True,
                    read_message_history=True, manage_channels=True, manage_roles=True),
                member: discord.PermissionOverwrite(view_channel=True, send_messages=True,
                    read_message_history=True),
                staff: discord.PermissionOverwrite(view_channel=True, send_messages=True,
                    read_message_history=True),
            }, reason='User requested a private support ticket')

    async def archive(self, channel_id, owner_id):
        channel = await self.fetch(channel_id)
        if channel is None:
            return
        # edit(overwrites=...) supports Object targets, including a departed owner.
        overwrites = {target: value for target, value in channel.overwrites.items()
                      if target.id != owner_id}
        overwrites[discord.Object(id=owner_id, type=discord.Member)] = discord.PermissionOverwrite(view_channel=False)
        # Change access and recovery marker in one Discord edit before the DB commit.
        await channel.edit(overwrites=overwrites, topic=f'closed-ticket:{channel.guild.id}:{owner_id}',
                           reason='Support ticket archived')


class OperationView(discord.ui.View):
    def __init__(self, client):
        super().__init__(timeout=None)
        self.client = client

    async def interaction_check(self, interaction):
        if (interaction.guild_id != self.client.cfg.guild_id
                or not isinstance(interaction.user, discord.Member)):
            await interaction.response.send_message('설정된 서버에서만 사용해 주세요.', ephemeral=True)
            return False
        return True

    async def perform(self, interaction, action):
        await interaction.response.defer(ephemeral=True, thinking=True)
        try:
            text = await action()
        except UserError as error:
            text = str(error)
        except discord.Forbidden:
            text = '봇 권한이 부족합니다. 운영진에게 역할 순서와 채널 권한 확인을 요청해 주세요.'
        except discord.HTTPException:
            text = 'Discord 요청에 실패했습니다. 잠시 후 다시 시도해 주세요.'
        except Exception:
            log.exception('Operation failed')
            text = '처리하지 못했습니다. 운영진이 실행 로그를 확인해 주세요.'
        await interaction.followup.send(text, ephemeral=True)

class Panel(OperationView):
    @discord.ui.button(label='회원 역할 받기 / 해제', style=discord.ButtonStyle.secondary,
                       custom_id='operations:member:v1')
    async def member(self, interaction, button):
        async def action():
            # Prevent overlapping toggle requests from one or several users.
            async with self.client.role_lock:
                guild = interaction.guild
                role = guild.get_role(self.client.cfg.member_role_id)
                validate_member_role(role, self.client.cfg.staff_role_id, guild.me)
                member = await guild.fetch_member(interaction.user.id)
                if role in member.roles:
                    await member.remove_roles(role, reason='Self-service membership')
                    result, event = '회원 역할을 해제했습니다.', 'role_remove'
                else:
                    await member.add_roles(role, reason='Self-service membership')
                    result, event = '회원 역할을 지급했습니다.', 'role_add'
                self.client.store.event(event, guild.id, member.id)
                return result
        await self.perform(interaction, action)

    @discord.ui.button(label='비공개 문의 열기', style=discord.ButtonStyle.primary,
                       custom_id='operations:ticket:v1')
    async def ticket(self, interaction, button):
        async def action():
            channel, created = await self.client.tickets.open(interaction.guild_id, interaction.user.id)
            # setup/close failure must not cause a second channel on retry.
            if created:
                await channel.send('문의 내용을 남겨 주세요. 운영진이 확인합니다.',
                                   view=ClosePanel(self.client))
            return f'문의 채널: {channel.mention}'
        await self.perform(interaction, action)


class ClosePanel(OperationView):
    @discord.ui.button(label='문의 종료 (운영진)', style=discord.ButtonStyle.danger,
                       custom_id='operations:close:v1')
    async def close_ticket(self, interaction, button):
        async def action():
            staff = any(r.id == self.client.cfg.staff_role_id for r in interaction.user.roles)
            await self.client.tickets.close(interaction.guild_id, interaction.user.id,
                                            interaction.channel_id, staff)
            return '문의를 종료했습니다. 기록은 운영진이 볼 수 있도록 채널에 보관합니다.'
        await self.perform(interaction, action)


class OperationsClient(discord.Client):
    def __init__(self, cfg):
        intents = discord.Intents.none()
        intents.guilds = True
        super().__init__(intents=intents, allowed_mentions=discord.AllowedMentions.none())
        self.cfg = cfg
        self.store = Store(cfg.database_path)
        self.role_lock = asyncio.Lock()
        self.tickets = TicketService(self.store, Gateway(self))
        self.tree = app_commands.CommandTree(self)
        guild = discord.Object(id=cfg.guild_id)
        self.tree.add_command(app_commands.Command(name='setup',
            description='현재 채널에 역할·문의 패널을 설치합니다.', callback=self.setup_panel), guild=guild)
        self.tree.add_command(app_commands.Command(name='audit',
            description='최근 운영 처리 기록 10개를 확인합니다.', callback=self.audit), guild=guild)
        self.tree.add_command(app_commands.Command(name='close',
            description='현재 문의 티켓을 종료합니다. 운영진 전용.', callback=self.close_ticket), guild=guild)

    async def setup_hook(self):
        self.add_view(Panel(self))
        self.add_view(ClosePanel(self))
        await self.tree.sync(guild=discord.Object(id=self.cfg.guild_id))

    async def close(self):
        try:
            await super().close()
        finally:
            self.store.close()

    @app_commands.default_permissions(manage_guild=True)
    @app_commands.guild_only()
    async def setup_panel(self, interaction: discord.Interaction):
        if interaction.guild_id != self.cfg.guild_id or not interaction.permissions.manage_guild:
            await interaction.response.send_message('서버 관리 권한이 필요합니다.', ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True, thinking=True)
        try:
            Gateway(self).resources(interaction.guild_id)
            validate_member_role(interaction.guild.get_role(self.cfg.member_role_id),
                                 self.cfg.staff_role_id, interaction.guild.me)
            await interaction.channel.send(embed=discord.Embed(title='서버 안내 / Support',
                description='회원 역할을 선택하거나 비공개 문의를 열어 주세요.',
                color=0x5865F2), view=Panel(self))
            text = '이 채널에 안내 패널을 설치했습니다.'
        except (UserError, discord.HTTPException) as error:
            text = str(error) if isinstance(error, UserError) else '채널 권한을 확인해 주세요.'
        await interaction.followup.send(text, ephemeral=True)

    @app_commands.default_permissions(manage_guild=True)
    @app_commands.guild_only()
    async def audit(self, interaction: discord.Interaction):
        if interaction.guild_id != self.cfg.guild_id or not interaction.permissions.manage_guild:
            await interaction.response.send_message('서버 관리 권한이 필요합니다.', ephemeral=True)
            return
        rows = self.store.recent(interaction.guild_id)
        text = '\n'.join(f"{r['created_at']} | {r['action']} | user:{r['actor_id']} | channel:{r['channel_id']}"
                         for r in rows) or '아직 기록이 없습니다.'
        await interaction.response.send_message(f'```\n{text}\n```', ephemeral=True)

    @app_commands.guild_only()
    async def close_ticket(self, interaction: discord.Interaction):
        view = ClosePanel(self)
        if await view.interaction_check(interaction):
            await view.close_ticket.callback(interaction)
