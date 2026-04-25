import discord
from discord import app_commands
from discord.ext import commands

from services.server_service import ServerService
from services.rcon_service import RconService
from bot.utils.formatters import (
    format_success,
    format_error,
    format_list,
    format_status_label,
    format_address,
)
from config.settings import Settings


MOD_LOADER_CHOICES = [
    app_commands.Choice(name="바닐라 (Vanilla)", value="VANILLA"),
    app_commands.Choice(name="Forge", value="FORGE"),
    app_commands.Choice(name="NeoForge", value="NEOFORGE"),
    app_commands.Choice(name="Fabric", value="FABRIC"),
    app_commands.Choice(name="Quilt", value="QUILT"),
    app_commands.Choice(name="Paper", value="PAPER"),
    app_commands.Choice(name="Spigot", value="SPIGOT"),
]


class ServerManagement(commands.Cog):
    """마인크래프트 서버 관리를 위한 디스코드 슬래시 명령."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.server_service = ServerService()
        self.rcon_service = RconService()

    # ------------------------------------------------------------------ #
    # /create
    # ------------------------------------------------------------------ #
    @app_commands.command(name="create", description="새 마인크래프트 서버를 생성합니다")
    @app_commands.describe(
        name="서버 이름 (영문/숫자/_/-, 최대 32자)",
        mod_loader="모드 로더 종류 (생략 시 Paper)",
        version="마인크래프트 버전 (생략 시 자동 LATEST, 예: 1.20.1)",
    )
    @app_commands.choices(mod_loader=MOD_LOADER_CHOICES)
    @app_commands.default_permissions(manage_guild=True)
    async def create_server(
        self,
        interaction: discord.Interaction,
        name: str,
        mod_loader: app_commands.Choice[str] | None = None,
        version: str | None = None,
    ):
        await interaction.response.defer(thinking=True)

        loader_value = mod_loader.value if mod_loader else "PAPER"
        loader_label = mod_loader.name if mod_loader else "Paper"
        version_value = version or Settings.DEFAULT_VERSION

        # 안티 X-ray 는 모든 서버에 필수로 자동 설치 (Vanilla 는 모드 시스템이 없어 자동 제외됨)
        success, error, result = await self.server_service.create_server(
            name,
            interaction.guild_id or 0,
            interaction.user.id,
            mod_loader=loader_value,
            version=version_value,
            enable_anti_xray=True,
        )

        if not success:
            await interaction.followup.send(format_error(error))
            return

        address = format_address(result["port"])

        notes = []
        if result.get("image", "").endswith(":java21"):
            notes.append("• Java 21 이미지를 자동 선택했습니다 (Spigot/구버전 호환)")
        installed = result.get("anti_xray")
        if installed:
            notes.append(f"• 안티 X-ray 자동 설치: **Modrinth `{installed}`** + 마이크 모드(simple-voice-chat) (첫 부팅 시 다운로드)")
        elif loader_value == "VANILLA":
            notes.append("• ⚠️ 바닐라는 모드/플러그인 시스템이 없어 안티 X-ray·마이크 모드가 동작하지 않습니다")
        notes_block = ("\n" + "\n".join(notes)) if notes else ""

        await interaction.followup.send(format_success(
            f"'{name}' 서버가 생성되었습니다!\n"
            f"• 모드 로더: **{loader_label}**\n"
            f"• 버전: **{result.get('version', version_value)}**\n"
            f"• 접속 주소: `{address}`\n"
            f"• 상태: 정지됨"
            f"{notes_block}\n"
            f"`/start name:{name}` 으로 서버를 시작하세요."
        ))

    # ------------------------------------------------------------------ #
    # /start
    # ------------------------------------------------------------------ #
    @app_commands.command(name="start", description="마인크래프트 서버를 시작합니다")
    @app_commands.describe(name="시작할 서버 이름")
    @app_commands.default_permissions(manage_guild=True)
    async def start_server(self, interaction: discord.Interaction, name: str):
        await interaction.response.defer(thinking=True)

        success, error = await self.server_service.start_server(name)
        if not success:
            await interaction.followup.send(format_error(error))
            return

        status = await self.server_service.get_server_status(name)
        address = format_address(status.get("port") if status else None)
        await interaction.followup.send(format_success(
            f"'{name}' 서버를 시작했습니다!\n• 접속 주소: `{address}`"
        ))

    # ------------------------------------------------------------------ #
    # /stop
    # ------------------------------------------------------------------ #
    @app_commands.command(name="stop", description="마인크래프트 서버를 정지합니다")
    @app_commands.describe(name="정지할 서버 이름")
    @app_commands.default_permissions(manage_guild=True)
    async def stop_server(self, interaction: discord.Interaction, name: str):
        await interaction.response.defer(thinking=True)

        success, error = await self.server_service.stop_server(name)
        if success:
            await interaction.followup.send(format_success(f"'{name}' 서버를 정지했습니다."))
        else:
            await interaction.followup.send(format_error(error))

    # ------------------------------------------------------------------ #
    # /delete
    # ------------------------------------------------------------------ #
    @app_commands.command(name="delete", description="마인크래프트 서버를 삭제합니다")
    @app_commands.describe(name="삭제할 서버 이름")
    @app_commands.default_permissions(manage_guild=True)
    async def delete_server(self, interaction: discord.Interaction, name: str):
        await interaction.response.defer(thinking=True)

        success, error = await self.server_service.delete_server(name)
        if success:
            await interaction.followup.send(format_success(f"'{name}' 서버를 삭제했습니다."))
        else:
            await interaction.followup.send(format_error(error))

    # ------------------------------------------------------------------ #
    # /list
    # ------------------------------------------------------------------ #
    @app_commands.command(name="list", description="모든 마인크래프트 서버 목록을 보여줍니다")
    async def list_servers(self, interaction: discord.Interaction):
        await interaction.response.defer(thinking=True)

        servers = await self.server_service.list_servers()
        await interaction.followup.send(format_list(servers))

    # ------------------------------------------------------------------ #
    # /status
    # ------------------------------------------------------------------ #
    @app_commands.command(name="status", description="특정 서버의 상태를 확인합니다")
    @app_commands.describe(name="상태를 확인할 서버 이름")
    async def server_status(self, interaction: discord.Interaction, name: str):
        await interaction.response.defer(thinking=True)

        status = await self.server_service.get_server_status(name)
        if not status:
            await interaction.followup.send(format_error(f"'{name}' 서버를 찾을 수 없습니다"))
            return

        emoji = "🟢" if status["status"] == "running" else "🔴"
        address = format_address(status.get("port"))
        await interaction.followup.send(
            f"{emoji} **{status['name']}**\n"
            f"• 상태: {format_status_label(status['status'])}\n"
            f"• 모드 로더: {status.get('mod_loader', 'VANILLA')}\n"
            f"• 버전: {status.get('version', 'LATEST')}\n"
            f"• 접속 주소: `{address}`"
        )

    # ------------------------------------------------------------------ #
    # /mods
    # ------------------------------------------------------------------ #
    mods_group = app_commands.Group(name="mods", description="모드 파일을 관리합니다")

    @mods_group.command(name="list", description="설치된 모드 파일 목록을 봅니다")
    @app_commands.describe(name="서버 이름")
    async def mods_list(self, interaction: discord.Interaction, name: str):
        await interaction.response.defer(thinking=True)

        ok, error, mods = await self.server_service.list_mods(name)
        if not ok:
            await interaction.followup.send(format_error(error))
            return

        if not mods:
            await interaction.followup.send(f"📦 '{name}' 서버에 설치된 모드가 없습니다.")
            return

        body = "\n".join(f"• `{m}`" for m in mods)
        await interaction.followup.send(f"📦 **'{name}' 서버 모드 ({len(mods)}개)**\n{body}")

    @mods_group.command(name="add", description="모드 .jar 파일을 업로드해서 설치합니다")
    @app_commands.describe(name="서버 이름", file="업로드할 .jar 모드 파일")
    @app_commands.default_permissions(manage_guild=True)
    async def mods_add(
        self,
        interaction: discord.Interaction,
        name: str,
        file: discord.Attachment,
    ):
        await interaction.response.defer(thinking=True)

        # 25MB 상한
        if file.size > 25 * 1024 * 1024:
            await interaction.followup.send(format_error("모드 파일이 25MB를 초과합니다"))
            return

        try:
            content = await file.read()
        except Exception as e:
            await interaction.followup.send(format_error(f"파일 다운로드 실패: {e}"))
            return

        ok, error = await self.server_service.add_mod(name, file.filename, content)
        if ok:
            await interaction.followup.send(format_success(
                f"'{file.filename}' 모드를 '{name}' 서버에 추가했습니다.\n"
                f"변경사항을 적용하려면 `/stop name:{name}` 후 `/start name:{name}` 으로 재시작하세요."
            ))
        else:
            await interaction.followup.send(format_error(error))

    @mods_group.command(name="remove", description="설치된 모드 파일을 삭제합니다")
    @app_commands.describe(name="서버 이름", filename="삭제할 모드 파일 이름 (예: jei.jar)")
    @app_commands.default_permissions(manage_guild=True)
    async def mods_remove(
        self,
        interaction: discord.Interaction,
        name: str,
        filename: str,
    ):
        await interaction.response.defer(thinking=True)

        ok, error = await self.server_service.remove_mod(name, filename)
        if ok:
            await interaction.followup.send(format_success(
                f"'{filename}' 모드를 삭제했습니다. 재시작 후 적용됩니다."
            ))
        else:
            await interaction.followup.send(format_error(error))

    # ------------------------------------------------------------------ #
    # /sayall — 게임 안 모든 플레이어에게 공지
    # ------------------------------------------------------------------ #
    @app_commands.command(name="sayall", description="서버 안 모든 플레이어에게 채팅 공지를 보냅니다")
    @app_commands.describe(name="서버 이름", message="공지 메시지")
    @app_commands.default_permissions(manage_guild=True)
    async def sayall(self, interaction: discord.Interaction, name: str, message: str):
        await interaction.response.defer(thinking=True)

        ok, error = await self.rcon_service.say(name, message)
        if ok:
            await interaction.followup.send(format_success(f"'{name}' 서버에 공지를 보냈습니다: {message}"))
        else:
            await interaction.followup.send(format_error(error))

    # ------------------------------------------------------------------ #
    # /tps — 서버 성능(TPS) 조회
    # ------------------------------------------------------------------ #
    @app_commands.command(name="tps", description="서버의 TPS(성능) 를 확인합니다")
    @app_commands.describe(name="서버 이름")
    async def tps(self, interaction: discord.Interaction, name: str):
        await interaction.response.defer(thinking=True)

        ok, error, info = await self.rcon_service.tps(name)
        if not ok:
            await interaction.followup.send(format_error(error))
            return

        tps_value = info.get("tps_1m")
        if tps_value is None:
            emoji, label = "⚪", "측정 불가"
        elif tps_value >= 19.0:
            emoji, label = "🟢", "정상"
        elif tps_value >= 15.0:
            emoji, label = "🟡", "약간 느림"
        else:
            emoji, label = "🔴", "버볫임 심각"

        tps_line = f"{tps_value:.2f} / 20.0" if tps_value is not None else "—"
        raw = info.get("raw", "")[:500]
        await interaction.followup.send(
            f"{emoji} **{name}** 서버 성능 — {label}\n"
            f"• TPS: **{tps_line}**\n"
            f"• 로더: {info.get('loader')}\n"
            f"• 사용 명령: `{info.get('command')}`\n"
            f"```\n{raw}\n```"
        )

    # ------------------------------------------------------------------ #
    # /help
    # ------------------------------------------------------------------ #
    @app_commands.command(name="help", description="사용 가능한 명령어 목록을 봅니다")
    async def help_command(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="🟩 마인크래프트 서버 봇 도움말",
            description=(
                f"기본 접속 도메인: `{Settings.PUBLIC_HOST}`\n"
                "각 서버는 `server.fri4666.com:<할당된 포트>` 로 접속합니다."
            ),
            color=discord.Color.green(),
        )

        embed.add_field(
            name="🛠️ 서버 관리",
            value=(
                "`/create name:<이름> [mod_loader] [version]` — 새 서버 생성\n"
                "  · `mod_loader` 생략 시 **Paper**\n"
                "  · `version` 생략(또는 빈 값) 시 **LATEST** 자동 선택\n"
                "  · 안티 X-ray + 마이크 모드(simple-voice-chat) 자동 설치 (필수)\n"
                "    └ Vanilla 만 모드 시스템이 없어 자동 설치 불가\n"
                "`/start name:<이름>` — 서버 시작\n"
                "`/stop name:<이름>` — 서버 정지\n"
                "`/delete name:<이름>` — 서버 삭제\n"
            ),
            inline=False,
        )

        embed.add_field(
            name="📋 정보 조회",
            value=(
                "`/list` — 모든 서버 목록 + 접속 주소\n"
                "`/status name:<이름>` — 특정 서버 상태/접속 주소\n"
                "`/tps name:<이름>` — 서버 성능(TPS) 측정\n"
            ),
            inline=False,
        )

        embed.add_field(
            name="🎙️ 게임 안 통신",
            value=(
                "`/sayall name:<이름> message:<내용>` — 모든 플레이어에게 채팅 공지\n"
            ),
            inline=False,
        )

        embed.add_field(
            name="📦 모드 관리",
            value=(
                "`/mods list name:<이름>` — 설치된 모드 보기\n"
                "`/mods add name:<이름> file:<.jar>` — 모드 업로드\n"
                "`/mods remove name:<이름> filename:<파일명>` — 모드 삭제\n"
                "※ 모드는 FORGE/FABRIC/NEOFORGE/QUILT 등 모드 로더 서버에서만 적용됩니다."
            ),
            inline=False,
        )

        embed.add_field(
            name="❓ 도움말",
            value="`/help` — 이 도움말을 다시 봅니다",
            inline=False,
        )

        embed.set_footer(text="서버 관리 명령은 '서버 관리' 권한이 있는 사용자만 사용할 수 있습니다.")

        await interaction.response.send_message(embed=embed, ephemeral=True)

    # ------------------------------------------------------------------ #
    # 공통 에러 핸들러
    # ------------------------------------------------------------------ #
    async def cog_app_command_error(
        self, interaction: discord.Interaction, error: app_commands.AppCommandError
    ):
        if isinstance(error, app_commands.MissingPermissions):
            msg = format_error("이 명령을 실행할 권한이 없습니다.")
        else:
            msg = format_error(f"오류가 발생했습니다: {error}")

        if interaction.response.is_done():
            await interaction.followup.send(msg, ephemeral=True)
        else:
            await interaction.response.send_message(msg, ephemeral=True)
