from langgraph.graph import StateGraph, END

from .state import AuditState
from .git_utils import clone_repository
from .analysis import analyze_repo_structure
from .slither_analyzer import run_slither_analysis
from .test_generator import generate_mcp_tests
from .forge_runner import run_forge_mcp_tests

# --- 조건부 엣지 로직 --- #
def should_continue_after_clone(state: AuditState) -> str:
    """클론 성공 여부에 따라 다음 단계를 결정합니다."""
    if state.get("error"):
        print(f"오류 발생으로 프로세스 중단: {state['error']}")
        return END
    if not state.get("local_repo_path"):
         print("리포지토리 클론 실패로 프로세스 중단")
         return END
    return "analyze_repo"

def should_continue_after_analyze(state: AuditState) -> str:
    """컴파일 성공 여부에 따라 다음 단계를 결정합니다."""
    compile_status = state.get("repo_analysis", {}).get("compile_status", "unknown")
    if state.get("error") or compile_status not in ["success", "success_info_error"]:
        print(f"컴파일 실패(상태: {compile_status}) 또는 오류 발생으로 분석 중단.")
        if state.get("error"):
            print(f"  오류: {state['error']}")
        return END
    print(f"컴파일 성공 (상태: {compile_status}). Slither 분석 단계로 진행.")
    return "run_slither"

def decide_after_mcp_generation(state: AuditState) -> str:
    """MCP 테스트 생성 후 실행 단계로 이동하거나 오류 시 종료합니다."""
    if state.get("error"):
        print(f"MCP 테스트 생성 중 오류 발생: {state['error']}. 워크플로우 종료.")
        return END
    if not state.get("generated_test_files"):
        print("생성된 MCP 테스트 파일이 없어 실행 단계를 건너뜁니다. 워크플로우 종료.")
        return END
    print("MCP 테스트 생성 완료. Forge 실행 단계로 진행.")
    return "run_mcp_forge_tests"

def decide_after_mcp_run(state: AuditState) -> str:
    """MCP 테스트 실행 후 종료합니다."""
    if state.get("error"):
        print(f"MCP 테스트 실행 중 오류 발생: {state['error']}")
    else:
        test_results = state.get("mcp_test_results", {})
        summary = test_results.get("summary", {})
        print(f"MCP 테스트 실행 완료 (Total: {summary.get('total', 0)}, Passed: {summary.get('passed', 0)}, Failed: {summary.get('failed', 0)}). 워크플로우 종료.")
    return END

# --- 그래프 정의 및 빌드 --- #
def build_workflow():
    """LangGraph 워크플로우를 정의하고 컴파일합니다."""
    workflow = StateGraph(AuditState)

    # 노드 추가
    workflow.add_node("clone", clone_repository)
    workflow.add_node("analyze_repo", analyze_repo_structure)
    workflow.add_node("run_slither", run_slither_analysis)
    workflow.add_node("generate_mcp_tests", generate_mcp_tests)
    workflow.add_node("run_mcp_forge_tests", run_forge_mcp_tests)

    # 엣지 추가
    workflow.set_entry_point("clone")

    # clone -> analyze_repo 또는 END
    workflow.add_conditional_edges("clone", should_continue_after_clone, {"analyze_repo": "analyze_repo", END: END})

    # analyze_repo -> run_slither 또는 END
    workflow.add_conditional_edges("analyze_repo", should_continue_after_analyze, {"run_slither": "run_slither", END: END})

    # run_slither -> generate_mcp_tests
    workflow.add_edge("run_slither", "generate_mcp_tests")

    # generate_mcp_tests -> run_mcp_forge_tests 또는 END
    workflow.add_conditional_edges("generate_mcp_tests", decide_after_mcp_generation, {"run_mcp_forge_tests": "run_mcp_forge_tests", END: END})

    # run_mcp_forge_tests -> END
    workflow.add_conditional_edges("run_mcp_forge_tests", decide_after_mcp_run, {END: END})

    # 그래프 컴파일
    app = workflow.compile()
    return app