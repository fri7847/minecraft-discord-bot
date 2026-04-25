from typing import Set, Optional
import docker


class PortManager:
    """Manages dynamic port allocation for Minecraft servers."""

    def __init__(self, start: int = 25565, end: int = 25999):
        self.start = start
        self.end = end
        self.allocated: Set[int] = set()
        self.docker_client = docker.from_env()
        self._sync_with_docker()

    def _sync_with_docker(self):
        """Sync allocated ports with existing Docker containers."""
        for container in self.docker_client.containers.list(all=True):
            ports = container.attrs.get('NetworkSettings', {}).get('Ports', {})
            if '25565/tcp' in ports and ports['25565/tcp']:
                host_port = int(ports['25565/tcp'][0]['HostPort'])
                if self.start <= host_port <= self.end:
                    self.allocated.add(host_port)

    def allocate(self) -> Optional[int]:
        """Allocate the next available port."""
        for port in range(self.start, self.end + 1):
            if port not in self.allocated:
                self.allocated.add(port)
                return port
        return None

    def release(self, port: int):
        """Release a port back to the pool."""
        self.allocated.discard(port)

    def is_allocated(self, port: int) -> bool:
        """Check if a port is currently allocated."""
        return port in self.allocated
