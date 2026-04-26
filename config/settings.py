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

    # 기본 버전 — 운영 정책상 26.1.2 고정 (사용자 결정).
    # LATEST 로 두면 itzg 가 신 버전(26.1.2+) 으로 풀어 자동 설치 플러그인 호환이 깨질 수 있어
    # 명시 버전 으로 둔다. 사용자가 /create version 옵션에 명시하면 그 값이 우선.
    DEFAULT_VERSION = "26.1.2"

    # 로더별로 26.1.2 가 호환 안 되는 경우 자동 폴백 (사용자가 version 명시 시엔 그 값이 우선).
    # - FORGE: Forge 가 mc 26.1.x 빌드를 안 함 (NeoForge 로 갈라진 후 정체). anti-xray forge 빌드도 1.20.4 가 마지막.
    # - QUILT: simple-voice-chat 의 quilt 빌드가 1.21.1 까지만 (이후 fabric jar 만 만듬, jar-in-jar QSL 충돌 회피).
    # - NEOFORGE: NeoForge 의 26.1.x 빌드는 모두 -beta 표시라 itzg install-neoforge 가 stable 못 찾음.
    LOADER_VERSION_OVERRIDE = {
        "FORGE":    "1.20.4",
        "QUILT":    "1.21.1",
        "NEOFORGE": "1.21.1",
    }

    # 로더별 안티 X-ray 자동 설치 매핑 (Modrinth 프로젝트 slug)
    # 콤마로 구분하면 의존 모드도 함께 다운로드됨
    # PAPER: Paper 내장 anti-xray (engine-mode 2) 가 진짜 obfuscation 을 담당 →
    #        Modrinth 플러그인은 detection 역할인 minertrack 만 설치 (자동 ban 까지).
    #        NeoAntiXray 는 사실 detection-only 라 obfuscation 효과 0 — 빼버림.
    # SPIGOT/BUKKIT 계열: 26.1.x 호환 obfuscation 플러그인이 Modrinth 에 사실상 없어
    #        neoantixray (detection-only) 라도 깔아 의심 패턴 알림이라도 받게 둘.
    #        진짜 X-ray 차단을 원하면 Paper 로 갈아타는 게 답.
    ANTI_XRAY_PROJECTS = {
        "PAPER":      "minertrack",
        "SPIGOT":     "neoantixray",
        "BUKKIT":     "neoantixray",
        "CRAFTBUKKIT":"neoantixray",
        "FORGE":      "anti-xray",
        "NEOFORGE":   "anti-xray",
        "FABRIC":     "anti-xray,fabric-api",   # AntiXray 가 Fabric API 필요
        "QUILT":      "anti-xray",              # Quilt 는 voicechat의 jar-in-jar QSL 사용 — fabric-api 추가하면 mixin 충돌
        # VANILLA 는 모드/플러그인을 못 받으므로 자동 설치 불가
    }

    # MinerTrack 자동 밴 설정 — PAPER 전용. 컨테이너 첫 부팅 전 미리 써둘.
    # 기본 config 에 xray.commands.7 = ban %player% 를 추가해서 VL 7 도달 시 영구 ban.
    # 기본값은 VL 5 = kick 까지만 있으므로 ban 은 추가 정책.
    MINERTRACK_CONFIG_PATH = "plugins/MinerTrack/config.yml"

    # Paper 내장 anti-xray obfuscation 활성화 — paper-world-defaults.yml 의
    # anti-xray 섹션을 enabled=true, engine-mode=2 로 패치해서 미리 박음.
    # itzg 가 부팅 시 같은 파일을 GitHub(Shonz1) 에서 다시 받아 덮어쓰므로
    # SKIP_DOWNLOAD_DEFAULTS=TRUE 도 함께 켜서 막아야 우리 파일이 살아남는다.
    PAPER_WORLD_DEFAULTS_PATH = "config/paper-world-defaults.yml"
    PAPER_WORLD_DEFAULTS_URL = (
        "https://raw.githubusercontent.com/Shonz1/minecraft-default-configs/"
        "main/{version}/paper-world-defaults.yml"
    )

    # SpigotMC 리소스 ID (Modrinth 에 없는 의존성). itzg SPIGET_RESOURCES 환경변수로 처리.
    # NeoAntiXray 로 바꿄 후엔 ProtocolLib 같은 anti-xray 의존성이 없어 비어 있음.
    # (Bukkit 계열 spark 자동 설치는 ALWAYS_INSTALL_SPIGET_BY_LOADER 가 처리)
    ANTI_XRAY_SPIGET_DEPS = {}

    # 모든 비-VANILLA 서버에 자동 설치할 Modrinth 프로젝트.
    # 여기 들어가는 slug 는 simple-voice-chat 처럼 모든 로더(fabric/paper/bukkit/...) 빌드를 가진 것만.
    ALWAYS_INSTALL_MODRINTH = [
        "simple-voice-chat",   # Henkelmax 공식 음성채팅 — mod + plugin 모두 같은 slug
    ]

    # 모드 로더 jar 만 Modrinth 에 있는 프로젝트 (Bukkit 계열은 SpigetMC 로 따로 받아야 함).
    # 예: spark 의 paper/spigot/bukkit jar 는 Modrinth 에 없고 SpigetMC 57242 에 있음.
    # QUILT: spark 의 quilt 빌드는 1.19.2 가 마지막이라 자동 설치에서 제외.
    ALWAYS_INSTALL_MODRINTH_BY_LOADER = {
        "FABRIC":   ["spark"],
        "FORGE":    ["spark"],
        "NEOFORGE": ["spark"],
    }

    # Bukkit 계열 자동 설치 SpigetMC 리소스 (anti-xray 의존성과 별개로 추가).
    # PAPER 는 1.21+ 부터 spark profiler 를 서버 jar 에 번들하므로 (FileProviderSource 가
    # "will not be loaded" 처리) 외부 다운로드 불필요. SPIGOT/BUKKIT/CRAFTBUKKIT 만 필요.
    ALWAYS_INSTALL_SPIGET_BY_LOADER = {
        "SPIGOT":     ["57242"],   # spark
        "BUKKIT":     ["57242"],
        "CRAFTBUKKIT":["57242"],
    }

    # RCON — /sayall, /tps 등 봇이 게임 안에 명령 보낼 때 사용
    # 컨테이너마다 달라지지 않게 단일 비밀번호 (봇과 마인크래프트 컨테이너만 같은 docker network라 외부 노출 X)
    RCON_PASSWORD = os.getenv("RCON_PASSWORD", "mc-bot-rcon-pw")
    RCON_PORT = 25575

    # Volume paths
    VOLUME_BASE_PATH = os.path.expanduser("~/docker/minecraft")

    # Port allocation
    # 호스트 측에서 다른 프로세스가 25565~ 점유한 경우 start_server 의 자동 재시도가
    # 다음 사용 가능 포트로 컨테이너를 재생성한다.
    PORT_START = 25565
    PORT_END = 25999

    # simple-voice-chat UDP 포트 = MC 본 포트(TCP)와 동일 번호로 통합.
    # MC 는 TCP 25565, voicechat 은 UDP 25565 — 프로토콜이 달라 OS 충돌 없음.
    # ENABLE_QUERY=FALSE 와 짝으로 동작 (query 가 켜지면 25565/UDP 를 마크가 잡아 충돌).
    # 사용자가 외부 방화벽·포트포워딩에서 한 포트만 열어도 마크와 마이크 모두 통과.
    # 이전엔 24454+offset 별도 포트였는데 운영상 외부 포트 추가 개방 누락이 잦아 통합.
    VOICE_PORT_BASE = 25565

    # 로더별 simple-voice-chat config 파일 상대 경로 (컨테이너 안 /data/ 기준).
    # 봇이 컨테이너 만들기 전에 미리 host 측에 voicechat-server.properties 를 써넣어
    # voicechat 가 voice_port 로 listen 하게 강제한다.
    VOICECHAT_CONFIG_PATH = {
        "PAPER":      "plugins/voicechat/voicechat-server.properties",
        "SPIGOT":     "plugins/voicechat/voicechat-server.properties",
        "BUKKIT":     "plugins/voicechat/voicechat-server.properties",
        "CRAFTBUKKIT":"plugins/voicechat/voicechat-server.properties",
        "FABRIC":     "config/voicechat/voicechat-server.properties",
        "FORGE":      "config/voicechat/voicechat-server.properties",
        "NEOFORGE":   "config/voicechat/voicechat-server.properties",
        "QUILT":      "config/voicechat/voicechat-server.properties",
        # VANILLA 는 voicechat 설치 자체가 안 되므로 매핑 없음.
    }

    # Resource limits
    MAX_CONTAINERS_PER_GUILD = 10
    MAX_CONTAINERS_PER_USER = 3
    MAX_RAM_MB = 4096
    MAX_CPU = 2.0

    # Security
    SERVER_NAME_PATTERN = r'^[a-zA-Z0-9_-]{1,32}$'
    ADMIN_ROLE = os.getenv("ADMIN_ROLE", "Minecraft Admin")
