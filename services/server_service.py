from typing import Optional, Dict, Any
from .docker_service import DockerService
from .port_manager import PortManager
from bot.utils.validators import validate_server_name
from config.settings import Settings


class ServerService:
    """Business logic for server management with limits and validation."""

    def __init__(self):
        self.docker_service = DockerService()
        self.port_manager = PortManager()

    async def create_server(
        self,
        name: str,
        guild_id: int,
        user_id: int,
        mod_loader: str = "VANILLA",
        version: str = "LATEST",
        enable_anti_xray: bool = True,
    ) -> tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
        """Create a new Minecraft server with validation and limits."""
        # Validate name
        is_valid, error = validate_server_name(name)
        if not is_valid:
            return False, error, None

        # 모드 로더 검증
        loader = (mod_loader or "VANILLA").upper()
        if loader not in Settings.SUPPORTED_MOD_LOADERS:
            supported = ", ".join(sorted(Settings.SUPPORTED_MOD_LOADERS))
            return False, f"지원하지 않는 모드 로더입니다. 사용 가능: {supported}", None

        # Check if container already exists
        existing = await self.docker_service.get_status(name)
        if existing:
            return False, f"'{name}' 서버가 이미 존재합니다", None

        # Check limits
        containers = await self.docker_service.list_containers()
        if len(containers) >= 50:  # Global limit
            return False, "최대 서버 개수(50개)에 도달했습니다", None

        # Allocate port
        port = self.port_manager.allocate()
        if port is None:
            return False, "사용 가능한 포트가 없습니다", None

        try:
            ver = (version or Settings.DEFAULT_VERSION).strip() or Settings.DEFAULT_VERSION
            result = await self.docker_service.create_container(
                name, port,
                mod_loader=loader,
                version=ver,
                enable_anti_xray=enable_anti_xray,
            )
            return True, None, result
        except Exception as e:
            self.port_manager.release(port)
            return False, f"서버 생성에 실패했습니다: {str(e)}", None

    async def start_server(self, name: str) -> tuple[bool, Optional[str]]:
        """Start a server."""
        existing = await self.docker_service.get_status(name)
        if not existing:
            return False, f"'{name}' 서버를 찾을 수 없습니다"

        if existing["status"] == "running":
            return False, f"'{name}' 서버는 이미 실행 중입니다"

        success = await self.docker_service.start_container(name)
        if success:
            return True, None
        return False, f"'{name}' 서버 시작에 실패했습니다"

    async def stop_server(self, name: str) -> tuple[bool, Optional[str]]:
        """Stop a server."""
        existing = await self.docker_service.get_status(name)
        if not existing:
            return False, f"'{name}' 서버를 찾을 수 없습니다"

        if existing["status"] == "exited":
            return False, f"'{name}' 서버는 이미 정지되어 있습니다"

        success = await self.docker_service.stop_container(name)
        if success:
            return True, None
        return False, f"'{name}' 서버 정지에 실패했습니다"

    async def delete_server(self, name: str) -> tuple[bool, Optional[str]]:
        """Delete a server and release its port."""
        existing = await self.docker_service.get_status(name)
        if not existing:
            return False, f"'{name}' 서버를 찾을 수 없습니다"

        # Release port
        if existing["port"]:
            self.port_manager.release(existing["port"])

        success = await self.docker_service.delete_container(name)
        if success:
            return True, None
        return False, f"'{name}' 서버 삭제에 실패했습니다"

    async def list_servers(self) -> list[Dict[str, Any]]:
        """List all servers."""
        return await self.docker_service.list_containers()

    async def get_server_status(self, name: str) -> Optional[Dict[str, Any]]:
        """Get server status."""
        return await self.docker_service.get_status(name)

    async def list_mods(self, name: str) -> tuple[bool, Optional[str], list[str]]:
        """서버의 mods 폴더에 들어 있는 모드 파일 목록을 반환합니다."""
        import os

        existing = await self.docker_service.get_status(name)
        if not existing:
            return False, f"'{name}' 서버를 찾을 수 없습니다", []

        mods_dir = f"/docker/minecraft/{name}/mods"
        if not os.path.isdir(mods_dir):
            return True, None, []

        mods = sorted(
            f for f in os.listdir(mods_dir)
            if f.lower().endswith((".jar", ".disabled"))
        )
        return True, None, mods

    async def add_mod(
        self, name: str, filename: str, content: bytes
    ) -> tuple[bool, Optional[str]]:
        """업로드된 모드 파일을 서버의 mods 폴더에 저장합니다."""
        import os

        existing = await self.docker_service.get_status(name)
        if not existing:
            return False, f"'{name}' 서버를 찾을 수 없습니다"

        loader = (existing.get("mod_loader") or "VANILLA").upper()
        if loader == "VANILLA":
            return False, "바닐라 서버에는 모드를 추가할 수 없습니다. FORGE/FABRIC 등으로 다시 만들어주세요"

        # 디렉터리 트래버설 방지 (확장자 검사보다 먼저)
        safe_name = os.path.basename(filename)
        if safe_name != filename or "/" in filename or "\\" in filename or safe_name.startswith("."):
            return False, "잘못된 파일 이름입니다"

        if not safe_name.lower().endswith(".jar"):
            return False, "모드 파일은 .jar 형식만 허용됩니다"

        mods_dir = f"/docker/minecraft/{name}/mods"
        target = os.path.join(mods_dir, safe_name)
        try:
            os.makedirs(mods_dir, exist_ok=True)
            with open(target, "wb") as f:
                f.write(content)
        except OSError as e:
            return False, f"파일 저장 실패: {e}"

        return True, None

    async def remove_mod(
        self, name: str, filename: str
    ) -> tuple[bool, Optional[str]]:
        """모드 파일을 삭제합니다."""
        import os

        existing = await self.docker_service.get_status(name)
        if not existing:
            return False, f"'{name}' 서버를 찾을 수 없습니다"

        safe_name = os.path.basename(filename)
        if safe_name != filename or "/" in filename or "\\" in filename:
            return False, "잘못된 파일 이름입니다"

        target = f"/docker/minecraft/{name}/mods/{safe_name}"
        if not os.path.isfile(target):
            return False, f"'{safe_name}' 모드를 찾을 수 없습니다"

        try:
            os.remove(target)
        except OSError as e:
            return False, f"파일 삭제 실패: {e}"

        return True, None
