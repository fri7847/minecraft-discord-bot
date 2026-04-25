from config.settings import Settings


STATUS_LABELS = {
    "running": "실행 중",
    "exited": "정지됨",
    "created": "생성됨",
    "restarting": "재시작 중",
    "paused": "일시정지",
    "dead": "오류",
}


def format_success(message: str) -> str:
    """성공 메시지 포맷."""
    return f"✅ {message}"


def format_error(message: str) -> str:
    """에러 메시지 포맷."""
    return f"❌ {message}"


def format_status_label(status: str) -> str:
    """상태 코드(영문)를 한국어 라벨로 변환."""
    return STATUS_LABELS.get(status, status)


def format_address(port) -> str:
    """접속 주소 문자열 (server.fri4666.com:포트)."""
    if not port:
        return "할당된 포트 없음"
    return f"{Settings.PUBLIC_HOST}:{port}"


def format_list(servers: list) -> str:
    """서버 목록을 한국어로 포맷."""
    if not servers:
        return "📋 등록된 마인크래프트 서버가 없습니다."

    lines = ["📋 **마인크래프트 서버 목록**"]
    for server in servers:
        emoji = "🟢" if server["status"] == "running" else "🔴"
        status_kr = format_status_label(server["status"])
        port = server.get("port")
        address = format_address(port) if port else "포트 미할당"
        lines.append(f"{emoji} **{server['name']}** — {status_kr} | 접속: `{address}`")
    return "\n".join(lines)
