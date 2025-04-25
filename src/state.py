from typing import TypedDict, List, Dict, Any, Optional
from crytic_compile import CryticCompile
from .scenarios import ThreatScenario

class AuditState(TypedDict, total=False):
    """확장된 감사 프로세스의 상태를 나타냅니다."""
    # --- 기본 정보 ---
    github_url: str
    local_repo_path: Optional[str]
    error: Optional[str]

    # --- 리포지토리 분석 ---
    repo_analysis: Optional[Dict[str, Any]]
    compile_instance: Optional[CryticCompile]

    # --- 정적 분석 ---
    slither_results: Optional[List[Dict[str, Any]]]

    # --- MCP 테스트 ---
    mcp_scenarios: Optional[List[ThreatScenario]]
    generated_test_files: Optional[List[str]]
    mcp_test_results: Optional[Dict[str, Any]]

    # --- 기타 (추후 확장용) ---
    fuzz_invariant_results: Optional[Dict[str, Any]]
    final_report: Optional[str]