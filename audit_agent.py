import operator
import os
import shutil
import subprocess
import tempfile
from typing import Annotated, List, TypedDict, Union

from langgraph.graph import StateGraph, END
from git import Repo

# 1. 확장된 감사 상태 정의
class AuditState(TypedDict):
    """확장된 감사 프로세스의 상태를 나타냅니다."""
    github_url: str          # 감사 대상 GitHub URL
    local_repo_path: str | None = None # 클론된 로컬 리포지토리 경로
    repo_analysis: dict | None = None  # 리포지토리 구조 분석 결과 (컨트랙트, 프레임워크 등)
    threat_model: dict | None = None # Threat Modeling 결과
    static_analysis_findings: List[str] = [] # 일반 정적 분석 결과
    slither_findings: List[str] = []       # Slither 분석 결과
    dependency_findings: List[str] = []    # 의존성 검사 결과
    mythril_findings: List[str] = []       # Mythril 분석 결과
    report: str | None = None              # 최종 보고서 내용
    feedback: str | None = None            # 피드백 내용
    error: str | None = None               # 프로세스 중 발생한 오류

# --- Helper Function --- 
def _run_command(command: list[str], cwd: str) -> tuple[bool, str]:
    """주어진 디렉토리에서 명령어를 실행하고 결과를 반환합니다."""
    try:
        process = subprocess.run(command, cwd=cwd, capture_output=True, text=True, check=True)
        return True, process.stdout
    except FileNotFoundError:
        return False, f"Error: Command '{command[0]}' not found. Is it installed and in PATH?"
    except subprocess.CalledProcessError as e:
        return False, f"Error running command {' '.join(command)}:\n{e.stderr}"
    except Exception as e:
        return False, f"An unexpected error occurred: {e}"

# 2. 워크플로우 노드 함수 정의
def clone_repository(state: AuditState) -> dict:
    """GitHub 리포지토리를 지정된 로컬 디렉토리('./audit_repo')에 클론하거나, 이미 존재하면 스킵합니다."""
    target_dir = "./audit_repo"
    print(f"--- 리포지토리 확인/클론 시작: {state['github_url']} -> {target_dir} ---")

    if os.path.exists(target_dir):
        print(f"디렉토리 '{target_dir}'가 이미 존재합니다. 클론을 건너니다.")
        # TODO: 기존 리포지토리의 URL이 맞는지, 최신 상태인지 확인할 수 있습니다 (예: git pull).
        # 이 예제에서는 존재하면 그냥 사용합니다.
        return {"local_repo_path": target_dir, "error": None}
    else:
        print(f"디렉토리 '{target_dir}' 생성 및 클론 시작...")
        try:
            # os.makedirs(target_dir, exist_ok=True) # clone_from이 디렉토리를 생성하므로 필요 없을 수 있음
            Repo.clone_from(state['github_url'], target_dir)
            print(f"리포지토리가 '{target_dir}'에 성공적으로 클론되었습니다.")
            return {"local_repo_path": target_dir, "error": None}
        except Exception as e:
            print(f"리포지토리 클론 중 오류 발생: {e}")
            # 실패 시 생성된 디렉토리가 있다면 정리 시도
            if os.path.exists(target_dir):
                 try:
                     # git clone 실패 시 생성된 빈 디렉토리나 일부 파일 삭제
                     shutil.rmtree(target_dir)
                 except Exception as rm_e:
                     print(f"클론 실패 후 디렉토리 정리 중 오류: {rm_e}")
            return {"local_repo_path": None, "error": f"Failed to clone repository: {e}"}

