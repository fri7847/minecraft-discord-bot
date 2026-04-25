import re
from typing import Optional

SERVER_NAME_PATTERN = re.compile(r'^[a-zA-Z0-9_-]{1,32}$')


def validate_server_name(name: str) -> tuple[bool, Optional[str]]:
    """서버 이름의 보안 요건을 검증합니다."""
    if not name:
        return False, "서버 이름을 입력해주세요"

    if not SERVER_NAME_PATTERN.fullmatch(name):
        return False, "서버 이름은 영문/숫자/언더스코어/하이픈만 사용할 수 있으며 1~32자여야 합니다"

    # 예약된 이름 검사
    reserved_names = ["admin", "system", "root", "docker"]
    if name.lower() in reserved_names:
        return False, f"'{name}' 은(는) 예약된 이름이라 사용할 수 없습니다"

    return True, None


def validate_port(port: int) -> tuple[bool, Optional[str]]:
    """포트 번호 검증."""
    if not (1024 <= port <= 65535):
        return False, "포트는 1024~65535 범위여야 합니다"
    return True, None
