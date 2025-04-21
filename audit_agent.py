import operator
import os
import shutil
import subprocess
import tempfile
from typing import Annotated, List, TypedDict, Union

from langgraph.graph import StateGraph, END
from git import Repo
# crytic-compile 라이브러리 import 제거
# from crytic_compile import CryticCompile
# from crytic_compile.platform import exceptions as crytic_exceptions

# 1. 확장된 감사 상태 정의
class AuditState(TypedDict):
    """확장된 감사 프로세스의 상태를 나타냅니다."""
    github_url: str          # 감사 대상 GitHub URL
    local_repo_path: str | None = None # 클론된 로컬 리포지토리 경로
    repo_analysis: dict | None = None  # 리포지토리 구조 분석 결과 (컨트랙트, 프레임워크 등)
    error: str | None = None               # 프로세스 중 발생한 오류

# 2. 워크플로우 노드 함수 정의
def clone_repository(state: AuditState) -> dict:
    """GitHub 리포지토리를 지정된 로컬 디렉토리('./audit_repo')에 클론하거나, 이미 존재하면 스킵합니다."""
    target_dir = "./audit_repo"
    print(f"--- 리포지토리 확인/클론 시작: {state['github_url']} -> {target_dir} ---")

    if os.path.exists(target_dir):
        print(f"디렉토리 '{target_dir}'가 이미 존재합니다. 클론을 건너뜁니다.")
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
    """프로젝트 빌드 및 crytic-compile CLI 실행으로 분석 환경을 준비합니다."""
    print("--- 리포지토리 분석 환경 준비 (Build + crytic-compile CLI) ---")
    repo_path = state.get("local_repo_path")
    if not repo_path or not os.path.isdir(repo_path):
        return {"error": "Repository path not valid or not found."}

    framework = "unknown"
    analysis_errors = []
    build_status = "pending"
    artifacts_path = None # 아티팩트 경로 초기화
    
    try:
        # 1. 프레임워크 식별
        print("  > 프레임워크 식별 중...")
        for root, _, files in os.walk(repo_path):
             if any(f"/{part}/" in root or root.endswith(f"/{part}") for part in [".git", "node_modules", "lib", "cache", "out"]):
                 continue
             for file in files:
                 if file == "hardhat.config.js" or file == "hardhat.config.ts": framework = "hardhat"
                 elif file == "foundry.toml": framework = "foundry"
             if framework != "unknown": break
        print(f"  > 프레임워크 식별됨: {framework}")

        # 2. 네이티브 Clean 및 Build 명령어 실행
        build_command = None
        clean_command = None
        if framework == 'foundry':
            clean_command = ["forge", "clean"]
            build_command = ["forge", "build"]
            artifacts_path = os.path.join(repo_path, 'out') # 예상 아티팩트 경로
        elif framework == 'hardhat':
             clean_command = ["npx", "hardhat", "clean"]
             build_command = ["npx", "hardhat", "compile"]
             artifacts_path = os.path.join(repo_path, 'artifacts') # 예상 아티팩트 경로
        
        build_successful = False
        if build_command:
            # Clean 실행
            if clean_command:
                print(f"  > 빌드 아티팩트 정리: {' '.join(clean_command)}...")
                try:
                    clean_result = subprocess.run(clean_command, cwd=repo_path, capture_output=True, text=True, check=False, encoding='utf-8')
                    if clean_result.returncode != 0:
                         print(f"  ! 경고: '{' '.join(clean_command)}' 실행 중 오류 (코드: {clean_result.returncode}): {clean_result.stderr[:500]}...")
                    else:
                         print(f"  > '{' '.join(clean_command)}' 실행 성공.")
                except Exception as clean_e:
                     print(f"  ! 경고: '{' '.join(clean_command)}' 실행 중 예외 발생: {clean_e}")
            
            # Build 실행
            print(f"  > 네이티브 빌드 실행: {' '.join(build_command)}...")
            try:
                result = subprocess.run(build_command, cwd=repo_path, check=False)
                if result.returncode != 0:
                    err_msg = f"'{ ' '.join(build_command) }' 실행 오류 (코드: {result.returncode}). 터미널 출력을 확인하세요."
                    print(f"  ! {err_msg}")
                    analysis_errors.append(err_msg)
                    build_status = "build_failed"
                else:
                    print(f"\n  > '{ ' '.join(build_command) }' 실행 성공.")
                    build_successful = True
            except FileNotFoundError:
                err_msg = f"'{build_command[0]}' 명령을 찾을 수 없습니다. 설치되어 있고 PATH에 있는지 확인하세요."
                print(f"  ! {err_msg}")
                analysis_errors.append(err_msg)
                build_status = "tool_not_found"
            except Exception as e:
                err_msg = f"'{ ' '.join(build_command) }' 실행 중 예외 발생: {e}"
                print(f"  ! {err_msg}")
                analysis_errors.append(err_msg)
                build_status = "build_exception"
        else:
            print("  > 프레임워크가 unknown이거나 특정 빌드 명령어가 없어 네이티브 빌드를 건너뜁니다.")
            build_successful = True # 빌드 건너뛰어도 crytic-compile은 시도

        # 3. crytic-compile CLI 실행 (네이티브 빌드 성공 시)
        compile_successful = False
        if build_successful:
            print(f"  > crytic-compile CLI 실행: crytic-compile . ...")
            try:
                # crytic-compile 명령어 실행 (출력은 터미널에 표시됨)
                compile_cmd = ["crytic-compile", "."]
                 # 프레임워크 힌트 추가 (선택적이지만 권장)
                if framework != 'unknown':
                     compile_cmd.extend(["--compile-force-framework", framework])
                
                result = subprocess.run(compile_cmd, cwd=repo_path, check=False)
                if result.returncode != 0:
                    err_msg = f"'crytic-compile .' 실행 오류 (코드: {result.returncode}). 터미널 출력을 확인하세요."
                    print(f"  ! {err_msg}")
                    analysis_errors.append(err_msg)
                    build_status = "compile_failed" if build_status == "pending" or build_status == "success" else build_status
                else:
                    print(f"\n  > 'crytic-compile .' 실행 성공.")
                    compile_successful = True
                    build_status = "success" # 최종 성공 상태
            except FileNotFoundError:
                err_msg = "'crytic-compile' 명령을 찾을 수 없습니다. 설치되어 있고 PATH에 있는지 확인하세요."
                print(f"  ! {err_msg}")
                analysis_errors.append(err_msg)
                build_status = "tool_not_found"
            except Exception as e:
                err_msg = f"'crytic-compile .' 실행 중 예외 발생: {e}"
                print(f"  ! {err_msg}")
                analysis_errors.append(err_msg)
                build_status = "compile_exception" if build_status == "pending" or build_status == "success" else build_status
        else:
             print("  > 네이티브 빌드 실패로 crytic-compile CLI 실행을 건너뜁니다.")
             # build_status는 이미 설정됨

        # 4. 최종 결과 조합 (상세 정보 없이 상태 위주)
        analysis_result = {
            "framework": framework,
            "build_status": build_status,
            "artifacts_path": artifacts_path if build_status == "success" else None, # 성공 시에만 경로 유효
            # 상세 컨트랙트 목록, 컴파일러 버전 등은 여기서 얻을 수 없음
        }
        print(f"분석 환경 준비 완료: 상태 = {build_status}, 프레임워크 = {framework}")
        
        return {"repo_analysis": analysis_result, "error": "; ".join(analysis_errors) if analysis_errors else None}

    except Exception as e:
        err_msg = f"리포지토리 분석 환경 준비 중 치명적 오류 발생: {e}"
        print(f"  ! {err_msg}")
        analysis_errors.append(err_msg)
        return {"repo_analysis": {"build_status": "fatal_error"}, "error": "; ".join(analysis_errors)}

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

