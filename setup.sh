#!/usr/bin/env bash
# minecraft-discord-bot — one-shot setup script
#
# 새 머신에서 이 한 줄이면 끝:
#   git clone https://github.com/fri7847/minecraft-discord-bot.git
#   cd minecraft-discord-bot && chmod +x setup.sh && ./setup.sh
#
# 필요한 것: sudo 권한 + 인터넷
# 자동 처리: Docker 설치, minecraft-network, /docker/minecraft, .env, 컨테이너 빌드
#
# 멱등(idempotent)이라 재실행 안전. 이미 처리된 단계는 건너뜀.

set -euo pipefail

# --- 색깔 출력 ---
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
RESET='\033[0m'

info() { echo -e "${GREEN}[+]${RESET} $*"; }
warn() { echo -e "${YELLOW}[!]${RESET} $*"; }
err()  { echo -e "${RED}[x]${RESET} $*" >&2; }
step() { echo -e "\n${BLUE}=== $* ===${RESET}"; }

# 스크립트 위치를 기준으로 작업 (다른 곳에서 호출돼도 안전)
cd "$(dirname "$(readlink -f "$0")")"

# --- 0) 사전 점검 ---
step "0) 사전 점검"

if [[ "$(uname -s)" != "Linux" && "$(uname -s)" != "Darwin" ]]; then
    err "Linux 또는 macOS 만 지원합니다. (현재: $(uname -s))"
    exit 1
fi

if ! command -v sudo >/dev/null 2>&1; then
    err "sudo 명령이 필요합니다."
    exit 1
fi

# sudo 비밀번호 미리 캐싱 (이후 단계에서 묻지 않게)
if ! sudo -v; then
    err "sudo 권한이 필요합니다."
    exit 1
fi

info "기본 사전 점검 통과 ($(uname -sm))"

# --- 1) Docker 설치 ---
step "1) Docker 설치 확인"

if ! command -v docker >/dev/null 2>&1; then
    info "Docker 가 없어서 설치합니다 (get.docker.com)..."
    curl -fsSL https://get.docker.com | sudo sh
    sudo usermod -aG docker "$USER"
    warn "Docker 그룹 적용을 위해 로그아웃·로그인 후 ./setup.sh 를 다시 실행하세요."
    warn "또는 동일 셰에서 'newgrp docker' 후 다시 실행."
    exit 0
else
    info "Docker 가 이미 설치되어 있습니다: $(docker --version)"
fi

# 그룹 권한 확인 — sudo 없이 docker 가 동작하는지
if ! docker info >/dev/null 2>&1; then
    err "현재 사용자가 docker 그룹에 없습니다. 'sudo usermod -aG docker $USER' 후 재로그인하세요."
    exit 1
fi

# docker compose v2 확인 (v1 docker-compose 는 미지원)
if ! docker compose version >/dev/null 2>&1; then
    err "docker compose v2 가 동작하지 않습니다. Docker 를 최신으로 업데이트하세요."
    exit 1
fi
info "docker compose v2 동작 확인: $(docker compose version --short 2>/dev/null || docker compose version)"

# --- 2) minecraft-network 생성 ---
step "2) Docker 네트워크 (minecraft-network)"

if docker network inspect minecraft-network >/dev/null 2>&1; then
    info "minecraft-network 가 이미 존재합니다."
else
    info "minecraft-network 를 새로 만듭니다."
    docker network create minecraft-network >/dev/null
fi

# --- 3) /docker/minecraft 디렉토리 ---
step "3) 마크 데이터 호스트 디렉토리 (/docker/minecraft)"

if [[ ! -d /docker/minecraft ]]; then
    info "/docker/minecraft 를 생성합니다 (sudo 필요)."
    sudo mkdir -p /docker/minecraft
    sudo chown "$USER":"$USER" /docker/minecraft
else
    info "/docker/minecraft 가 이미 존재합니다."
fi

# --- 4) .env 작성 ---
step "4) .env 환경변수 파일"

if [[ -f .env ]]; then
    info ".env 가 이미 존재합니다. 기존 값을 그대로 사용합니다."
    info "내용을 바꾸려면 ./setup.sh 종료 후 .env 직접 편집 또는 .env 삭제 후 재실행."
