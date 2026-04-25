import discord
from discord.ext import commands
from config.settings import Settings
from bot.cogs.server_management import ServerManagement

# Configure bot intents
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True

# 슬래시 명령으로 전환했지만, 라이브러리 요구로 prefix는 형식상 유지합니다.
bot = commands.Bot(
    command_prefix=Settings.DISCORD_PREFIX,
    intents=intents,
    help_command=None,
)


@bot.event
async def on_ready():
    """봇이 준비됐을 때 호출됩니다."""
    print(f"로그인 완료: {bot.user.name} ({bot.user.id})")
    print(f"{len(bot.guilds)}개의 길드에 연결되었습니다")

    try:
        synced = await bot.tree.sync()
        print(f"{len(synced)}개의 슬래시 명령을 동기화했습니다.")
    except Exception as e:
        print(f"슬래시 명령 동기화 실패: {e}")


@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error):
    """앱 커맨드 글로벌 에러 핸들러."""
    msg = f"❌ 오류가 발생했습니다: {error}"
    if interaction.response.is_done():
        await interaction.followup.send(msg, ephemeral=True)
    else:
        await interaction.response.send_message(msg, ephemeral=True)


async def main():
    """Main entry point."""
    await bot.add_cog(ServerManagement(bot))
    await bot.start(Settings.DISCORD_TOKEN)


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
