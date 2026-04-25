# Minecraft Discord Bot

Docker 위에서 마인크래프트 서버를 디스코드 슬래시 명령으로 관리하는 봇입니다.
서버 생성/시작/정지/삭제는 물론, 안티 X-ray·음성 채팅 모드 자동 설치, 게임 안 채팅 공지, TPS(성능) 측정까지 한 명령으로 처리합니다.

## 주요 기능

- **여러 모드 로더 지원**: Vanilla, Paper, Spigot, Bukkit, Fabric, Quilt, Forge, NeoForge
- **자동 환경 선택**: Spigot/구버전은 Java 21 이미지 자동, Spigot은 4GB 메모리 자동 할당
- **자동 모드 설치** (Vanilla 제외 모든 로더):
  - 안티 X-ray (Orebfuscator / AntiXray) + 의존성(ProtocolLib, Fabric API) 자동
  - Simple Voice Chat (Henkelmax)
  - Spark (성능 프로파일러)
- **게임 안 통신**: `/sayall` 채팅 공지, `/tps` 성능 측정 (RCON)
- **모드 파일 관리**: `/mods add` 로 디스코드에서 직접 .jar 업로드
- **동적 포트 할당** (25565~25999)

## 슬래시 명령

```
/create  name:foo [mod_loader] [version]    새 서버 생성 (기본 Paper, LATEST)
/start   name:foo                           서버 시작
/stop    name:foo                           서버 정지
/delete  name:foo                           서버 삭제
/list                                       모든 서버 + 접속 주소
/status  name:foo                           특정 서버 상태/접속 주소
/tps     name:foo                           성능 측정 (TPS)
/sayall  name:foo message:공지내용          게임 안 모든 플레이어에게 채팅 공지
/mods    list|add|remove                    모드 파일 관리
/help                                       전체 명령 안내
```

## 설치

```bash
git clone https://github.com/<your-account>/minecraft-discord-bot.git
cd minecraft-discord-bot

# 환경변수 설정
cp .env.example .env
# .env 를 열어서 DISCORD_TOKEN, RCON_PASSWORD 등을 채우세요

# 봇 + 네트워크 기동
docker compose up -d --build
```

## 환경변수

| 변수 | 설명 |
|---|---|
| `DISCORD_TOKEN` | Discord Developer Portal 에서 발급한 봇 토큰 (필수) |
| `ADMIN_ROLE` | 서버 관리 명령을 쓸 수 있는 역할 이름 (기본 "Minecraft Admin") |
| `RCON_PASSWORD` | 봇이 마인크래프트 컨테이너에 명령 보낼 때 쓰는 비밀번호 (필수) |
| `PUBLIC_HOST` | 응답 메시지에 표시할 서버 공개 도메인 (선택) |

## 보안

- 입력 검증으로 명령 인젝션 방지
- 컨테이너별 리소스 한도 (DoS 방지)
- 컨테이너 권한 최소화 (`cap_drop`, `no-new-privileges`)
- RCON 포트는 외부 노출 X — 봇과 마인크래프트 컨테이너가 동일 docker network 내부 통신
- 디렉터리 트래버설 차단 (`/mods add` 업로드 검증)

## 라이선스

MIT
