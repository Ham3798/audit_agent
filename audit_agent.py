import operator
import os
import shutil
import subprocess
import tempfile
import argparse
from typing import Annotated, List, TypedDict, Union
import json

from langgraph.graph import StateGraph, END
from git import Repo
from crytic_compile import CryticCompile, InvalidCompilation

# 1. 확장된 감사 상태 정의
class AuditState(TypedDict):
    """확장된 감사 프로세스의 상태를 나타냅니다."""
    github_url: str          # 감사 대상 GitHub URL
    local_repo_path: str | None = None # 클론된 로컬 리포지토리 경로
    repo_analysis: dict | None = None  # 리포지토리 구조 분석 결과 (컨트랙트, 프레임워크 등)
    error: str | None = None               # 프로세스 중 발생한 오류

# 2. 워크플로우 노드 함수 정의
def clone_repository(state: AuditState) -> dict:
    """GitHub 리포지토리를 지정된 로컬 디렉토리('./audit_repo')에 클론하거나, 이미 존재하면 스킵/정리합니다."""
    target_dir = "./audit_repo"
    print(f"--- 리포지토리 확인/클론 시작: {state['github_url']} -> {target_dir} ---")

    if os.path.exists(target_dir):
        print(f"디렉토리 '{target_dir}'가 이미 존재합니다.")
        try:
             repo = Repo(target_dir)
             # 원격 URL 비교 (origin이 존재하고 URL이 하나 이상일 때)
             if repo.remotes and hasattr(repo.remotes, 'origin') and repo.remotes.origin.urls:
                 origin_urls = list(repo.remotes.origin.urls)
                 if state['github_url'] not in origin_urls:
                     raise ValueError(f"기존 디렉토리의 remote URL ({origin_urls})이 요청된 URL ({state['github_url']})과 다릅니다.")
                 print("  > 기존 리포지토리 URL 일치 확인.")
                 # 선택적: git pull 등 추가 작업 가능
                 return {"local_repo_path": target_dir, "error": None}
             else:
                  print("  ! 경고: 기존 디렉토리에 유효한 'origin' remote가 없습니다. 디렉토리를 삭제하고 다시 클론합니다.")
                  raise ValueError("Invalid git repository in existing directory")

        except Exception as e:
             print(f"  ! 기존 리포지토리 검증/사용 중 오류: {e}")
             print("  > 기존 디렉토리를 삭제하고 새로 클론합니다.")
             try:
                 shutil.rmtree(target_dir)
             except Exception as rm_e:
                 print(f"  ! 기존 디렉토리 삭제 중 오류: {rm_e}")
                 return {"local_repo_path": None, "error": f"Failed to clean up existing directory: {rm_e}"}
             # 클론 로직으로 진행

    print(f"디렉토리 '{target_dir}' 생성 및 클론 시작...")
    try:
        Repo.clone_from(state['github_url'], target_dir)
        print(f"리포지토리가 '{target_dir}'에 성공적으로 클론되었습니다.")
        return {"local_repo_path": target_dir, "error": None}
    except Exception as e:
        print(f"  ! 리포지토리 클론 중 오류 발생: {e}")
        if os.path.exists(target_dir):
             try:
                 shutil.rmtree(target_dir)
                 print(f"  > 클론 실패 후 디렉토리 '{target_dir}' 정리 완료.")
             except Exception as rm_e:
                 print(f"  ! 클론 실패 후 디렉토리 정리 중 오류: {rm_e}")
        return {"local_repo_path": None, "error": f"Failed to clone repository: {e}"}


