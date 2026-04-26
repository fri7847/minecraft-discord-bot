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

DIFFICULTY_CHOICES = [
    app_commands.Choice(name="평화", value="peaceful"),
    app_commands.Choice(name="쉬움", value="easy"),
    app_commands.Choice(name="보통", value="normal"),
    app_commands.Choice(name="어려움", value="hard"),
]

GAMEMODE_CHOICES = [
    app_commands.Choice(name="서바이벌", value="survival"),
    app_commands.Choice(name="크리에이티브", value="creative"),
    app_commands.Choice(name="어드벤처", value="adventure"),
    app_commands.Choice(name="스펙테이터", value="spectator"),
]

# itzg LEVEL_TYPE — MC 1.19+ 는 namespaced ID. 자주 쓰는 4종만 노출.
LEVEL_TYPE_CHOICES = [
    app_commands.Choice(name="일반 (normal)", value="minecraft:normal"),
    app_commands.Choice(name="평지 (flat)", value="minecraft:flat"),
    app_commands.Choice(name="큰 바이옷 (large biomes)", value="minecraft:large_biomes"),
    app_commands.Choice(name="증폭 (amplified)", value="minecraft:amplified"),
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
        version=f"마인크래프트 버전 (생략 시 {Settings.DEFAULT_VERSION}, 예: 1.21.4 / LATEST)",
        difficulty="난이도",
        gamemode="기본 게임 모드",
        max_players="최대 동시 접속 인원 (1~100)",
        motd="서버 목록에 표시될 한 줄 설명 (MOTD)",
        pvp="PvP 허용 여부",
        level_type="월드 생성 타입 (평지/일반 등)",
        seed="월드 시드 (생략 시 매번 새 랜덤 시드)",
        hardcore="하드코어 모드 (사망 시 스펙테이터)",
        allow_nether="네더 차원 허용 여부",
        view_distance="청크 시야 거리 (3~32)",
        spawn_protection="스폰 보호 반경 블록 (0~256, 0=비활성)",
        online_mode="정품 인증 (false=오프라인 서버)",
        ram_gb=f"메모리 할당 GB (1~{Settings.MAX_RAM_MB // 1024}, 생략 시 자동)",
        whitelist="화이트리스트 활성화",
    )
    @app_commands.choices(
        mod_loader=MOD_LOADER_CHOICES,
        difficulty=DIFFICULTY_CHOICES,
        gamemode=GAMEMODE_CHOICES,
        level_type=LEVEL_TYPE_CHOICES,
    )
    @app_commands.default_permissions(manage_guild=True)
    async def create_server(
        self,
        interaction: discord.Interaction,
        name: str,
        mod_loader: app_commands.Choice[str] | None = None,
        version: str | None = None,
        difficulty: app_commands.Choice[str] | None = None,
        gamemode: app_commands.Choice[str] | None = None,
        max_players: app_commands.Range[int, 1, 100] | None = None,
        motd: str | None = None,
        pvp: bool | None = None,
        level_type: app_commands.Choice[str] | None = None,
        seed: str | None = None,
        hardcore: bool | None = None,
        allow_nether: bool | None = None,
        view_distance: app_commands.Range[int, 3, 32] | None = None,
        spawn_protection: app_commands.Range[int, 0, 256] | None = None,
        online_mode: bool | None = None,
        ram_gb: app_commands.Range[int, 1, Settings.MAX_RAM_MB // 1024] | None = None,
        whitelist: bool | None = None,
    ):
        await interaction.response.defer(thinking=True)

        loader_value = mod_loader.value if mod_loader else "PAPER"
        loader_label = mod_loader.name if mod_loader else "Paper"
        # 사용자가 version 명시 안 했으면 로더별 폴백 → DEFAULT_VERSION 순서로 적용.
        # FORGE/QUILT 는 26.1.x 호환 안 돼서 LOADER_VERSION_OVERRIDE 가 더 옥 안정 버전을 줌.
        version_overridden = False
        if version:
            version_value = version
        elif loader_value in Settings.LOADER_VERSION_OVERRIDE:
            version_value = Settings.LOADER_VERSION_OVERRIDE[loader_value]
            version_overridden = True
        else:
            version_value = Settings.DEFAULT_VERSION

        progress = await interaction.followup.send(
            f"🟡 '{name}' 서버 생성 중... (이미지 풀/컨테이너 준비)",
            wait=True,
        )

        try:
            # 안티 X-ray 는 모든 서버에 필수로 자동 설치 (Vanilla 는 모드 시스템이 없어 자동 제외됨)
            success, error, result = await self.server_service.create_server(
                name,
                interaction.guild_id or 0,
                interaction.user.id,
                mod_loader=loader_value,
                version=version_value,
                enable_anti_xray=True,
                difficulty=difficulty.value if difficulty else None,
                gamemode=gamemode.value if gamemode else None,
                max_players=max_players,
                motd=motd,
                pvp=pvp,
                level_type=level_type.value if level_type else None,
                seed=seed,
                hardcore=hardcore,
                allow_nether=allow_nether,
                view_distance=view_distance,
                spawn_protection=spawn_protection,
                online_mode=online_mode,
                ram_gb=ram_gb,
                whitelist=whitelist,
            )

            if not success:
                await progress.edit(content=format_error(error))
                return

            address = format_address(result["port"])

            notes = []
            if version_overridden:
                notes.append(
                    f"• ⚠️ {loader_label} 는 mc {Settings.DEFAULT_VERSION} 호환 자동설치 모드가 없어 "
                    f"**{version_value}** 로 자동 조정했습니다 (다른 버전을 원하면 `version:` 명시)"
                )
            if result.get("image", "").endswith(":java21"):
                notes.append("• Java 21 이미지를 자동 선택했습니다 (Spigot/구버전 호환)")
            installed = result.get("anti_xray")
            if installed:
                notes.append(f"• 안티 X-ray 자동 설치: **Modrinth `{installed}`** + 마이크 모드(simple-voice-chat) (첫 부팅 시 다운로드)")
            elif loader_value == "VANILLA":
                notes.append("• ⚠️ 바닐라는 모드/플러그인 시스템이 없어 안티 X-ray·마이크 모드가 동작하지 않습니다")
            notes_block = ("\n" + "\n".join(notes)) if notes else ""

            await progress.edit(content=format_success(
                f"'{name}' 서버가 생성되었습니다!\n"
                f"• 모드 로더: **{loader_label}**\n"
                f"• 버전: **{result.get('version', version_value)}**\n"
                f"• 접속 주소: `{address}`\n"
                f"• 상태: 정지됨"
                f"{notes_block}\n"
                f"`/start name:{name}` 으로 서버를 시작하세요."
            ))
        except Exception as e:
            await progress.edit(content=format_error(f"서버 생성 중 예상치 못한 오류: {e}"))

    # ------------------------------------------------------------------ #
    # /start — 컨테이너 start 직후가 아니라 실제 RCON 응답까지 기다린 뒤 알림
    # ------------------------------------------------------------------ #
    @app_commands.command(name="start", description="마인크래프트 서버를 시작합니다")
    @app_commands.describe(name="시작할 서버 이름")
    @app_commands.default_permissions(manage_guild=True)
    async def start_server(self, interaction: discord.Interaction, name: str):
        await interaction.response.defer(thinking=True)

        progress = await interaction.followup.send(
            f"🟡 '{name}' 서버 시작 중...",
            wait=True,
        )

        try:
            success, error = await self.server_service.start_server(name)
            if not success:
                await progress.edit(content=format_error(error))
                return

            status = await self.server_service.get_server_status(name)
            address = format_address(status.get("port") if status else None)

            await progress.edit(content=(
                f"🟡 '{name}' 서버 부팅 중... (월드/플러그인 로드 대기, 최대 5분)\n"
                f"• 접속 주소: `{address}`"
            ))

            ready = await self.rcon_service.wait_until_ready(name, max_s=300.0)

            if ready:
                await progress.edit(content=format_success(
                    f"'{name}' 서버 준비 완료! 이제 접속하실 수 있습니다.\n"
                    f"• 접속 주소: `{address}`"
                ))
            else:
                await progress.edit(content=format_error(
                    f"'{name}' 컨테이너는 시작됐지만 5분 안에 RCON 응답이 없습니다.\n"
                    f"• 접속 주소: `{address}` (직접 접속해 보거나 `/status name:{name}` 로 확인)"
                ))
        except Exception as e:
            await progress.edit(content=format_error(f"서버 시작 중 예상치 못한 오류: {e}"))

    # ------------------------------------------------------------------ #
    # /stop — graceful 종료(월드 저장)까지 기다린 뒤 알림
    # ------------------------------------------------------------------ #
    @app_commands.command(name="stop", description="마인크래프트 서버를 정지합니다")
    @app_commands.describe(name="정지할 서버 이름")
    @app_commands.default_permissions(manage_guild=True)
    async def stop_server(self, interaction: discord.Interaction, name: str):
        await interaction.response.defer(thinking=True)

        # graceful shutdown 중에는 월드 저장으로 수 초~30초 정도 블로킹됨.
        # 작업 시작과 동시에 진행 메시지를 보내고, 끝나면 갱신.
        progress = await interaction.followup.send(
            f"🟡 '{name}' 서버 정지 중... (월드 저장 대기, 최대 30초)",
            wait=True,
        )

        try:
            success, error = await self.server_service.stop_server(name)
            if not success:
                await progress.edit(content=format_error(error))
                return

            # docker stop 이 반환되면 컨테이너는 실제로 정지된 상태. 한 번 더 확인.
            status = await self.server_service.get_server_status(name)
            if status and status["status"] == "exited":
                await progress.edit(content=format_success(f"'{name}' 서버가 완전히 정지되었습니다."))
            else:
                await progress.edit(content=format_error(
                    f"'{name}' 정지 명령은 보냈지만 상태가 'exited' 가 아닙니다 (현재: {status['status'] if status else '없음'})"
                ))
        except Exception as e:
            await progress.edit(content=format_error(f"서버 정지 중 예상치 못한 오류: {e}"))

    # ------------------------------------------------------------------ #
    # /delete
    # ------------------------------------------------------------------ #
    @app_commands.command(name="delete", description="마인크래프트 서버를 삭제합니다")
    @app_commands.describe(name="삭제할 서버 이름")
    @app_commands.default_permissions(manage_guild=True)
    async def delete_server(self, interaction: discord.Interaction, name: str):
        await interaction.response.defer(thinking=True)

        progress = await interaction.followup.send(
            f"🟡 '{name}' 서버 삭제 중... (컨테이너 + 월드 데이터까지 영구 삭제)",
            wait=True,
        )

        try:
            success, error = await self.server_service.delete_server(name)
            if success:
                await progress.edit(content=format_success(
                    f"'{name}' 서버와 월드 데이터를 영구 삭제했습니다."
                ))
            else:
                await progress.edit(content=format_error(error))
        except Exception as e:
            await progress.edit(content=format_error(f"서버 삭제 중 예상치 못한 오류: {e}"))

    # ------------------------------------------------------------------ #
    # /list
    # ------------------------------------------------------------------ #
    @app_commands.command(name="list", description="모든 마인크래프트 서버 목록을 보여줍니다")
    async def list_servers(self, interaction: discord.Interaction):
        await interaction.response.defer(thinking=True)

        try:
            servers = await self.server_service.list_servers()
            await interaction.followup.send(format_list(servers))
        except Exception as e:
            await interaction.followup.send(format_error(f"서버 목록 조회 중 오류: {e}"))

    # ------------------------------------------------------------------ #
    # /status
    # ------------------------------------------------------------------ #
    @app_commands.command(name="status", description="특정 서버의 상태를 확인합니다")
    @app_commands.describe(name="상태를 확인할 서버 이름")
    async def server_status(self, interaction: discord.Interaction, name: str):
        await interaction.response.defer(thinking=True)

        try:
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
        except Exception as e:
            await interaction.followup.send(format_error(f"상태 조회 중 오류: {e}"))

    # ------------------------------------------------------------------ #
    # /mods
    # ------------------------------------------------------------------ #
    mods_group = app_commands.Group(name="mods", description="모드 파일을 관리합니다")

    @mods_group.command(name="list", description="설치된 모드 파일 목록을 봅니다")
    @app_commands.describe(name="서버 이름")
    async def mods_list(self, interaction: discord.Interaction, name: str):
        await interaction.response.defer(thinking=True)

        try:
            ok, error, mods = await self.server_service.list_mods(name)
            if not ok:
                await interaction.followup.send(format_error(error))
                return

            if not mods:
                await interaction.followup.send(f"📦 '{name}' 서버에 설치된 모드가 없습니다.")
                return

            body = "\n".join(f"• `{m}`" for m in mods)
            await interaction.followup.send(f"📦 **'{name}' 서버 모드 ({len(mods)}개)**\n{body}")
        except Exception as e:
            await interaction.followup.send(format_error(f"모드 목록 조회 중 오류: {e}"))

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

        progress = await interaction.followup.send(
            f"🟡 '{file.filename}' 업로드 중...",
            wait=True,
        )

        try:
            # 25MB 상한
            if file.size > 25 * 1024 * 1024:
                await progress.edit(content=format_error("모드 파일이 25MB를 초과합니다"))
                return

            try:
                content = await file.read()
            except Exception as e:
                await progress.edit(content=format_error(f"파일 다운로드 실패: {e}"))
                return

            ok, error = await self.server_service.add_mod(name, file.filename, content)
            if ok:
                await progress.edit(content=format_success(
                    f"'{file.filename}' 모드를 '{name}' 서버에 추가했습니다.\n"
                    f"변경사항을 적용하려면 `/stop name:{name}` 후 `/start name:{name}` 으로 재시작하세요."
                ))
            else:
                await progress.edit(content=format_error(error))
        except Exception as e:
            await progress.edit(content=format_error(f"모드 업로드 중 예상치 못한 오류: {e}"))

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

        try:
            ok, error = await self.server_service.remove_mod(name, filename)
            if ok:
                await interaction.followup.send(format_success(
                    f"'{filename}' 모드를 삭제했습니다. 재시작 후 적용됩니다."
                ))
            else:
                await interaction.followup.send(format_error(error))
        except Exception as e:
            await interaction.followup.send(format_error(f"모드 삭제 중 예상치 못한 오류: {e}"))

    # ------------------------------------------------------------------ #
    # /sayall — 게임 안 모든 플레이어에게 공지
    # ------------------------------------------------------------------ #
    @app_commands.command(name="sayall", description="서버 안 모든 플레이어에게 채팅 공지를 보냅니다")
    @app_commands.describe(name="서버 이름", message="공지 메시지")
    @app_commands.default_permissions(manage_guild=True)
    async def sayall(self, interaction: discord.Interaction, name: str, message: str):
        await interaction.response.defer(thinking=True)

        try:
            ok, error = await self.rcon_service.say(name, message)
            if ok:
                await interaction.followup.send(format_success(f"'{name}' 서버에 공지를 보냈습니다: {message}"))
            else:
                await interaction.followup.send(format_error(error))
        except Exception as e:
            await interaction.followup.send(format_error(f"공지 전송 중 예상치 못한 오류: {e}"))

    # ------------------------------------------------------------------ #
    # /tps — 서버 성능(TPS) 조회
    # ------------------------------------------------------------------ #
    @app_commands.command(name="tps", description="서버의 TPS(성능) 를 확인합니다")
    @app_commands.describe(name="서버 이름")
    async def tps(self, interaction: discord.Interaction, name: str):
        await interaction.response.defer(thinking=True)

        try:
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
                emoji, label = "🔴", "버벵임 심각"

            tps_line = f"{tps_value:.2f} / 20.0" if tps_value is not None else "—"
            raw = info.get("raw", "")[:500]
            await interaction.followup.send(
                f"{emoji} **{name}** 서버 성능 — {label}\n"
                f"• TPS: **{tps_line}**\n"
                f"• 로더: {info.get('loader')}\n"
                f"• 사용 명령: `{info.get('command')}`\n"
                f"```\n{raw}\n```"
            )
        except Exception as e:
            await interaction.followup.send(format_error(f"TPS 조회 중 예상치 못한 오류: {e}"))

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
                "`/create name:<이름> [옵션...]` — 새 서버 생성\n"
                "  · 필수: `name`\n"
                "  · 기본 옵션: `mod_loader` (생략=Paper), `version` (생략="
                f"{Settings.DEFAULT_VERSION})\n"
                "  · 게임플레이: `difficulty`, `gamemode`, `pvp`, `hardcore`, `allow_nether`, `max_players`, `motd`\n"
                "  · 월드: `level_type` (일반/평지/큰바이옷/증폭), `seed` (생략 시 매번 새 랜덤 맵)\n"
                "  · 성능/네트워크: `view_distance` (3~32), `spawn_protection`, `ram_gb` (1~4), `online_mode`, `whitelist`\n"
                "  · 자동 설치: 안티 X-ray + 마이크 모드(simple-voice-chat). PAPER 는 X-ray 자동 ban (MinerTrack)\n"
                "    └ Vanilla 만 모드 시스템이 없어 자동 설치 불가\n"
                "`/start name:<이름>` — 서버 시작\n"
                "`/stop name:<이름>` — 서버 정지\n"
                "`/delete name:<이름>` — 서버 삭제 (월드 데이터까지 영구 삭제)\n"
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