def analyze_repo_structure(state: AuditState) -> dict:
    """클론된 리포지토리 구조를 분석하여 컨트랙트 파일과 프레임워크를 식별합니다."""
    print("--- 리포지토리 구조 분석 시작 ---")
    repo_path = state.get("local_repo_path")
    if not repo_path or not os.path.isdir(repo_path):
        return {"error": "Repository path not valid or not found."}

    contracts = []
    framework = "unknown"

    try:
        for root, _, files in os.walk(repo_path):
            # 특정 디렉토리 제외 (예: node_modules, .git, lib)
            if any(part in root for part in ["node_modules", ".git", "lib", "test", "script"]):
                continue

            for file in files:
                if file.endswith(".sol"):
                    # repo_path 기준으로 상대 경로 저장
                    relative_path = os.path.relpath(os.path.join(root, file), repo_path)
                    contracts.append(relative_path)
                elif file == "hardhat.config.js" or file == "hardhat.config.ts":
                    framework = "hardhat"
                elif file == "foundry.toml":
                    framework = "foundry"

        analysis_result = {
            "contracts": sorted(contracts),
            "framework": framework,
            "dependencies": "(Not implemented yet)" # 의존성 분석은 추후 구현
        }
        print(f"분석 완료: {len(contracts)}개의 Solidity 파일 발견, 프레임워크: {framework}")
        return {"repo_analysis": analysis_result, "error": None}

    except Exception as e:
        print(f"리포지토리 분석 중 오류 발생: {e}")
        return {"repo_analysis": None, "error": f"Failed to analyze repository structure: {e}"}

def threat_modeling(state: AuditState) -> dict:
    """Threat Modeling을 수행합니다 (Placeholder)."""
    print("--- Threat Modeling 수행 (Placeholder) ---")
    if not state.get("local_repo_path"):
        return {"error": "Repository not cloned."}
    # 여기에 실제 Threat Modeling 로직 추가
    # 예: LLM 호출, 아키텍처 분석, STRIDE 적용 등
    threat_model_result = {"identified_threats": ["Placeholder Threat 1", "Placeholder Threat 2"]}
    print(f"Threat Modeling 결과 (예시): {threat_model_result}")
    return {"threat_model": threat_model_result}

def run_static_analysis(state: AuditState) -> dict:
    """일반 정적 코드 분석을 수행합니다 (Placeholder)."""
    print("--- 일반 정적 분석 실행 (Placeholder) ---")
    repo_path = state.get("local_repo_path")
    if not repo_path:
        return {"error": "Repository not cloned."}
    
    # 여기에 실제 정적 분석 도구(예: bandit, pylint) 연동 코드 추가
    # 예시: bandit 실행 (Python 프로젝트 가정)
    # success, output = _run_command(["bandit", "-r", "."], cwd=repo_path)
    # findings = state.get("static_analysis_findings", [])
    # if success:
    #     findings.append("Bandit Analysis:\n" + output)
    # else:
    #     findings.append("Bandit Analysis Failed:\n" + output)
    
    findings = state.get("static_analysis_findings", []) # 임시 결과
    findings.append("일반 정적 분석 결과: 잠재적 보안 취약점 발견 (예시)")
    print(f"현재까지 발견된 사항 (정적 분석): {len(findings)}개")
    return {"static_analysis_findings": findings}

def run_slither(state: AuditState) -> dict:
    """Slither를 사용하여 Solidity 코드를 분석합니다 (Placeholder)."""
    print("--- Slither 분석 실행 (Placeholder) ---")
    repo_path = state.get("local_repo_path")
    if not repo_path:
        return {"error": "Repository not cloned."}
    
    # Solidity 파일 존재 여부 확인 로직 추가 가능
    # 여기에 실제 Slither 실행 및 결과 파싱 코드 추가
    # 예시: slither 실행
    # success, output = _run_command(["slither", "."], cwd=repo_path)
    # findings = state.get("slither_findings", [])
    # if success:
    #     findings.append("Slither Analysis:\n" + output)
    # else:
    #     findings.append("Slither Analysis Failed:\n" + output)

    findings = state.get("slither_findings", []) # 임시 결과
    findings.append("Slither 분석 결과: Reentrancy 취약점 가능성 (예시)")
    print(f"현재까지 발견된 사항 (Slither): {len(findings)}개")
    return {"slither_findings": findings}