def analyze_repo_structure(state: AuditState) -> dict:
    """crytic-compile 라이브러리를 사용하여 리포지토리를 분석하고 컴파일합니다. 자동 감지만 시도하고 실패 시 종료합니다."""
    print("--- 리포지토리 분석 및 컴파일 시작 (crytic-compile Library - 자동 감지 전용) ---")
    repo_path = state.get("local_repo_path")
    if not repo_path or not os.path.isdir(repo_path):
        return {"error": "Repository path not valid or not found."}

    # 프레임워크 힌트는 더 이상 컴파일에 사용하지 않지만, 로깅/보고용으로 남겨둘 수 있음
    framework_hint = "unknown"
    analysis_errors = []
    compile_status = "pending"
    compile_instance = None
    detected_framework = None
    artifacts_path = None
    all_contract_names = set() # 모든 컨트랙트 이름을 저장할 집합

    try:
        # 1. 프레임워크 식별 (정보 제공 목적)
        print("  > 프레임워크 식별 (정보 제공 목적)...")
        ignore_dirs = {".git", "node_modules", "lib", "cache", "out", "build"} # 무시할 디렉토리
        for root, dirs, files in os.walk(repo_path):
            dirs[:] = [d for d in dirs if d not in ignore_dirs] # 탐색 제외
            path_parts = set(os.path.normpath(root).split(os.sep))
            if ignore_dirs.intersection(path_parts):
                continue

            for file in files:
                if file == "hardhat.config.js" or file == "hardhat.config.ts":
                    framework_hint = "hardhat"
                    break
                elif file == "foundry.toml":
                    framework_hint = "foundry"
                    break
            if framework_hint != "unknown":
                break
        print(f"  > 식별된 프레임워크 힌트: {framework_hint}")


        # 2. crytic-compile 라이브러리 실행 (자동 감지만 시도)
        print(f"  > crytic-compile 라이브러리 실행 시도 (자동 감지, 대상: {repo_path})...")
        try:
            compile_instance = CryticCompile(target=repo_path) # compile_force_framework 제거
            compile_status = "success"
            print(f"\n  > crytic-compile 자동 감지 및 컴파일 성공.")

            # 성공 시 정보 추출
            try:
                # 라이브러리가 실제로 사용/감지한 프레임워크 확인 시도
                if hasattr(compile_instance, 'platform') and compile_instance.platform:
                    detected_framework = compile_instance.platform.NAME
                elif compile_instance.compilation_units:
                    first_unit = list(compile_instance.compilation_units.values())[0]
                    if hasattr(first_unit, 'platform') and first_unit.platform:
                         detected_framework = first_unit.platform.NAME
                # 감지 실패 시 None 유지
                print(f"  > 라이브러리가 감지/사용한 프레임워크: {detected_framework if detected_framework else '감지 불가'}")

                # 아티팩트 경로 설정
                actual_framework = detected_framework or framework_hint # 보고 및 경로 설정용
                if actual_framework == 'foundry':
                    artifacts_path = os.path.join(repo_path, 'out')
                elif actual_framework == 'hardhat':
                     artifacts_path = os.path.join(repo_path, 'artifacts')
                # 다른 프레임워크 경로 추가

                # 모든 컴파일 유닛에서 컨트랙트 이름 추출 (수정된 로직)
                if compile_instance and compile_instance.compilation_units:
                    for unit in compile_instance.compilation_units.values():
                        # source_units 딕셔너리를 순회
                        if hasattr(unit, 'source_units') and unit.source_units:
                            for source_unit in unit.source_units.values():
                                # SourceUnit 객체에 contracts_names 속성이 있는지 확인
                                if hasattr(source_unit, 'contracts_names'):
                                    all_contract_names.update(source_unit.contracts_names)
                                else:
                                    # contracts_names 속성이 없다면 contracts (딕셔너리)의 키를 사용 시도
                                    if hasattr(source_unit, 'contracts'):
                                        all_contract_names.update(source_unit.contracts.keys())

                contract_names_list = sorted(list(all_contract_names)) # 정렬된 리스트로 변환
                print(f"  > 컴파일된 총 컨트랙트 수: {len(contract_names_list)}")
                print(f"  > 컴파일된 컨트랙트 (최대 5개): {contract_names_list[:5]}")

            except Exception as info_e:
                 print(f"  ! 컴파일 성공 후 정보 추출 중 오류: {info_e}")
                 analysis_errors.append(f"Error extracting info after compile: {info_e}")

        except InvalidCompilation as e:
            err_msg = f"CryticCompile 실패 (자동 감지): {e}"
            print(f"  ! {err_msg}")
            analysis_errors.append(err_msg)
            compile_status = "compile_failed"
            # 재시도 로직 제거됨
        except Exception as e_other:
             err_msg = f"CryticCompile 실행 중 예기치 않은 예외 발생: {e_other}"
             print(f"  ! {err_msg}")
             analysis_errors.append(err_msg)
             compile_status = "compile_exception"


        # 3. 최종 결과 조합
        analysis_result = {
            # 프레임워크는 성공 시 감지된 값, 실패 시 힌트 또는 unknown
            "framework": detected_framework if compile_status == "success" else framework_hint,
            "compile_status": compile_status,
            "artifacts_path": artifacts_path if compile_status == "success" else None,
            "contracts": sorted(list(all_contract_names)) if compile_status == "success" else [], # 성공 시에만 컨트랙트 목록 포함
        }
        print(f"\n분석 및 컴파일 시도 완료: 최종 상태 = {compile_status}, 프레임워크 = {analysis_result['framework']}")

        return {"repo_analysis": analysis_result, "error": "; ".join(analysis_errors) if analysis_errors else None}

    except Exception as e:
        err_msg = f"리포지토리 분석 및 컴파일 중 치명적 오류 발생: {e}"
        print(f"  ! {err_msg}")
        analysis_errors.append(err_msg)
        return {"repo_analysis": {"compile_status": "fatal_error", "framework": framework_hint}, "error": "; ".join(analysis_errors)}


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