# 3. 그래프 정의 및 노드/엣지 추가
workflow = StateGraph(AuditState)

# 노드 추가
workflow.add_node("clone", clone_repository)
workflow.add_node("analyze_repo", analyze_repo_structure)

# 엣지 추가 (단순화된 워크플로우)
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

# 분석 후 -> 종료 (더 이상 다음 단계 없음)
workflow.add_edge("analyze_repo", END) # 분석 후 무조건 종료

# 4. 그래프 컴파일
app = workflow.compile()

# 5. 에이전트 실행 (예시)
if __name__ == "__main__":
    github_repo_url = input("감사할 GitHub 리포지토리 URL을 입력하세요: ") or "https://github.com/Uniswap/v4-core.git"
    # 상태 정의 축소에 따라 초기 상태 필드 조정 필요 (실제 사용 시)
    initial_state = AuditState(github_url=github_repo_url) # 축소된 AuditState 사용

    print("initial_state: ", initial_state)
    print("\n--- audit_agent start ---")

    final_state = None
    try:
        final_state = app.invoke(initial_state)

    except Exception as e:
        print(f"\n워크플로우 실행 중 예상치 못한 오류 발생: {e}")
        if final_state is None:
            print("초기 실행 단계에서 오류가 발생했을 수 있습니다.")
        else:
             print("\n오류 발생 시점의 상태:")
             import json
             print(json.dumps(final_state, indent=2, ensure_ascii=False))
    finally:
        print("\n--- 감사 에이전트 실행 완료 ---")

        if final_state:
            print("\nfinal_state:")
            # report 필드가 없으므로 repo_analysis 결과를 출력하거나 다른 정보 표시
            print(f"  리포지토리 경로: {final_state.get('local_repo_path')}")
            print(f"  분석 결과: {final_state.get('repo_analysis')}")
            if final_state.get("error"):
                print(f"  오류: {final_state['error']}") 