import asyncio
import re
import socket
import struct
from typing import Optional

import docker

from config.settings import Settings


class MCRconException(Exception):
    """RCON 프로토콜 오류."""


class _ThreadSafeRcon:
    """asyncio.to_thread 워커에서도 안전한 최소 RCON 클라이언트.

    Why: pypi `mcrcon` 은 timeout 을 SIGALRM 으로 구현해서 메인 스레드 밖에서는
    "signal only works in main thread" 로 항상 실패합니다. 여기서는 같은 효과를
    `socket.settimeout` 으로 구현해 워커 스레드에서도 동작하게 합니다.
    """

    def __init__(self, host: str, password: str, port: int = 25575, timeout: float = 5.0):
        self._host, self._password, self._port, self._timeout = host, password, port, timeout
        self._sock: Optional[socket.socket] = None

    def __enter__(self) -> "_ThreadSafeRcon":
        self._sock = socket.create_connection((self._host, self._port), timeout=self._timeout)
        self._sock.settimeout(self._timeout)
        rid = self._send_packet(3, self._password)         # SERVERDATA_AUTH
        resp_id, _ty, _body = self._recv_packet()
        if resp_id == -1:
            raise MCRconException("RCON 인증 실패 (비밀번호 불일치)")
        if resp_id != rid:
            raise MCRconException(f"RCON 인증 응답 ID 불일치 (req={rid}, resp={resp_id})")
        return self

    def __exit__(self, *_):
        if self._sock is not None:
            try:
                self._sock.close()
            finally:
                self._sock = None

    def command(self, cmd: str) -> str:
        rid = self._send_packet(2, cmd)                    # SERVERDATA_EXECCOMMAND
        _resp_id, _ty, body = self._recv_packet()
        return body

    # ---- protocol ----
    _next_id = 0

    def _send_packet(self, type_: int, body: str) -> int:
        if self._sock is None:
            raise MCRconException("RCON 소켓이 닫혀 있습니다")
        _ThreadSafeRcon._next_id = (_ThreadSafeRcon._next_id + 1) & 0x7FFFFFFF
        rid = _ThreadSafeRcon._next_id
        payload = struct.pack("<ii", rid, type_) + body.encode("utf-8") + b"\x00\x00"
        self._sock.sendall(struct.pack("<i", len(payload)) + payload)
        return rid

    def _recv_all(self, n: int) -> bytes:
        assert self._sock is not None
        buf = b""
        while len(buf) < n:
            chunk = self._sock.recv(n - len(buf))
            if not chunk:
                raise MCRconException("RCON 연결이 끊어졌습니다")
            buf += chunk
        return buf

    def _recv_packet(self) -> tuple[int, int, str]:
        (length,) = struct.unpack("<i", self._recv_all(4))
        if length < 10:
            raise MCRconException(f"RCON 응답 길이 비정상: {length}")
        body = self._recv_all(length)
        rid, ty = struct.unpack("<ii", body[:8])
        return rid, ty, body[8:-2].decode("utf-8", errors="replace")


# 로더별 TPS 명령
TPS_COMMANDS = {
    "PAPER":      "tps",
    "SPIGOT":     "tps",
    "BUKKIT":     "tps",
    "CRAFTBUKKIT":"tps",
    "FORGE":      "forge tps",
    "NEOFORGE":   "neoforge tps",
    "FABRIC":     "spark tps",
    "QUILT":      "spark tps",
    "VANILLA":    "tick query",   # 1.21+ 내장
}


# ANSI 색 코드(§a, §c 등) + Minecraft formatting code 제거
_MC_COLOR_RE = re.compile(r"§[0-9a-fk-or]", re.IGNORECASE)


def _strip_mc_codes(text: str) -> str:
    """마인크래프트 색/포맷 코드를 디스코드용으로 제거."""
    return _MC_COLOR_RE.sub("", text or "").strip()


def _sanitize_message(msg: str) -> str:
    """RCON 명령 인젝션 방지 — 줄바꿈 차단 + 공백 정리."""
    return msg.replace("\r", " ").replace("\n", " ").strip()