def check_dependencies(state: AuditState) -> dict:
    """프로젝트 의존성을 검사합니다 (Placeholder)."""
    print("--- 의존성 검사 실행 (Placeholder) ---")
    repo_path = state.get("local_repo_path")
    if not repo_path:
        return {"error": "Repository not cloned."}
    
    # 여기에 실제 의존성 검사 도구(예: safety, pip-audit) 연동 코드 추가
    # 예시: safety 실행 (requirements.txt 또는 pyproject.toml 필요)
    # success, output = _run_command(["safety", "check", "-r", "requirements.txt"], cwd=repo_path)
    # findings = state.get("dependency_findings", [])
    # if success:
    #     findings.append("Dependency Check (safety):\n" + output)
    # else:
    #     findings.append("Dependency Check (safety) Failed:\n" + output)

    findings = state.get("dependency_findings", []) # 임시 결과
    findings.append("의존성 검사 결과: 알려진 취약점이 있는 패키지 사용 (예시)")
    print(f"현재까지 발견된 사항 (의존성): {len(findings)}개")
    return {"dependency_findings": findings}

def run_mythril(state: AuditState) -> dict:
    """Mythril을 사용하여 EVM 바이트코드를 분석합니다 (Placeholder)."""
    print("--- Mythril 분석 실행 (Placeholder) ---")
    repo_path = state.get("local_repo_path")
    if not repo_path:
        return {"error": "Repository not cloned."}
    
    # 분석 대상 바이트코드 식별 로직 필요
    # 여기에 실제 Mythril 실행 및 결과 파싱 코드 추가
    # 예시: myth analyze <contract_address or bytecode>
    # success, output = _run_command(["myth", "analyze", "<target>"], cwd=repo_path) # <target> 수정 필요
    # findings = state.get("mythril_findings", [])
    # if success:
    #     findings.append("Mythril Analysis:\n" + output)
    # else:
    #     findings.append("Mythril Analysis Failed:\n" + output)

    findings = state.get("mythril_findings", []) # 임시 결과
    findings.append("Mythril 분석 결과: 특정 함수에서 Integer Overflow 가능성 (예시)")
    print(f"현재까지 발견된 사항 (Mythril): {len(findings)}개")
    return {"mythril_findings": findings}

def compile_report(state: AuditState) -> dict:
    """모든 분석 결과를 종합하여 최종 감사 보고서를 생성합니다."""
    print("--- 감사 보고서 생성 ---")
    if state.get("error"): # 중간에 에러 발생 시
        report_content = f"감사 실패: {state['error']}"
        print(report_content)
        return {"report": report_content}

    all_findings = {
        "Threat Modeling": state.get("threat_model", {}),
        "Static Analysis": state.get("static_analysis_findings", []),
        "Slither Analysis": state.get("slither_findings", []),
        "Dependency Check": state.get("dependency_findings", []),
        "Mythril Analysis": state.get("mythril_findings", []),
    }

    report_lines = [f"감사 대상: {state['github_url']}", "="*30]

    has_findings = False
    for category, findings in all_findings.items():
        if findings:
            report_lines.append(f"\n[{category} 결과]")
            if isinstance(findings, list):
                if findings:
                    has_findings = True
                    for i, finding in enumerate(findings):
                        report_lines.append(f"- {finding}")
                else:
                     report_lines.append("- 발견된 사항 없음")
            elif isinstance(findings, dict):
                 has_findings = True
                 import json
                 report_lines.append(json.dumps(findings, indent=2, ensure_ascii=False))
            else:
                 report_lines.append(str(findings))
    
    if not has_findings:
        report_lines.append("\n축하합니다! 모든 분석 단계에서 특별한 문제가 발견되지 않았습니다.")

    final_report = "\n".join(report_lines)
    print(final_report)
    print("-" * 20)
    return {"report": final_report}

