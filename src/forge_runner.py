# src/forge_runner.py
import subprocess
import json
import os
import re # re 모듈 임포트 추가
from typing import Dict, List, Any, Optional

from .state import AuditState

def _parse_forge_json_output(output_lines: List[str]) -> List[Dict[str, Any]]:
    """Forge JSON 출력 스트림을 파싱하여 각 테스트 결과를 추출합니다."""
    test_results = []
    current_json_block = ""
    for line in output_lines:
        # JSON 블록은 { 로 시작해서 } 로 끝난다고 가정
        stripped_line = line.strip()
        if stripped_line.startswith('{'):
            current_json_block = stripped_line
        elif current_json_block: # 블록이 시작된 상태면 내용을 추가
            current_json_block += stripped_line
        
        if current_json_block and stripped_line.endswith('}'):
            try:
                # 완전한 JSON 블록 파싱 시도
                result = json.loads(current_json_block)
                
                # 예상되는 테스트 결과 구조인지 확인 (더 구체적인 확인 필요)
                # 예: result가 딕셔너리이고 test 파일 경로를 키로 가지는지 등
                # Foundry 버전에 따라 출력 형식이 다를 수 있으므로 주의
                # 간단히 딕셔너리인지, 그리고 특정 키(예: test_results)가 있는지 확인
                if isinstance(result, dict) and any(k.endswith('.sol') for k in result.keys()):
                     test_results.append(result)

            except json.JSONDecodeError:
                print(f"  ! JSON 파싱 경고 (블록 무시): {current_json_block}")
            finally:
                current_json_block = "" # 다음 블록을 위해 초기화

    # 파싱된 결과가 없는 경우, 전체 출력을 반환할 수도 있음 (디버깅용)
    if not test_results and output_lines:
         print("  ! 경고: 표준 JSON 라인 파싱 실패, 전체 출력에서 결과 추출 시도.")
         # TODO: 전체 stdout에서 결과 요약 및 실패를 추출하는 로직 추가 (복잡함)

    return test_results


