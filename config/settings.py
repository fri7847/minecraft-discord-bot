import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    # Discord
    DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
    DISCORD_PREFIX = "!"

    # 공개 접속용 도메인 (server.fri4666.com:<port>)
    PUBLIC_HOST = os.getenv("PUBLIC_HOST", "server.fri4666.com")

    # Docker
    DOCKER_NETWORK = "minecraft-network"
    MINECRAFT_IMAGE = "itzg/minecraft-server:latest"
    # SPIGOT/BuildTools 또는 1.20.x 이하 버전은 java21 이미지가 필요 (latest는 Java 25)
    MINECRAFT_IMAGE_JAVA21 = "itzg/minecraft-server:java21"

    # 지원하는 모드 로더 (itzg/minecraft-server TYPE 값)
    SUPPORTED_MOD_LOADERS = {"VANILLA", "FORGE", "FABRIC", "PAPER", "SPIGOT", "QUILT", "NEOFORGE"}

    # 항상 java21 이미지로 강제하는 로더 (BuildTools 가 신 Java 거부)
    JAVA21_REQUIRED_LOADERS = {"SPIGOT", "BUKKIT", "CRAFTBUKKIT"}

    # 기본 버전 — itzg는 LATEST/lastest 모두 LATEST로 받지만 표준은 LATEST
    DEFAULT_VERSION = "LATEST"

    # 로더별 안티 X-ray 자동 설치 매핑 (Modrinth 프로젝트 slug)
    # 콤마로 구분하면 의존 모드도 함께 다운로드됨
    ANTI_XRAY_PROJECTS = {
        "PAPER":      "orebfuscator",
        "SPIGOT":     "orebfuscator",
        "BUKKIT":     "orebfuscator",
        "CRAFTBUKKIT":"orebfuscator",
        "FORGE":      "anti-xray",
        "NEOFORGE":   "anti-xray",
        "FABRIC":     "anti-xray,fabric-api",   # AntiXray 가 Fabric API 필요
        "QUILT":      "anti-xray",              # Quilt 는 voicechat의 jar-in-jar QSL 사용 — fabric-api 추가하면 mixin 충돌
        # VANILLA 는 모드/플러그인을 못 받으므로 자동 설치 불가
    }

    # SpigotMC 리소스 ID (Modrinth에 없는 의존성). itzg SPIGET_RESOURCES 환경변수로 처리
    # Bukkit/Spigot/Paper의 Orebfuscator 는 ProtocolLib(1997) 필요
    ANTI_XRAY_SPIGET_DEPS = {
        "PAPER":      "1997",
        "SPIGOT":     "1997",
        "BUKKIT":     "1997",
        "CRAFTBUKKIT":"1997",
    }

    # 모든 서버에 항상 설치할 Modrinth 프로젝트 (VANILLA 는 자동 제외)
    # itzg가 컨테이너 TYPE에 맞는 mod/plugin 변형을 자동 선택
    ALWAYS_INSTALL_MODRINTH = [
        "simple-voice-chat",   # Henkelmax 공식 음성채팅 (mod + plugin 모두 같은 slug)
        "spark",               # 성능 프로파일러 — /tps 명령에 사용 (모든 로더 지원)
    ]

    # RCON — /sayall, /tps 등 봇이 게임 안에 명령 보낼 때 사용
    # 컨테이너마다 달라지지 않게 단일 비밀번호 (봇과 마인크래프트 컨테이너만 같은 docker network라 외부 노출 X)
    RCON_PASSWORD = os.getenv("RCON_PASSWORD", "mc-bot-rcon-pw")
    RCON_PORT = 25575

    # Volume paths
    VOLUME_BASE_PATH = os.path.expanduser("~/docker/minecraft")

    # Port allocation
    PORT_START = 25565
    PORT_END = 25999

    # Resource limits
    MAX_CONTAINERS_PER_GUILD = 10
    MAX_CONTAINERS_PER_USER = 3
    MAX_RAM_MB = 4096
    MAX_CPU = 2.0

    # Security
    SERVER_NAME_PATTERN = r'^[a-zA-Z0-9_-]{1,32}$'
    ADMIN_ROLE = os.getenv("ADMIN_ROLE", "Minecraft Admin")
