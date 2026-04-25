# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project purpose

Discord 봇이 디스코드 슬래시 명령으로 Docker 위에서 마인크래프트 서버를 라이프사이클 관리합니다 (생성/시작/정지/삭제, 모드 업로드, 게임 안 통신). 봇 자체와 마인크래프트 컨테이너 모두 `minecraft-network` (Docker bridge) 에 묶여 있고, 봇은 호스트의 Docker socket(`/var/run/docker.sock`) 을 마운트해서 다른 컨테이너를 만듭니다.

사용자 응답 메시지는 한국어로 작성 (formatters.py + cogs 안 한국어 문자열).

## Common commands

```bash
# 새 코드를 봇에 적용 (가장 자주 씀)
docker compose up -d --build

# 봇 로그 확인
docker logs -f minecraft-discord-bot

# 컴파일/문법만 빠르게 (호스트에 mcrcon/docker SDK 없어도 됨)
python3 -m py_compile config/settings.py services/*.py bot/cogs/*.py bot/main.py

# Docker SDK 와 mcrcon 을 모킹해서 모듈/슬래시 트리 검증 (테스트 프레임워크 없음)
# (services/server_service.py, services/rcon_service.py 의 _가 붙은 헬퍼는 직접 호출 가능 — 이전 검증 패턴 참고)

# 봇이 만든 root-소유 호스트 파일 정리 (sudo 없이)
docker run --rm -v $HOME/docker/minecraft:/data alpine sh -c 'rm -rf /data/<dir>'
```

테스트 프레임워크는 없습니다. 기능 검증은 itzg/minecraft-server 컨테이너를 직접 띄워 healthcheck 로 확인하는 패턴 사용 (`docker inspect <name> --format '{{.State.Health.Status}}'`).

## Architecture (big picture)

`bot/main.py` 가 진입점. 디스코드 봇이 뜰 때 `bot.tree.sync()` 로 슬래시 명령을 길드에 동기화합니다.

레이어 분리:

```
bot/cogs/server_management.py    슬래시 명령 정의 (얇은 컨트롤러)
        ↓
services/server_service.py        검증·정책 (이름/버전 검증, 메시지 한국어 변환)
services/rcon_service.py          RCON 으로 게임 안 명령 보내기 + 응답 파싱
        ↓
services/docker_service.py        Docker SDK 호출 (컨테이너 라이프사이클, 환경변수 빌드)
services/port_manager.py          25565~25999 포트 할당 (기존 컨테이너 sync)
        ↓
config/settings.py                **모든 정책의 단일 진실의 원천**
```

`Settings` 가 핵심입니다. 모드 로더 → 이미지/모드/플러그인 매핑이 전부 여기에 있습니다:
- `JAVA21_REQUIRED_LOADERS` — Spigot/Bukkit/CraftBukkit. itzg `:latest` 의 Java 25 가 BuildTools 거부하므로 무조건 `:java21` 이미지
- `ANTI_XRAY_PROJECTS` / `ANTI_XRAY_SPIGET_DEPS` — 로더별 안티 X-ray Modrinth slug + ProtocolLib(SpigetMC 1997) 같은 비-Modrinth 의존성
- `ALWAYS_INSTALL_MODRINTH` — 모든 서버에 자동 설치 (Vanilla 자동 제외): `simple-voice-chat`, `spark`
- `RCON_PASSWORD` — 모든 마인크래프트 컨테이너 공통 (외부 노출 X, network 내부 접근만)

### 컨테이너 생성 흐름 (`docker_service.create_container`)

