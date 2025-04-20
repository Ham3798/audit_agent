import operator
import os
import shutil
import subprocess
import tempfile
from typing import Annotated, List, TypedDict, Union

from langgraph.graph import StateGraph, END
from git import Repo
from crytic_compile import CryticCompile

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
    """프로젝트 빌드 후 crytic-compile 라이브러리로 구조 및 컴파일 정보를 분석합니다."""
    print("--- 리포지토리 구조 분석 시작 (Build + crytic-compile library) ---")
    repo_path = state.get("local_repo_path")
    if not repo_path or not os.path.isdir(repo_path):
        return {"error": "Repository path not valid or not found."}

    analysis_result = {}
    framework = "unknown"
    analysis_errors = [] # 오류 기록용 리스트 추가
    
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

        # 2. 네이티브 빌드 명령어 실행 (프레임워크 기반)
        build_command = None
        if framework == 'foundry':
            build_command = ["forge", "build"]
        elif framework == 'hardhat':
             # npx가 PATH에 있어야 함
             build_command = ["npx", "hardhat", "compile"]
        
        build_successful = False
        if build_command:
            print(f"  > 네이티브 빌드 실행: {' '.join(build_command)}...")
            try:
                # 빌드 명령어 실행 (실시간 출력 위해 capture_output 제거)
                # result = subprocess.run(build_command, cwd=repo_path, capture_output=True, text=True, check=False, encoding='utf-8')
                result = subprocess.run(build_command, cwd=repo_path, check=False) # stderr/stdout이 터미널에 직접 표시됨
                
                if result.returncode != 0:
                    # stderr가 캡처되지 않으므로 에러 메시지에서 제거
                    err_msg = f"'{ ' '.join(build_command) }' 실행 오류 (코드: {result.returncode}). 터미널 출력을 확인하세요."
                    print(f"  ! {err_msg}")
                    analysis_errors.append(err_msg)
                else:
                    print(f"\n  > '{ ' '.join(build_command) }' 실행 성공.") # 가독성을 위해 줄바꿈 추가
                    build_successful = True
            except FileNotFoundError:
                err_msg = f"'{build_command[0]}' 명령을 찾을 수 없습니다. 설치되어 있고 PATH에 있는지 확인하세요."
                print(f"  ! {err_msg}")
                analysis_errors.append(err_msg)
            except Exception as e:
                err_msg = f"'{ ' '.join(build_command) }' 실행 중 예외 발생: {e}"
                print(f"  ! {err_msg}")
                analysis_errors.append(err_msg)
        else:
            print("  > 프레임워크가 unknown이거나 특정 빌드 명령어가 없어 빌드를 건너니다.")
            # 빌드 과정이 없어도 crytic-compile은 시도해볼 수 있음
            build_successful = True 

        # 3. CryticCompile 실행 (빌드 성공 시)
        if build_successful:
            print(f"  > CryticCompile 초기화 (프레임워크: {framework})...")
            compile_kwargs = {}
            if framework != 'unknown':
                compile_kwargs['compile_force_framework'] = framework
            
            crytic_compile = CryticCompile(repo_path, **compile_kwargs)
            print("  > CryticCompile 분석 완료.")

            # 4. 분석 결과 추출
            contracts_summary = []
            compiler_versions = set()
            for unit_name, compilation_unit in crytic_compile.compilation_units.items():
                if hasattr(compilation_unit, 'compiler_version') and compilation_unit.compiler_version:
                     compiler_version_obj = compilation_unit.compiler_version
                     if hasattr(compiler_version_obj, 'version'):
                          compiler_versions.add(compiler_version_obj.version)
                     else:
                          compiler_versions.add(str(compiler_version_obj))
                
                if hasattr(compilation_unit, 'contracts') and compilation_unit.contracts:
                    for contract_object in compilation_unit.contracts:
                        if hasattr(contract_object, 'name'):
                            contract_name = contract_object.name
                            relative_path = os.path.relpath(unit_name, repo_path) if os.path.isabs(unit_name) else unit_name
                            contracts_summary.append({
                                "name": contract_name, 
                                "source_path": relative_path 
                            })
            
            artifacts_path = None
            if framework == 'foundry':
                artifacts_path = os.path.join(repo_path, 'out')
            elif framework == 'hardhat':
                 artifacts_path = os.path.join(repo_path, 'artifacts')
            potential_cache_path = os.path.join(repo_path, 'crytic-compile-cache')
            if artifacts_path is None and os.path.isdir(potential_cache_path):
                 artifacts_path = potential_cache_path
            
            analysis_result = {
                "contracts": sorted(contracts_summary, key=lambda x: x['source_path']),
                "framework": framework,
                "compiler_versions": sorted(list(compiler_versions)),
                "artifacts_path": artifacts_path
            }
            print(f"분석 완료: {len(contracts_summary)}개의 컨트랙트 발견, 프레임워크: {framework}")
            print(f"  > 사용된 컴파일러 버전: {analysis_result['compiler_versions']}")
            print(f"  > 아티팩트 경로 (추정): {artifacts_path}")
        else:
             print("  > 빌드 실패로 CryticCompile 분석을 건너니다.")
             # 빌드 실패 시 analysis_result는 비어있음

        # 최종 상태 반환 (오류 포함 가능)
        return {"repo_analysis": analysis_result, "error": "; ".join(analysis_errors) if analysis_errors else None}

    except Exception as e:
        # 전체 분석 프로세스 중 예외 발생
        err_msg = f"리포지토리 분석 중 치명적 오류 발생: {e}"
        print(f"  ! {err_msg}")
        # 기존 오류에 추가
        analysis_errors.append(err_msg)
        return {"repo_analysis": None, "error": "; ".join(analysis_errors)}

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

    print("\n--- 감사 에이전트 실행 시작 (단순화된 워크플로우) ---")
    final_state = None
    try:
        final_state = app.invoke(initial_state, {"recursion_limit": 5}) # 재귀 제한 감소

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
            print("\n최종 상태:")
            # report 필드가 없으므로 repo_analysis 결과를 출력하거나 다른 정보 표시
            print(f"  리포지토리 경로: {final_state.get('local_repo_path')}")
            print(f"  분석 결과: {final_state.get('repo_analysis')}")
            if final_state.get("error"):
                print(f"  오류: {final_state['error']}") 