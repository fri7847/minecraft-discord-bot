import docker
import asyncio
import re
from typing import Optional, Dict, Any
from docker.errors import APIError, NotFound

from config.settings import Settings


def select_image(mod_loader: str, version: str) -> str:
    """모드 로더/버전에 맞는 itzg 이미지 태그를 결정합니다.

    - SPIGOT/BUKKIT 계열: BuildTools 가 신 Java 를 거부 → java21
    - 1.20.x 이하 vanilla/paper/fabric/quilt/forge: 안전하게 java21
    - 그 외(LATEST, 1.21+): 기본 이미지 (Java 25)
    """
    loader = (mod_loader or "VANILLA").upper()
    ver = (version or "LATEST").upper()

    if loader in Settings.JAVA21_REQUIRED_LOADERS:
        return Settings.MINECRAFT_IMAGE_JAVA21

    if ver != "LATEST":
        m = re.match(r"^1\.(\d+)", ver)
        if m and int(m.group(1)) <= 20:
            return Settings.MINECRAFT_IMAGE_JAVA21

    return Settings.MINECRAFT_IMAGE


class DockerService:
    """Wrapper for Docker SDK operations with security hardening."""

    def __init__(self):
        self.client = docker.DockerClient(base_url='unix:///var/run/docker.sock')
        self._ensure_network()

    def _ensure_network(self):
        """Ensure the minecraft network exists."""
        try:
            self.client.networks.get("minecraft-network")
        except NotFound:
            self.client.networks.create(
                name="minecraft-network",
                driver="bridge",
                internal=False
            )

    async def create_container(
        self,
        name: str,
        port: int,
        ram_mb: Optional[int] = None,
        cpu: float = 1.0,
        mod_loader: str = "VANILLA",
        version: str = "LATEST",
        enable_anti_xray: bool = True,
    ) -> Dict[str, Any]:
        """Create a Minecraft server container with security limits."""
        volume_path = f"/docker/minecraft/{name}"
        mods_path = f"/docker/minecraft/{name}/mods"

        loader = (mod_loader or "VANILLA").upper()
        ver = (version or Settings.DEFAULT_VERSION).strip() or Settings.DEFAULT_VERSION
        # 사용자가 'lastest' 같은 흔한 오타를 보내도 정상 동작하도록
        if ver.lower() in {"lastest", "latst", "lates"}:
            ver = "LATEST"

        # SPIGOT/BUKKIT 은 BuildTools + 월드 생성 비용이 커서 OOM 위험 → 4GB
        if ram_mb is None:
            ram_mb = 4096 if loader in Settings.JAVA21_REQUIRED_LOADERS else 2048

        environment = {
            "EULA": "TRUE",
            "MEMORY": f"{ram_mb // 1024}G",
            "UID": "0",
            "GID": "0",
            "TYPE": loader,
            "VERSION": ver,
            # RCON — /sayall, /tps 등 봇 명령 처리에 필요. 외부 포트는 노출하지 않음 (network 내부 접근만).
            "ENABLE_RCON": "TRUE",
            "RCON_PASSWORD": Settings.RCON_PASSWORD,
            "RCON_PORT": str(Settings.RCON_PORT),
        }

        # Modrinth 자동 설치 목록 빌드 (anti-xray + 항상 설치할 모드)
        # VANILLA 는 모드/플러그인 시스템이 없으므로 자동 설치 전체 스킵
        modrinth_projects: list[str] = []
        anti_xray_project = None
        if loader != "VANILLA":
            if enable_anti_xray:
                anti_xray_project = Settings.ANTI_XRAY_PROJECTS.get(loader)
                if anti_xray_project:
                    modrinth_projects.extend(anti_xray_project.split(","))
                spiget_dep = Settings.ANTI_XRAY_SPIGET_DEPS.get(loader)
                if spiget_dep:
                    environment["SPIGET_RESOURCES"] = spiget_dep
            modrinth_projects.extend(Settings.ALWAYS_INSTALL_MODRINTH)

        if modrinth_projects:
            seen = set()
            uniq = [p for p in modrinth_projects if not (p in seen or seen.add(p))]
            environment["MODRINTH_PROJECTS"] = ",".join(uniq)
            environment["MODRINTH_DOWNLOAD_DEPENDENCIES"] = "required"

        image = select_image(loader, ver)

        # Security-hardened container configuration
        container = self.client.containers.create(
            image=image,
            name=name,
            environment=environment,
            volumes={
                volume_path: {"bind": "/data", "mode": "rw"},
                mods_path: {"bind": "/mods", "mode": "rw"},
            },
            ports={"25565/tcp": port},
            network="minecraft-network",
            dns=["8.8.8.8", "1.1.1.1"],   # 호스트 DNS 장애 시에도 모드/플러그인 다운로드 가능
            mem_limit=f"{ram_mb}m",
            cpu_quota=int(cpu * 100000),
            cpu_period=100000,
            restart_policy={"Name": "on-failure", "MaximumRetryCount": 3},
            cap_drop=["NET_ADMIN", "SYS_ADMIN"],
            cap_add=["CHOWN", "SETUID", "SETGID"],
            security_opt=["no-new-privileges:true"],
            detach=True
        )

        return {
            "id": container.id,
            "name": container.name,
            "port": port,
            "mod_loader": loader,
            "version": ver,
            "image": image,
            "mods_path": mods_path,
            "anti_xray": anti_xray_project,  # 적용된 Modrinth slug, 또는 None
        }

    async def start_container(self, name: str) -> bool:
        """Start a container by name."""
        try:
            container = self.client.containers.get(name)
            container.start()
            return True
        except NotFound:
            return False

    async def stop_container(self, name: str) -> bool:
        """Stop a container by name."""
        try:
            container = self.client.containers.get(name)
            container.stop(timeout=30)
            return True
        except NotFound:
            return False

    async def delete_container(self, name: str) -> bool:
        """Delete a container and its volume."""
        try:
            container = self.client.containers.get(name)
            container.remove(force=True)

            # Remove volume
            volume_path = f"/docker/minecraft/{name}"
            try:
                volume = self.client.volumes.get(f"minecraft_{name}")
                volume.remove()
            except NotFound:
                pass

            return True
        except NotFound:
            return False

    async def list_containers(self) -> list[Dict[str, Any]]:
        """itzg/minecraft-server 이미지 컨테이너만 마인크래프트 서버로 취급."""
        containers = []
        for container in self.client.containers.list(all=True):
            tags = container.image.tags or []
            if not any("itzg/minecraft-server" in t.lower() for t in tags):
                continue

            ports = container.attrs.get('NetworkSettings', {}).get('Ports', {})
            host_port = None
            if '25565/tcp' in ports and ports['25565/tcp']:
                host_port = int(ports['25565/tcp'][0]['HostPort'])

            containers.append({
                "name": container.name,
                "status": container.status,
                "id": container.id[:12],
                "port": host_port,
            })
        return containers

    async def get_status(self, name: str) -> Optional[Dict[str, Any]]:
        """Get detailed status of a container."""
        try:
            container = self.client.containers.get(name)
            ports = container.attrs.get('NetworkSettings', {}).get('Ports', {})
            host_port = None
            if '25565/tcp' in ports and ports['25565/tcp']:
                host_port = int(ports['25565/tcp'][0]['HostPort'])

            env_list = container.attrs.get('Config', {}).get('Env', []) or []
            env_dict = {}
            for entry in env_list:
                if "=" in entry:
                    k, v = entry.split("=", 1)
                    env_dict[k] = v

            return {
                "name": container.name,
                "status": container.status,
                "port": host_port,
                "created": container.attrs['Created'],
                "mod_loader": env_dict.get("TYPE", "VANILLA"),
                "version": env_dict.get("VERSION", "LATEST"),
            }
        except NotFound:
            return None