def cleanup(state: AuditState) -> dict:
    """임시 파일 등을 정리합니다. './audit_repo'는 삭제하지 않습니다."""
    print("--- 정리 작업 시작 (./audit_repo 제외) --- ")
    repo_path = state.get("local_repo_path") # 상태에는 여전히 경로가 있을 수 있음

    # './audit_repo'는 사용자가 관리하도록 남겨둡니다.
    if repo_path == "./audit_repo":
        print(f"감사 리포지토리 디렉토리 '{repo_path}'는 삭제하지 않습니다.")
    elif repo_path and os.path.exists(repo_path):
        # 만약 다른 임시 경로가 사용되었다면 삭제 시도 (이전 버전 호환 등)
        print(f"경고: 예상치 못한 경로 '{repo_path}'가 상태에 있습니다. 삭제를 시도합니다.")
        try:
            shutil.rmtree(repo_path)
            print(f"임시 디렉토리 '{repo_path}'가 삭제되었습니다.")
        except Exception as e:
            print(f"임시 디렉토리 삭제 중 오류 발생: {e}")
    else:
        print("정리할 추가 임시 디렉토리가 없습니다.")

    # 다른 정리 작업이 필요하면 여기에 추가 (예: 생성된 로그 파일 삭제 등)

    return {} # 상태 변경 없음

def handle_feedback(state: AuditState) -> dict:
    """피드백을 처리하거나 다음 단계를 결정합니다 (Placeholder)."""
    print("--- 피드백 처리 (Placeholder) ---")
    final_report = state.get("report")
    # 여기에 피드백 입력 요청, LLM을 이용한 보고서 개선,
    # 또는 특정 분석 재실행 등의 로직 추가 가능
    print("감사 보고서가 생성되었습니다. 필요한 경우 피드백을 기록하고 추가 조치를 취할 수 있습니다.")
    # 예시: 사용자 입력 대기 또는 자동 종료
    user_feedback = input("피드백을 입력하시겠습니까? (y/N): ")
    if user_feedback.lower() == 'y':
        feedback_text = input("피드백 내용: ")
        return {"feedback": feedback_text} # 피드백 상태 저장
    return {}

# --- 조건부 엣지 로직 --- #
def should_continue_after_clone(state: AuditState) -> str: # 함수 이름 변경
    """오류 발생 여부 또는 클론 성공 여부에 따라 다음 단계를 결정합니다."""
    if state.get("error"):
        print(f"오류 발생으로 프로세스 중단: {state['error']}")
        return "cleanup" # 오류 발생 시 정리 후 종료
    if not state.get("local_repo_path"):
         print("리포지토리 클론 실패로 프로세스 중단")
         return END
    return "analyze_repo" # 수정: 클론 성공 시 리포 분석으로 이동

def should_continue_after_analysis(state: AuditState) -> str:
    """리포지토리 분석 후 오류 여부에 따라 다음 단계를 결정합니다."""
    if state.get("error"): # analyze_repo_structure 에서 에러 발생 시
        print(f"리포지토리 분석 오류로 프로세스 중단: {state['error']}")
        # 분석 실패 시에도 정리는 필요할 수 있음
        return "cleanup"
    # 분석 성공 시 Threat Modeling 으로 진행
    return "threat_modeling"

# 3. 그래프 정의 및 노드/엣지 추가
workflow = StateGraph(AuditState)

# 노드 추가
workflow.add_node("clone", clone_repository)
workflow.add_node("analyze_repo", analyze_repo_structure) # 새 노드 추가
workflow.add_node("threat_modeling", threat_modeling)
workflow.add_node("static_analysis", run_static_analysis)
workflow.add_node("slither", run_slither) # Solidity 분석
workflow.add_node("dependency_check", check_dependencies)
workflow.add_node("mythril", run_mythril) # EVM 분석
workflow.add_node("compile_report", compile_report)
workflow.add_node("handle_feedback", handle_feedback)
workflow.add_node("cleanup", cleanup)