else
    info ".env 를 새로 만듭니다. 아래 값들을 입력하세요."
    echo

    # 토큰: 필수
    while :; do
        read -r -p "  Discord 봇 토큰 (필수): " DISCORD_TOKEN
        [[ -n "$DISCORD_TOKEN" ]] && break
        warn "비어있습니다. 다시 입력하세요."
    done

    # 공개 호스트
    read -r -p "  공개 호스트 도메인/IP [기본: server.fri4666.com]: " PUBLIC_HOST
    PUBLIC_HOST="${PUBLIC_HOST:-server.fri4666.com}"

    # 관리자 역할
    read -r -p "  관리자 디스코드 역할 이름 [기본: Minecraft Admin]: " ADMIN_ROLE
    ADMIN_ROLE="${ADMIN_ROLE:-Minecraft Admin}"

    # RCON 비밀번호 — 엔터면 랜덤
    read -r -p "  RCON 비밀번호 [엔터=랜덤 생성]: " RCON_PASSWORD
    if [[ -z "$RCON_PASSWORD" ]]; then
        if command -v openssl >/dev/null 2>&1; then
            RCON_PASSWORD=$(openssl rand -hex 16)
        else
            RCON_PASSWORD=$(head -c 64 /dev/urandom | base64 | tr -dc 'a-zA-Z0-9' | head -c 24)
        fi
        info "랜덤 RCON 비밀번호 생성 완료 (24+자, .env 에 저장됨)"
    fi

    cat > .env <<EOF
DISCORD_TOKEN=$DISCORD_TOKEN
ADMIN_ROLE=$ADMIN_ROLE
RCON_PASSWORD=$RCON_PASSWORD
PUBLIC_HOST=$PUBLIC_HOST
EOF
    chmod 600 .env
    info ".env 작성 완료 (권한 600)"
fi

# --- 5) 컨테이너 빌드·시작 ---
step "5) 봇 컨테이너 빌드·시작"

info "docker compose up -d --build 실행 중... (첫 실행은 이미지 빌드로 1~3분 소요)"
docker compose up -d --build

# 잠깐 봇이 살아 났는지 확인
sleep 3
if [[ "$(docker inspect -f '{{.State.Status}}' minecraft-discord-bot 2>/dev/null)" != "running" ]]; then
    err "minecraft-discord-bot 컨테이너가 running 이 아닙니다. 'docker logs minecraft-discord-bot' 로 확인하세요."
    exit 1
fi

# --- 6) 마무리 안내 ---
step "6) 완료 — 다음 단계"

cat <<EOM

${GREEN}✅ 설치 완료!${RESET} 봇이 백그라운드에서 동작 중입니다.

📋 봇 로그 실시간 보기:
   ${BLUE}docker logs -f minecraft-discord-bot${RESET}
   → "총 N개 슬래시 명령 동기화 완료" 메시지가 보이면 디스코드에서 명령 사용 가능.

🌐 외부 접속을 위해 ${YELLOW}공유기/방화벽에서 포트포워딩${RESET}이 필요합니다:
   ${YELLOW}TCP + UDP   25565 ~ 25999${RESET}   (마크 본 포트 + voicechat 통합)
   같은 번호 한 쌍으로 외부에 열어주세요. 한 포트에 친구들 다 모이게 25565 만 우선 열어도 OK.

🛠 디스코드 슬래시 명령 (관리자):
   ${BLUE}/create name:<이름> mod_loader:Paper${RESET}      ─ 새 서버 생성 (옵션 18개 지원)
   ${BLUE}/start  name:<이름> [port:<포트>]${RESET}         ─ 시작 (포트 변경 시 데이터 보존)
   ${BLUE}/stop   name:<이름>${RESET}                       ─ 정지 (월드 저장)
   ${BLUE}/delete name:<이름>${RESET}                       ─ 삭제 (월드 데이터 영구 제거)
   ${BLUE}/list /status /tps /sayall /mods …${RESET}

🔄 코드 업데이트 후 재배포:
   ${BLUE}git pull && docker compose up -d --build${RESET}

EOM
