from langgraph.graph import StateGraph, END

from .state import AuditState
from .git_utils import clone_repository
from .analysis import analyze_repo_structure

# --- 조건부 엣지 로직 --- #
def should_continue_after_clone(state: AuditState) -> str:
    """클론 성공 여부에 따라 다음 단계를 결정합니다."""
    if state.get("error"):
        print(f"오류 발생으로 프로세스 중단: {state['error']}")
        return END # 오류 발생 시 바로 종료
    if not state.get("local_repo_path"):
         print("리포지토리 클론 실패로 프로세스 중단")
         return END # 클론 실패 시 바로 종료
    return "analyze_repo" # 성공 시 analyze_repo로 이동

# --- 조건부 엣지 로직 --- #
def should_continue_after_analyze(state: AuditState) -> str:
    """컴파일 성공 여부에 따라 다음 단계를 결정합니다."""
    compile_status = state.get("repo_analysis", {}).get("compile_status", "unknown")
    # 이제 'success_with_hint' 상태는 없으므로 'success'만 확인
    if state.get("error") or compile_status != "success":
        print(f"컴파일 실패(상태: {compile_status}) 또는 오류 발생으로 분석 중단.")
        if state.get("error"):
            print(f"  오류: {state['error']}")
        return END # 오류 또는 컴파일 실패 시 종료
    print(f"컴파일 성공 (상태: {compile_status}). 다음 단계 진행 가능.")
    return END # 현재 워크플로우에서는 분석 후 종료

# --- 그래프 정의 및 빌드 --- #
def build_workflow():
    """LangGraph 워크플로우를 정의하고 컴파일합니다."""
    workflow = StateGraph(AuditState)

    # 노드 추가
    workflow.add_node("clone", clone_repository)
    workflow.add_node("analyze_repo", analyze_repo_structure)

    # 엣지 추가
    workflow.set_entry_point("clone")

    # 클론 후 -> 분석 또는 종료
    workflow.add_conditional_edges(
        "clone",
        should_continue_after_clone,
        {
            "analyze_repo": "analyze_repo", # 성공 시 analyze_repo
            END: END                     # 실패 시 END
        }
    )

    # 분석 후 -> 다음 단계 또는 종료
    workflow.add_conditional_edges(
        "analyze_repo",
        should_continue_after_analyze,
        {
            END: END                     # 실패 또는 현재 워크플로우 종료
        }
    )

    # 그래프 컴파일
    app = workflow.compile()
    return app 