# 엣지 추가 (워크플로우 정의)
workflow.set_entry_point("clone")

# 조건부 시작: 클론 성공 시 -> 리포 분석
workflow.add_conditional_edges(
    "clone",
    should_continue_after_clone, # 변경된 조건 함수 사용
    {
        "analyze_repo": "analyze_repo", # 변경: 성공 시 analyze_repo로
        "cleanup": "cleanup",
        END: END
    }
)

# 리포 분석 후 -> Threat Modeling (또는 에러 시 cleanup)
workflow.add_conditional_edges(
    "analyze_repo",
    should_continue_after_analysis,
    {
        "threat_modeling": "threat_modeling", # 성공 시 Threat Modeling
        "cleanup": "cleanup"               # 실패 시 Cleanup
    }
)

# Threat Modeling 이후 엣지 연결 (기존과 동일)
workflow.add_edge("threat_modeling", "static_analysis")
workflow.add_edge("static_analysis", "slither") # Slither 실행 (조건부 실행은 추가 구현 필요)
workflow.add_edge("slither", "dependency_check")
workflow.add_edge("dependency_check", "mythril") # Mythril 실행 (조건부 실행은 추가 구현 필요)
workflow.add_edge("mythril", "compile_report")
workflow.add_edge("compile_report", "handle_feedback")
workflow.add_edge("handle_feedback", "cleanup") # 피드백 처리 후 정리
workflow.add_edge("cleanup", END) # 정리 후 최종 종료

# 4. 그래프 컴파일
app = workflow.compile()

# 5. 에이전트 실행 (예시)
if __name__ == "__main__":
    github_repo_url = input("감사할 GitHub 리포지토리 URL을 입력하세요: ") or "https://github.com/Uniswap/v4-core.git"
    initial_state = AuditState(github_url=github_repo_url)

    print("\n--- 감사 에이전트 실행 시작 ---")
    final_state = None
    try:
        # LangGraph 실행 및 상태 변화 스트리밍 (상세 로그 확인 시)
        # for event in app.stream(initial_state, {"recursion_limit": 15}): # 재귀 제한 증가
        #     for node_name, output in event.items():
        #         print(f"\n[노드 실행 완료] '{node_name}'")
        #         # print(f"상태 업데이트: {output}") # 상세 상태 변화 확인용
        #     print("-" * 10)

        # LangGraph 실행 (최종 결과만 필요 시)
        final_state = app.invoke(initial_state, {"recursion_limit": 15})

    except Exception as e:
        print(f"\n워크플로우 실행 중 예상치 못한 오류 발생: {e}")
        # 오류 발생 시에도 최종 상태 (오류 정보 포함)를 확인하거나 로깅할 수 있음
        if final_state is None: # invoke 이전 오류
            print("초기 실행 단계에서 오류가 발생했을 수 있습니다.")
        else:
             print("\n오류 발생 시점의 상태:")
             import json
             print(json.dumps(final_state, indent=2, ensure_ascii=False))
    finally:
        print("\n--- 감사 에이전트 실행 완료 ---")
        # 프로그램 종료 전 항상 정리 노드 호출 시도 (선택적)
        # if final_state and final_state.get("local_repo_path"):
        #     print("\n프로그램 종료 전 최종 정리 시도...")
        #     app.invoke({"local_repo_path": final_state["local_repo_path"]}, config={"run_name": "final_cleanup", "recursion_limit": 2}, select="cleanup")

        if final_state:
            print("\n최종 감사 보고서:")
            print(final_state.get("report", "보고서가 생성되지 않았습니다."))
            if final_state.get("feedback"):
                print("\n사용자 피드백:")
                print(final_state["feedback"]) 