1. 로더/버전 정규화 — `lastest` 같은 오타 보정, 빈 값 → `LATEST`
2. **이미지 자동 선택** (`select_image`) — Spigot/Bukkit 또는 1.20.x 이하면 `:java21`, 그 외 `:latest`
3. **메모리 자동 조정** — Spigot/Bukkit 은 4GB (BuildTools + 월드 생성 OOM 방지), 그 외 2GB
4. **`MODRINTH_PROJECTS` 환경변수 빌드** — anti-xray 매핑 + always-install 합쳐서 콤마 결합. 중복 제거. Vanilla 면 빈 값 (모드 시스템 없음)
5. **`SPIGET_RESOURCES`** — Bukkit 계열만 (ProtocolLib)
6. **`ENABLE_RCON=TRUE` + `RCON_PASSWORD`** — 모든 컨테이너
7. **`--dns 8.8.8.8 1.1.1.1` 강제** — 호스트 DNS(KT 등) 장애로 itzg 의 jar 다운로드가 실패하는 사고 회피
8. `minecraft-network` 에 부착, 모든 보안 옵션 (cap_drop, no-new-privileges) 적용

### RCON 통신 (`rcon_service.py`)

봇 컨테이너와 마인크래프트 컨테이너가 같은 `minecraft-network` 에 있으므로 컨테이너 이름으로 직접 접근합니다 — RCON 포트(25575)는 외부에 노출하지 않습니다. `/sayall` 은 `say <msg>`, `/tps` 는 로더별 다른 명령(`TPS_COMMANDS` 매핑)을 보내고 응답 텍스트에서 첫 0~20 사이 숫자를 추출합니다 (`_extract_first_tps`). MC 색코드(`§a` 등)와 줄바꿈은 `_strip_mc_codes`/`_sanitize_message` 로 정리.

## Notable gotchas (이전 사고 기반)

- **Spigot + `:latest` 이미지 = 항상 죽음.** `Unsupported Java detected (69.0)`. `select_image` 로 강제로 `:java21` 보내야 합니다. 이건 봇 결함이 아니라 itzg `:latest` 가 Java 25 를 쓰는 것.
- **Quilt + Modrinth `fabric-api` 명시 = mixin 충돌로 컨테이너 죽음.** `voicechat-quilt-*.jar` 안에 jar-in-jar 로 QSL 이 들어있어 외부 `fabric-api` 를 추가하면 충돌. `ANTI_XRAY_PROJECTS["QUILT"]` 는 의도적으로 fabric-api 빠져 있음.
- **VANILLA 는 모드/플러그인 시스템 자체가 없음** — `MODRINTH_PROJECTS` 줘도 jar 다운로드는 되지만 서버 jar 가 무시. 봇은 Vanilla 일 때 자동 설치 전체 스킵.
- **컨테이너가 root 로 만든 호스트 파일은 fri4666 가 직접 못 지움.** sudo 없이 정리하려면 위 alpine docker run 패턴 사용.
- **itzg `MODRINTH_PROJECTS=anti-xray` 의 자동 매칭은 컨테이너의 TYPE/VERSION 기반.** VERSION=LATEST 면 가장 최신 jar 받는데 Fabric API 등 의존성과 호환 안 맞을 수 있음 (이전 fabric 1.4.16+26.1 케이스). 안정성 원하면 명시 버전 권장.
- **Spigot 1.20.1 BuildTools jar 는 Java 21 에서 chunk 생성이 매우 느리거나 stuck.** 1.21.x 권장.

## Coding conventions

- 사용자 응답 메시지는 모두 한국어. 영문 메시지 발견 시 `formatters.py` 또는 cog 안에서 한국어로 번역.
- 슬래시 명령은 `discord.app_commands` 로 작성. prefix(`!`) 명령은 더 이상 쓰지 않음 (`/help`, `/create` 등 `/` 사용).
- 새 자동 설치 모드/플러그인 추가는 `Settings.ALWAYS_INSTALL_MODRINTH` 또는 `ANTI_XRAY_PROJECTS` 매핑에 한 줄 추가하는 식. 코드 분기 추가하지 말 것.
- `services/docker_service.py` 의 `select_image` 같은 매핑 함수를 거치지 않고 컨테이너 이미지를 직접 하드코딩하지 말 것.