# 3. 그래프 정의 및 노드/엣지 추가
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

# 4. 그래프 컴파일
app = workflow.compile()

# 5. 에이전트 실행 (예시)
if __name__ == "__main__":
    github_repo_url = input("감사할 GitHub 리포지토리 URL을 입력하세요: ") or "https://github.com/Uniswap/v4-core.git"
    initial_state = AuditState(github_url=github_repo_url)

    print("initial_state: ", initial_state)
    print("\n--- audit_agent start ---")

    final_state = None
    try:
        # invoke 대신 stream 사용 예시 (중간 상태 확인 가능)
        for event in app.stream(initial_state):
            event_type = list(event.keys())[0] # 이벤트 타입 (노드 이름 또는 'finish')
            event_data = event[event_type]
            print(f"\n[Event: {event_type}]")
            # 데이터가 딕셔너리 형태일 때만 상세 출력 (StateGraph 업데이트)
            if isinstance(event_data, dict):
                 serializable_data = {k: v for k, v in event_data.items() if isinstance(v, (str, int, float, bool, list, dict, type(None)))}
                 print("  Updated State:", json.dumps(serializable_data, indent=2, ensure_ascii=False))
            else:
                 print("  Data:", event_data)

            # 마지막 상태 저장 ('__end__' 키 확인)
            if event_type == '__end__': # LangGraph 최신 버전의 종료 이벤트 키
                 final_state = event_data # 최종 상태 전체를 저장
                 break

    except Exception as e:
        print(f"\n워크플로우 실행 중 예상치 못한 오류 발생: {e}")
        import traceback
        traceback.print_exc()

    finally:
        print("\n--- 감사 에이전트 실행 완료 ---")

        if final_state:
            print("\nFinal State:")
            print(f"  GitHub URL: {final_state.get('github_url')}")
            print(f"  Local Path: {final_state.get('local_repo_path')}")
            repo_analysis = final_state.get('repo_analysis')
            if repo_analysis:
                 print("  Repo Analysis:")
                 print(f"    Framework: {repo_analysis.get('framework')}")
                 print(f"    Compile Status: {repo_analysis.get('compile_status')}")
                 print(f"    Artifacts Path: {repo_analysis.get('artifacts_path')}")
                 # 컴파일 성공 시 컨트랙트 목록 출력
                 if repo_analysis.get('compile_status') == 'success' and 'contracts' in repo_analysis:
                     print(f"    Compiled Contracts ({len(repo_analysis['contracts'])}): {repo_analysis['contracts'][:10]}...") # 최대 10개만 출력
            if final_state.get("error"):
                print(f"  Error: {final_state['error']}")
        else:
            print("최종 상태를 가져올 수 없습니다.")