def run_forge_mcp_tests(state: AuditState) -> Dict[str, Optional[Dict[str, Any]] | Optional[str]]:
    """생성된 MCP 테스트 파일을 실행하고 결과를 요약합니다."""
    print("--- MCP 테스트 실행 시작 (Forge) ---")
    repo_path = state.get("local_repo_path")
    generated_files = state.get("generated_test_files") # 생성된 파일 목록 (참고용으로 유지)

    if not repo_path:
        return {"error": "Local repository path not found for running tests."}
    if not generated_files: # 생성된 파일이 있는지 다시 확인
        print("  > 실행할 생성된 테스트 파일이 없습니다. 건너<0xEB><0x9C><0x84>니다.")
        return {"mcp_test_results": {"summary": {"total": 0, "passed": 0, "failed": 0, "notes":"No tests generated."}, "failures": []}}

    # 생성된 테스트가 있는 디렉토리 경로
    mcp_test_dir = os.path.join("test", "mcp_generated") # repo_path 기준 상대 경로
    mcp_test_dir_abs = os.path.join(repo_path, mcp_test_dir)

    if not os.path.isdir(mcp_test_dir_abs) or not any(f.endswith('.t.sol') for f in os.listdir(mcp_test_dir_abs)):
         print(f"  ! MCP 테스트 디렉토리({mcp_test_dir})가 없거나 테스트 파일이 없습니다. 건너<0xEB><0x9C><0x84>니다.")
         return {"mcp_test_results": {"summary": {"total": 0, "passed": 0, "failed": 0, "notes": "Test directory not found or empty."}, "failures": []}}

    # --match-path 대신 경로 인자로 디렉토리 지정 또는 --match-contract 사용
    # 방법 1: 테스트 디렉토리 경로를 직접 전달
    # command = ["forge", "test", mcp_test_dir, "-vv", "--json"]
    # 방법 2: --match-contract 사용 (더 명시적일 수 있음)
    command = ["forge", "test", "--match-contract", "MCPTest_", "-vv", "--json"] # MCPTest_ 접두사로 시작하는 모든 컨트랙트 실행


    print(f"  > 실행 명령어: {' '.join(command)}")

    results_summary = {"total": 0, "passed": 0, "failed": 0}
    failed_tests_details = []
    error_output: Optional[str] = None

    try:
        process = subprocess.Popen(command, cwd=repo_path, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8')

        raw_stdout_lines = []
        if process.stdout:
            for line in iter(process.stdout.readline, ''):
                # print(f"  [Forge STDOUT] {line.strip()}") # 너무 길어지므로 주석 처리
                raw_stdout_lines.append(line.strip())
            process.stdout.close()

        stderr_output = ""
        if process.stderr:
             stderr_output = process.stderr.read()
             if stderr_output and "Ran 0 tests" not in stderr_output: # 실제 에러만 출력
                 print("\n  --- Forge STDERR ---")
                 print(stderr_output)
                 print("  --------------------")
             process.stderr.close()

        process.wait()
        print(f"  > Forge 실행 완료 (Return Code: {process.returncode})")

        # Forge JSON 출력 파싱 (수정된 함수 사용)
        parsed_results = _parse_forge_json_output(raw_stdout_lines)

        # 결과 요약 및 실패 상세 정보 추출 (파싱 결과 기반)
        total_tests = 0
        passed_tests = 0
        for file_result in parsed_results:
             # 파일 경로가 키인 구조로 가정
             file_path = list(file_result.keys())[0]
             contract_results = file_result[file_path]
             for contract_name, tests in contract_results.items():
                 for test_name, details in tests.get("test_results", {}).items():
                     total_tests += 1
                     status = details.get("status", "Unknown")
                     if status == "Success":
                         passed_tests += 1
                     else:
                         failure_detail = {
                             "test_file": file_path,
                             "contract_name": contract_name,
                             "test_function": test_name,
                             "status": status,
                             "reason": details.get("reason"),
                             "decoded_logs": details.get("decoded_logs"),
                             "logs": details.get("logs"),
                             # TODO: trace 정보 파싱 추가 (필요 시)
                             # "trace": details.get("traces") # Foundry JSON 출력 확인 필요
                         }
                         failed_tests_details.append(failure_detail)

        results_summary["total"] = total_tests
        results_summary["passed"] = passed_tests
        results_summary["failed"] = total_tests - passed_tests


        if process.returncode != 0 and not failed_tests_details and total_tests == 0:
             # 테스트 실패는 없지만 0개 테스트 실행 및 0 아닌 종료 코드 (컴파일 오류 등)
             error_output = f"Forge process exited with code {process.returncode} and ran 0 tests. Possible compile error? Stderr: {stderr_output or 'N/A'}"
             print(f"  ! 오류: {error_output}")
        elif process.returncode != 0 and results_summary["failed"] == 0:
             # 테스트는 모두 성공했지만 0 아닌 종료 코드 (드문 경우)
             error_output = f"Forge process exited with code {process.returncode} but all tests passed. Stderr: {stderr_output or 'N/A'}"
             print(f"  ! 경고: {error_output}")


    except FileNotFoundError:
        error_output = "Forge command not found. Ensure Foundry is installed and in PATH."
        print(f"  ! 오류: {error_output}")
    except Exception as e:
        error_output = f"Error running Forge tests: {e}\nStderr: {stderr_output or 'N/A'}"
        print(f"  ! 오류: {error_output}")
        traceback.print_exc()

    final_results = {
        "summary": results_summary,
        "failures": failed_tests_details
    }

    print(f"--- MCP 테스트 실행 완료 (Total: {results_summary['total']}, Passed: {results_summary['passed']}, Failed: {results_summary['failed']}) ---")

    # 실패 시에도 error_output은 기록될 수 있음 (예: 프로세스 오류)
    return {"mcp_test_results": final_results, "error": state.get("error") or error_output} # 기존 에러 유지 + 새 에러 추가
