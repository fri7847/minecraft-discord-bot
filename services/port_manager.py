from typing import Set, Optional
import socket
import docker

from config.settings import Settings


class PortManager:
    """Manages dynamic port allocation for Minecraft servers."""

    def __init__(self, start: Optional[int] = None, end: Optional[int] = None):
        self.start = start if start is not None else Settings.PORT_START
        self.end = end if end is not None else Settings.PORT_END
        self.allocated: Set[int] = set()
        self.docker_client = docker.from_env()
        self._sync_with_docker()

    def _sync_with_docker(self):
        """Sync allocated ports with existing Docker containers.

        mc port (25565/tcp) 외에도 voicechat UDP publish (24454+) 를 함께 보고
        대응하는 mc port 를 마킹한다. 봇 외부에서 만든 컨테이너가 voice port 만
        잡고 있어도 같은 mc-voice offset 의 새 컨테이너가 충돌 안 하도록 함.
        """
        voice_base = Settings.VOICE_PORT_BASE
        voice_max = voice_base + (self.end - self.start)
        for container in self.docker_client.containers.list(all=True):
            ports = container.attrs.get('NetworkSettings', {}).get('Ports', {})
            # mc port
            if '25565/tcp' in ports and ports['25565/tcp']:
                host_port = int(ports['25565/tcp'][0]['HostPort'])
                if self.start <= host_port <= self.end:
                    self.allocated.add(host_port)
            # voice port (24454+/udp) — 대응 mc port 도 함께 마킹
            for proto_port, bindings in ports.items():
                if not (proto_port.endswith('/udp') and bindings):
                    continue
                host_voice = int(bindings[0]['HostPort'])
                if voice_base <= host_voice <= voice_max:
                    corresponding_mc = self.start + (host_voice - voice_base)
                    if self.start <= corresponding_mc <= self.end:
                        self.allocated.add(corresponding_mc)

    def allocate(self) -> Optional[int]:
        """Allocate the next available port."""
        for port in range(self.start, self.end + 1):
            if port not in self.allocated:
                self.allocated.add(port)
                return port
        return None

    def mark_unusable(self, port: int) -> None:
        """포트를 영구 점유 마킹 (docker 외부 — WSL2 의 Windows 측 등 — 가 잡은 포트).

        실제 start 시점에 'address already in use' 가 나면 이걸 호출해서
        같은 포트를 두 번 시도 안 하게 한다.
        """
        self.allocated.add(port)

    def release(self, port: int):
        """Release a port back to the pool."""
        self.allocated.discard(port)

    def is_allocated(self, port: int) -> bool:
        """Check if a port is currently allocated."""
        return port in self.allocated
