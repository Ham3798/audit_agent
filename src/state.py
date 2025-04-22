from typing import TypedDict

class AuditState(TypedDict):
    """확장된 감사 프로세스의 상태를 나타냅니다."""
    github_url: str          # 감사 대상 GitHub URL
    local_repo_path: str | None = None # 클론된 로컬 리포지토리 경로
    repo_analysis: dict | None = None  # 리포지토리 구조 분석 결과 (컨트랙트, 프레임워크 등)
    error: str | None = None               # 프로세스 중 발생한 오류 