class RconService:
    """봇 컨테이너에서 마인크래프트 컨테이너로 RCON 명령을 보냅니다.

    봇과 마인크래프트 컨테이너는 같은 docker network('minecraft-network')에
    있으므로 컨테이너 이름으로 직접 접근합니다. 외부 포트 노출 불필요.
    """

    def __init__(self):
        self.client = docker.DockerClient(base_url="unix:///var/run/docker.sock")

    def _get_loader(self, name: str) -> Optional[str]:
        """컨테이너의 TYPE 환경변수 (= 모드 로더)를 읽어옵니다."""
        try:
            container = self.client.containers.get(name)
            for entry in container.attrs.get("Config", {}).get("Env", []) or []:
                if entry.startswith("TYPE="):
                    return entry.split("=", 1)[1].upper()
        except docker.errors.NotFound:
            return None
        return None

    async def _send(self, name: str, command: str, timeout: float = 5.0) -> str:
        """RCON 명령 한 줄 전송하고 응답을 받습니다 (블로킹 호출은 별도 스레드)."""
        def _blocking() -> str:
            with _ThreadSafeRcon(name, Settings.RCON_PASSWORD, port=Settings.RCON_PORT, timeout=timeout) as mc:
                return mc.command(command) or ""

        return await asyncio.to_thread(_blocking)

    # ------------------------------------------------------------------ #
    # 부팅 완료 대기 — RCON `list` 가 응답할 때까지 폴링.
    # `/start` 가 "실제로 사용 가능한 시점" 에 메시지를 보내기 위해 사용합니다.
    # ------------------------------------------------------------------ #
    async def wait_until_ready(self, name: str, max_s: float = 300.0, interval: float = 3.0) -> bool:
        loop = asyncio.get_event_loop()
        deadline = loop.time() + max_s
        while loop.time() < deadline:
            try:
                await self._send(name, "list", timeout=3.0)
                return True
            except Exception:
                await asyncio.sleep(interval)
        return False

    # ------------------------------------------------------------------ #
    # /sayall — 게임 안 모든 플레이어에게 채팅 공지
    # ------------------------------------------------------------------ #
    async def say(self, name: str, message: str) -> tuple[bool, Optional[str]]:
        clean = _sanitize_message(message)
        if not clean:
            return False, "공지 내용이 비어있습니다"

        try:
            await self._send(name, f"say {clean}")
            return True, None
        except (MCRconException, ConnectionError, OSError) as e:
            return False, f"RCON 접속 실패: {e}"

    # ------------------------------------------------------------------ #
    # /tps — 로더별 TPS 명령 분기 + 결과 정리
    # ------------------------------------------------------------------ #
    async def tps(self, name: str) -> tuple[bool, Optional[str], dict]:
        loader = self._get_loader(name)
        if loader is None:
            return False, f"'{name}' 서버를 찾을 수 없습니다", {}

        command = TPS_COMMANDS.get(loader)
        if command is None:
            return False, f"'{loader}' 로더는 TPS 조회를 지원하지 않습니다", {}

        try:
            raw = await self._send(name, command)
        except (MCRconException, ConnectionError, OSError) as e:
            return False, f"RCON 접속 실패: {e}", {}

        clean = _strip_mc_codes(raw)
        return True, None, {
            "loader": loader,
            "command": command,
            "raw": clean,
            "tps_1m": _extract_first_tps(clean),
        }


# ------------------------------------------------------------------ #
# 응답 파싱 — 로더마다 응답 형식이 달라 일단 첫 번째 보이는 숫자(0~20)를 추출
# ------------------------------------------------------------------ #
_TPS_NUM_RE = re.compile(r"(\d{1,2}\.\d{1,3})")


def _extract_first_tps(text: str) -> Optional[float]:
    for m in _TPS_NUM_RE.finditer(text or ""):
        try:
            v = float(m.group(1))
        except ValueError:
            continue
        if 0.0 <= v <= 20.0:
            return v
    return None
