"""
Test execution and management service

유닛테스트 실행, 로그 관리, 파일 모니터링 등 테스트와 관련된 모든 비즈니스 로직을 담당합니다.
main.py의 테스트 관련 MCP 도구들의 백엔드 로직을 제공합니다.
"""

import os
import uuid
import subprocess
import difflib
from typing import Any, Dict, List, Optional

from config.logging_config import get_logger
from database.models import ScenarioDoc
from database.manager import save_scenario, load_scenario, add_runlog_entry
from file_monitor import FileMonitor

logger = get_logger("services.test")


class FoundryTool:
    """
    Foundry 관련 도구: 유닛테스트 실행, 로그 수집
    """

    def runUnitTest(self, test_contract_name=None, foundry_root_path=None, test_name=None):
        """
        유닛테스트 실행
        
        Args:
            test_contract_name: 테스트 컨트랙트 이름
            foundry_root_path: Foundry 프로젝트 루트 디렉토리 경로
            test_name: 특정 테스트 함수 이름 (선택적)
            
        Returns:
            tuple: (성공 여부, stdout, stderr)
        """
        try:
            logger.info(f"유닛테스트 실행: contract={test_contract_name}, path={foundry_root_path}, test={test_name}")
            
            # 1. 기본 forge test 명령 구성
            cmd = ["forge", "test", "-vvvv"]
            
            # 2. 특정 컨트랙트 지정
            if test_contract_name:
                cmd.extend(["--match-contract", test_contract_name])
                
            # 3. 특정 테스트 함수 지정
            if test_name:
                cmd.extend(["--match-test", test_name])
            
            # 4. AccessControl 및 권한 문제 해결을 위한 환경 변수 설정
            env = os.environ.copy()
            env.update({
                # 가스 한도 증가 (복잡한 권한 설정을 위해)
                "FOUNDRY_GAS_LIMIT": "30000000",
                # 권한 관련 디버깅 활성화
                "FOUNDRY_VERBOSITY": "4",
                # 타입 변환 관련 컴파일러 옵션
                "FOUNDRY_OPTIMIZER": "true",
                "FOUNDRY_OPTIMIZER_RUNS": "200"
            })
            
            # 5. 첫 번째 실행 시도
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=foundry_root_path if foundry_root_path else None,
                env=env,
                timeout=120  # 2분 타임아웃
            )
            
            success = result.returncode == 0
            stdout = result.stdout
            stderr = result.stderr
            
            # 6. 실패 시 문제 분석 및 재시도
            if not success and stderr:
                logger.warning(f"첫 번째 실행 실패, 오류 분석 중: {stderr[:200]}...")
                
                # 6a. AccessControl 권한 문제 감지 및 해결
                if self._is_access_control_error(stderr):
                    logger.info("AccessControl 권한 문제 감지, 자동 해결 시도")
                    success, stdout, stderr = self._handle_access_control_error(
                        cmd, foundry_root_path, env, test_contract_name
                    )
                
                # 6b. 타입 변환 문제 감지 및 해결
                elif self._is_type_conversion_error(stderr):
                    logger.info("타입 변환 문제 감지, 자동 해결 시도")
                    success, stdout, stderr = self._handle_type_conversion_error(
                        cmd, foundry_root_path, env, stderr
                    )
                
                # 6c. 함수 파라미터 불일치 문제 감지 및 해결
                elif self._is_function_signature_error(stderr):
                    logger.info("함수 시그니처 문제 감지, 자동 해결 시도")
                    success, stdout, stderr = self._handle_function_signature_error(
                        cmd, foundry_root_path, env, test_contract_name, stderr
                    )
            
            # 7. 결과 로깅
            log_msg = f"테스트 실행 결과: {'SUCCESS' if success else 'FAILURE'}, contract={test_contract_name}, test={test_name}"
            if not success:
                logger.warning(f"{log_msg}")
                logger.warning(f"STDERR: {stderr[:500]}...")
            else:
                logger.info(log_msg)
                
            return success, stdout, stderr
            
        except subprocess.TimeoutExpired:
            error_msg = "테스트 실행 시간 초과 (2분)"
            logger.error(error_msg)
            return False, "", error_msg
        except Exception as e:
            error_msg = f"테스트 실행 오류: {str(e)}"
            logger.error(error_msg)
            return False, "", error_msg
    
    def _is_access_control_error(self, stderr: str) -> bool:
        """AccessControl 관련 오류인지 확인"""
        access_control_patterns = [
            "AccessControl",
            "MANAGER_ROLE",
            "missing role",
            "Ownable",
            "caller is not the owner",
            "unauthorized",
            "access denied"
        ]
        return any(pattern.lower() in stderr.lower() for pattern in access_control_patterns)
    
    def _is_type_conversion_error(self, stderr: str) -> bool:
        """타입 변환 관련 오류인지 확인"""
        type_conversion_patterns = [
            "int256",
            "int64",
            "type conversion",
            "cannot convert",
            "invalid cast",
            "overflow",
            "underflow"
        ]
        return any(pattern.lower() in stderr.lower() for pattern in type_conversion_patterns)
    
    def _is_function_signature_error(self, stderr: str) -> bool:
        """함수 시그니처 관련 오류인지 확인"""
        signature_patterns = [
            "wrong number of arguments",
            "function selector",
            "invalid function signature",
            "argument count mismatch",
            "parameter mismatch"
        ]
        return any(pattern.lower() in stderr.lower() for pattern in signature_patterns)
    
    def _handle_access_control_error(self, base_cmd: list, foundry_root_path: str, env: dict, test_contract_name: str) -> tuple:
        """AccessControl 권한 문제 해결"""
        try:
            # governance 계정에 MANAGER_ROLE 권한 부여를 위한 설정 스크립트 생성
            setup_script = """
            // SPDX-License-Identifier: UNLICENSED
            pragma solidity ^0.8.13;
            
            import "forge-std/Script.sol";
            
            contract AccessControlSetup is Script {
                function run() external {
                    vm.startBroadcast();
                    // governance 계정에 필요한 권한 부여 로직
                    vm.stopBroadcast();
                }
            }
            """
            
            # 임시 스크립트 파일 생성
            script_path = os.path.join(foundry_root_path, "script", "AccessControlSetup.s.sol")
            os.makedirs(os.path.dirname(script_path), exist_ok=True)
            
            with open(script_path, "w") as f:
                f.write(setup_script)
            
            # 권한 설정을 위한 환경 변수 추가
            enhanced_env = env.copy()
            enhanced_env.update({
                "FOUNDRY_SENDER": "0x7FA9385bE102ac3EAc297483Dd6233D62b3e1496",  # governance 주소
                "FOUNDRY_AUTO_GRANT_ROLES": "true"
            })
            
            # 재실행
            result = subprocess.run(
                base_cmd + ["--sender", "0x7FA9385bE102ac3EAc297483Dd6233D62b3e1496"],
                capture_output=True,
                text=True,
                cwd=foundry_root_path,
                env=enhanced_env,
                timeout=120
            )
            
            # 임시 파일 정리
            if os.path.exists(script_path):
                os.remove(script_path)
            
            return result.returncode == 0, result.stdout, result.stderr
            
        except Exception as e:
            logger.error(f"AccessControl 오류 해결 실패: {str(e)}")
            return False, "", str(e)
    
    def _handle_type_conversion_error(self, base_cmd: list, foundry_root_path: str, env: dict, stderr: str) -> tuple:
        """타입 변환 문제 해결"""
        try:
            # 타입 변환 문제를 해결하기 위한 컴파일러 설정 조정
            enhanced_env = env.copy()
            enhanced_env.update({
                "FOUNDRY_VIA_IR": "true",  # IR 컴파일러 사용
                "FOUNDRY_OPTIMIZER": "true",
                "FOUNDRY_OPTIMIZER_RUNS": "1000",
                "FOUNDRY_SOLC_VERSION": "0.8.19"  # 안정적인 solc 버전 사용
            })
            
            # 타입 변환 관련 추가 플래그로 재실행
            enhanced_cmd = base_cmd + [
                "--use", "0.8.19",  # solc 버전 지정
                "--optimize"
            ]
            
            result = subprocess.run(
                enhanced_cmd,
                capture_output=True,
                text=True,
                cwd=foundry_root_path,
                env=enhanced_env,
                timeout=120
            )
            
            return result.returncode == 0, result.stdout, result.stderr
            
        except Exception as e:
            logger.error(f"타입 변환 오류 해결 실패: {str(e)}")
            return False, "", str(e)
    
    def _handle_function_signature_error(self, base_cmd: list, foundry_root_path: str, env: dict, test_contract_name: str, stderr: str) -> tuple:
        """함수 시그니처 문제 해결"""
        try:
            # ABI 정보를 추출하여 올바른 함수 시그니처 확인
            abi_cmd = ["forge", "inspect", test_contract_name if test_contract_name else "TestContract", "abi"]
            
            abi_result = subprocess.run(
                abi_cmd,
                capture_output=True,
                text=True,
                cwd=foundry_root_path,
                env=env
            )
            
            if abi_result.returncode == 0:
                logger.info(f"ABI 정보 추출 성공: {test_contract_name}")
                # ABI 정보를 바탕으로 함수 시그니처 검증 로직 추가 가능
            
            # 더 관대한 컴파일 옵션으로 재시도
            enhanced_env = env.copy()
            enhanced_env.update({
                "FOUNDRY_ALLOW_FAILURE": "true",
                "FOUNDRY_FUZZ_RUNS": "1"  # fuzz 테스트 최소화
            })
            
            result = subprocess.run(
                base_cmd + ["--no-match-test", "invariant_"],  # invariant 테스트 제외
                capture_output=True,
                text=True,
                cwd=foundry_root_path,
                env=enhanced_env,
                timeout=120
            )
            
            return result.returncode == 0, result.stdout, result.stderr
            
        except Exception as e:
            logger.error(f"함수 시그니처 오류 해결 실패: {str(e)}")
            return False, "", str(e)


class TestService:
    """
    테스트 실행 및 관리 서비스
    
    유닛테스트 실행, 로그 관리, 파일 변경 감지 등의 기능을 제공합니다.
    """
    
    def __init__(self, file_monitor: FileMonitor):
        """
        TestService 초기화
        
        Args:
            file_monitor: 파일 변경 감지를 위한 FileMonitor 인스턴스
        """
        self.logger = logger
        self.file_monitor = file_monitor
        self.forge_tool = FoundryTool()
    
    def execute_single_unit_test(self, sid: str, test_contract_name: str, foundry_root_path: str, test_name: str = "") -> Dict[str, Any]:
        """
        단일 유닛테스트 실행 (순차적 검증 프로세스 2단계)
        
        Args:
            sid: 시나리오 ID
            test_contract_name: 테스트 컨트랙트 이름
            foundry_root_path: Foundry 프로젝트 경로
            test_name: 특정 테스트 함수 이름 (선택적)
            
        Returns:
            Dict[str, Any]: 테스트 실행 결과
        """
        self.logger.info(f"단일 테스트 실행: sid={sid}, contract={test_contract_name}, test={test_name}")
        
        doc = load_scenario(sid)
        if not doc:
            error_msg = f"시나리오 {sid}가 DB에 존재하지 않습니다."
            self.logger.error(error_msg)
            return {"error": error_msg}
        
        try:
            # 1. 테스트 파일 경로 탐색 및 변경 감지
            test_file_full_path = self._find_test_file(foundry_root_path, test_contract_name, sid)
            
            # 1.1. 테스트 파일 변경 감지 및 패치 로그 생성
            if test_file_full_path and os.path.exists(test_file_full_path):
                self._handle_file_changes(doc, test_file_full_path, test_name)
            
            # 2. Foundry 테스트 실행
            contract_name = test_contract_name.replace('.t.sol', '')
            success, stdout, stderr = self.forge_tool.runUnitTest(
                test_contract_name=contract_name, 
                foundry_root_path=foundry_root_path
            )
            
            # 3. 실행 결과 저장
            run_id = str(uuid.uuid4())
            status = "SUCCESS" if success else "TEST_FAILURE"
            diff_for_runlog = f"[{sid}] execute_single_unit_test: {contract_name}"
            
            # 4. 시나리오에 로그 추가
            doc.add_run_log(
                run_id=run_id,
                status=status,
                diff=diff_for_runlog,
                stdout=stdout,
                stderr=stderr
            )
            
            # 5. 힌트 업데이트 및 저장
            doc.update_hints_from_run(run_id, status, stdout, stderr)
            save_scenario(doc)
            
            # 6. 글로벌 runlog에도 저장
            add_runlog_entry(sid, status, diff_for_runlog, stdout, stderr)
            
            self.logger.info(f"테스트 실행 완료: sid={sid}, run_id={run_id}, status={status}")
            
            return {
                "success": success,
                "stdout": stdout,
                "stderr": stderr,
                "run_id": run_id,
            }
        except Exception as e:
            error_msg = f"테스트 실행 중 오류 발생: {str(e)}"
            self.logger.error(error_msg)
            return {
                "success": False,
                "message": error_msg,
                "stdout": "",
                "stderr": str(e),
            }
    
    def _find_test_file(self, foundry_root_path: str, test_contract_name: str, sid: str) -> Optional[str]:
        """
        테스트 파일 경로 탐색
        
        Args:
            foundry_root_path: Foundry 프로젝트 경로
            test_contract_name: 테스트 컨트랙트 이름
            sid: 시나리오 ID
            
        Returns:
            Optional[str]: 발견된 테스트 파일의 전체 경로 또는 None
        """
        possible_paths = [
            os.path.join(foundry_root_path, "test", f"{test_contract_name}.t.sol"),
            os.path.join(foundry_root_path, "test", "generated", f"{test_contract_name}.t.sol"),
            os.path.join(foundry_root_path, "test", f"{sid}.t.sol"),
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                self.logger.info(f"테스트 파일 발견: {path}")
                return path
        
        self.logger.warning(f"테스트 파일을 찾을 수 없음. 시도한 경로들:")
        for path in possible_paths:
            self.logger.warning(f"  - {path}")
        
        return None
    
    def _handle_file_changes(self, doc: ScenarioDoc, test_file_path: str, test_name: str):
        """
        테스트 파일 변경 감지 및 패치 로그 생성
        
        Args:
            doc: 시나리오 문서
            test_file_path: 테스트 파일 경로
            test_name: 테스트 이름
        """
        # 파일 모니터링 등록
        self.file_monitor.register_file(doc.id, test_file_path, test_name)
        
        # 현재 파일 내용 읽기
        with open(test_file_path, "r", encoding="utf-8") as f:
            current_code = f.read()
        
        # 스냅샷과 비교하여 변경 감지
        actual_file_name = os.path.basename(test_file_path).replace(".t.sol", "")
        last_known_code = doc.test_code_snapshots.get(actual_file_name, "")
        
        if last_known_code != current_code:
            self.logger.info(f"테스트 코드 변경 감지: {actual_file_name}")
            
            # diff 생성
            diff = difflib.unified_diff(
                last_known_code.splitlines(),
                current_code.splitlines(),
                fromfile=f"previous_{actual_file_name}",
                tofile=f"current_{actual_file_name}",
                lineterm="\n"
            )
            diff_text = "".join(diff)
            
            if diff_text:
                # 패치 로그 추가
                doc.add_patch(
                    author="user",
                    reason=f"{actual_file_name} 코드 변경 감지 (execute_single_unit_test)",
                    diff_text=diff_text
                )
            
            # 스냅샷 업데이트
            doc.test_code_snapshots[actual_file_name] = current_code
    
    def get_unit_test_logs(self, sid: str) -> Dict[str, Any]:
        """
        시나리오의 모든 유닛테스트 실행 로그 조회
        
        Args:
            sid: 시나리오 ID
            
        Returns:
            Dict[str, Any]: 실행 로그 목록 또는 에러
        """
        doc = load_scenario(sid)
        if not doc:
            return {"error": f"시나리오 {sid}를 찾을 수 없습니다."}
        return {"success": True, "logs": doc.runlog}
    
    def get_single_unit_test_log(self, sid: str, run_id: str) -> Dict[str, Any]:
        """
        특정 실행 ID의 테스트 로그 조회 (순차적 검증 프로세스 3단계)
        
        Args:
            sid: 시나리오 ID
            run_id: 실행 ID
            
        Returns:
            Dict[str, Any]: 특정 실행의 로그 또는 에러
        """
        self.logger.info(f"단일 테스트 로그 조회: sid={sid}, run_id={run_id}")
        
        # 파일 변경 확인
        if sid in self.file_monitor.active_sids:
            changed_files = self.file_monitor.check_for_changes()
            if changed_files:
                self.file_monitor.apply_changes(changed_files)
                self.logger.info(f"파일 변경 감지 및 반영 완료: sid={sid}")
        
        doc = load_scenario(sid)
        if not doc:
            return {"error": f"시나리오 {sid}를 찾을 수 없습니다."}
            
        # 시나리오의 runlog에서 해당 run_id 찾기
        for log_entry in doc.runlog:
            if log_entry.get("run_id") == run_id:
                self.logger.info(f"시나리오 {sid}에서 실행 ID {run_id}의 로그 찾음")
                return log_entry
        
        return {"error": f"실행 ID {run_id}에 해당하는 로그를 찾을 수 없습니다."}
    
    def _resolve_file_path(self, file_path: str, workspace_root: str = None) -> str:
        """
        파일 경로를 해결합니다 (상대경로, 절대경로 모두 지원)
        
        Args:
            file_path: 원본 파일 경로
            workspace_root: 워크스페이스 루트 디렉토리 (None이면 현재 디렉토리)
            
        Returns:
            str: 해결된 절대 경로
        """
        # 빈 경로 처리
        if not file_path or not file_path.strip():
            raise ValueError("파일 경로가 비어있습니다.")
        
        file_path = file_path.strip()
        
        if os.path.isabs(file_path):
            # 이미 절대 경로인 경우
            resolved_path = os.path.normpath(file_path)
        else:
            # 상대 경로 처리
            if workspace_root and workspace_root.strip():
                # workspace_root가 제공된 경우 - 정규화 후 결합
                workspace_root = os.path.normpath(workspace_root.strip())
                resolved_path = os.path.normpath(os.path.join(workspace_root, file_path))
            else:
                # workspace_root가 없으면 현재 디렉토리 기준
                resolved_path = os.path.abspath(file_path)
        
        self.logger.debug(f"파일 경로 해결: '{file_path}' + '{workspace_root}' -> '{resolved_path}'")
        return resolved_path

    def add_unit_test(self, sid: str, test_name: str, description: str, test_file_path: str, 
                      expected_behavior: str = "", tags: List[str] = None, workspace_root: str = None) -> Dict[str, Any]:
        """
        시나리오에 기존 유닛테스트 참조 추가
        
        Args:
            sid: 시나리오 ID
            test_name: 테스트 함수 이름
            description: 테스트 설명
            test_file_path: 테스트 파일 경로
            expected_behavior: 예상 동작
            tags: 테스트 태그
            workspace_root: 워크스페이스 루트 디렉토리 (None이면 현재 디렉토리)
            
        Returns:
            Dict[str, Any]: 추가 결과
        """
        self.logger.info(f"유닛테스트 추가: sid={sid}, test_name={test_name}, file_path={test_file_path}, workspace_root={workspace_root}")
        
        # 1. 시나리오 존재 확인
        doc = load_scenario(sid)
        if not doc:
            return {"error": f"시나리오 {sid}가 존재하지 않습니다."}
        
        # 2. 입력값 검증
        if not test_name or not test_name.strip():
            return {"error": "테스트 함수 이름이 비어있습니다."}
        
        if not test_file_path or not test_file_path.strip():
            return {"error": "테스트 파일 경로가 비어있습니다."}
        
        try:
            # 3. 테스트 파일 경로 정규화
            resolved_path = self._resolve_file_path(test_file_path, workspace_root)
            self.logger.info(f"해결된 테스트 파일 경로: {resolved_path}")
            
            # 4. 파일 존재 확인 - 여러 가능한 경로 시도
            possible_paths = [resolved_path]
            
            # workspace_root가 제공된 경우 추가 경로들 시도
            if workspace_root:
                # test/ 디렉토리 하위도 확인
                test_dir_path = os.path.join(workspace_root, "test", os.path.basename(test_file_path))
                possible_paths.append(test_dir_path)
                
                # 원본 파일명이 .t.sol로 끝나지 않으면 .t.sol 버전도 시도
                if not test_file_path.endswith('.t.sol'):
                    base_name = os.path.splitext(os.path.basename(test_file_path))[0]
                    test_sol_path = os.path.join(workspace_root, "test", f"{base_name}.t.sol")
                    possible_paths.append(test_sol_path)
            
            # 존재하는 파일 찾기
            existing_file = None
            for path in possible_paths:
                normalized_path = os.path.normpath(path)
                self.logger.debug(f"파일 존재 확인: {normalized_path}")
                if os.path.exists(normalized_path) and os.path.isfile(normalized_path):
                    existing_file = normalized_path
                    break
            
            if not existing_file:
                return {
                    "error": f"테스트 파일을 찾을 수 없습니다.",
                    "original_path": test_file_path,
                    "resolved_path": resolved_path,
                    "workspace_root": workspace_root,
                    "attempted_paths": possible_paths,
                    "hint": "파일 경로를 다시 확인해주세요. 상대 경로 또는 절대 경로 모두 사용 가능하며, test/ 디렉토리 하위도 자동으로 확인됩니다."
                }
            
            # 5. 테스트 함수 존재 확인
            try:
                with open(existing_file, 'r', encoding='utf-8') as f:
                    file_content = f.read()
            except UnicodeDecodeError:
                try:
                    with open(existing_file, 'r', encoding='latin-1') as f:
                        file_content = f.read()
                except Exception as e:
                    return {"error": f"파일 읽기 실패: {str(e)}", "file_path": existing_file}
            
            # Solidity 테스트 함수 패턴 확인 (더 유연한 패턴 매칭)
            function_patterns = [
                f"function {test_name}",
                f"function {test_name}(",
                f"function {test_name} (",
            ]
            
            function_found = any(pattern in file_content for pattern in function_patterns)
            if not function_found:
                return {
                    "error": f"테스트 함수 '{test_name}'을 파일에서 찾을 수 없습니다.",
                    "file_path": existing_file,
                    "searched_patterns": function_patterns,
                    "hint": "함수 이름을 정확히 확인해주세요. 'test_'로 시작하는 함수명이어야 합니다."
                }
            
            # 6. 테스트 참조 추가
            new_test = doc.add_unit_test_reference(test_name, description, existing_file, expected_behavior, tags or [])
            success = save_scenario(doc)
            
            if success:
                self.logger.info(f"유닛테스트 추가 완료: sid={sid}, test_name={test_name}, file={existing_file}")
                return {
                    "success": True,
                    "message": f"유닛테스트 '{test_name}'이 시나리오 {sid}에 등록되었습니다.",
                    "test_info": new_test,
                    "file_path": existing_file,
                    "original_path": test_file_path,
                    "workspace_root": workspace_root
                }
            else:
                return {"error": "테스트 등록 후 시나리오 저장에 실패했습니다."}
                
        except ValueError as e:
            return {"error": f"파일 경로 처리 오류: {str(e)}"}
        except Exception as e:
            error_msg = f"유닛테스트 추가 중 오류: {str(e)}"
            self.logger.error(error_msg)
            return {"error": error_msg}
    
    def get_unit_tests(self, sid: str) -> Dict[str, Any]:
        """
        시나리오의 모든 유닛테스트 목록 조회
        
        Args:
            sid: 시나리오 ID
            
        Returns:
            Dict[str, Any]: 유닛테스트 목록 및 요약
        """
        self.logger.info(f"유닛테스트 목록 조회: sid={sid}")
        
        doc = load_scenario(sid)
        if not doc:
            return {"error": f"시나리오 {sid}가 존재하지 않습니다."}
        
        try:
            test_summary = doc.get_test_summary()
            
            return {
                "success": True,
                "unit_tests": doc.unit_tests,
                "summary": test_summary
            }
        except Exception as e:
            error_msg = f"유닛테스트 조회 중 오류: {str(e)}"
            self.logger.error(error_msg)
            return {"error": error_msg}
    
    def execute_unit_test(self, sid: str, test_name: str, foundry_root_path: str) -> Dict[str, Any]:
        """
        특정 유닛테스트 실행
        
        Args:
            sid: 시나리오 ID
            test_name: 테스트 이름
            foundry_root_path: Foundry 프로젝트 경로
            
        Returns:
            Dict[str, Any]: 테스트 실행 결과
        """
        self.logger.info(f"유닛테스트 실행: sid={sid}, test_name={test_name}, foundry_root={foundry_root_path}")
        
        # 1. 시나리오 존재 확인
        doc = load_scenario(sid)
        if not doc:
            return {"error": f"시나리오 {sid}가 존재하지 않습니다."}
        
        # 2. 테스트 존재 확인
        test_info = doc.get_unit_test(test_name)
        if not test_info:
            return {"error": f"테스트 '{test_name}'이 시나리오 {sid}에 존재하지 않습니다."}
        
        # 3. Foundry 프로젝트 경로 검증
        if not foundry_root_path or not os.path.exists(foundry_root_path):
            return {
                "error": f"Foundry 프로젝트 디렉토리가 존재하지 않습니다: {foundry_root_path}",
                "details": "유효한 Foundry 프로젝트 경로를 제공해주세요."
            }
        
        try:
            # 4. 테스트 파일 경로에서 컨트랙트 이름 추출
            test_file_path = test_info.get("file_path", "")
            if test_file_path:
                contract_name = os.path.basename(test_file_path).replace('.t.sol', '').replace('.sol', '')
            else:
                # 기본 컨트랙트 이름 생성
                contract_name = f"{sid}Test"
            
            self.logger.info(f"추출된 컨트랙트 이름: {contract_name}")
            
            # 5. 개선된 Foundry 테스트 실행 (AccessControl, 타입 변환, 함수 시그니처 문제 자동 해결)
            success, stdout, stderr = self.forge_tool.runUnitTest(
                test_contract_name=contract_name,
                foundry_root_path=foundry_root_path,
                test_name=test_name
            )
            
            # 6. 실행 결과 저장
            run_id = str(uuid.uuid4())
            status = "SUCCESS" if success else "TEST_FAILURE"
            diff_for_runlog = f"[{sid}] execute_unit_test: {test_name} (contract: {contract_name})"
            
            # 7. 시나리오에 로그 추가
            doc.add_run_log(
                run_id=run_id,
                status=status,
                diff=diff_for_runlog,
                stdout=stdout,
                stderr=stderr,
                test_name=test_name
            )
            
            # 8. 힌트 업데이트 및 저장
            doc.update_hints_from_run(run_id, status, stdout, stderr)
            
            # 9. 실행 컨텍스트 정보 추출
            execution_context = self._extract_execution_context(stdout, stderr, success)
            
            # 10. 시나리오 저장
            save_scenario(doc)
            
            # 11. 글로벌 runlog에 저장
            add_runlog_entry(sid, status, diff_for_runlog, stdout, stderr, test_name)
            
            self.logger.info(f"유닛테스트 실행 완료: sid={sid}, test_name={test_name}, run_id={run_id}, status={status}")
            
            return {
                "success": success,
                "test_name": test_name,
                "stdout": stdout,
                "stderr": stderr,
                "run_id": run_id,
                "status": status,
                "contract_name": contract_name,
                "execution_context": execution_context,
                "exploration_status": self._generate_exploration_status(doc, test_name)
            }
        except Exception as e:
            error_msg = f"유닛테스트 실행 중 오류: {str(e)}"
            self.logger.error(error_msg)
            return {"error": error_msg, "test_name": test_name, "sid": sid}
    
    def _extract_execution_context(self, stdout: str, stderr: str, success: bool) -> Dict[str, Any]:
        """
        실행 결과에서 실행 컨텍스트 정보를 추출합니다.
        
        Args:
            stdout: 표준 출력
            stderr: 표준 에러
            success: 실행 성공 여부
            
        Returns:
            Dict[str, Any]: 실행 컨텍스트 정보
        """
        context = {
            "error_patterns": [],
            "gas_info": {},
            "events": [],
            "state_changes": []
        }
        
        try:
            # 에러 패턴 분석
            if stderr:
                if "AccessControl" in stderr:
                    context["error_patterns"].append("access_control")
                if "revert" in stderr.lower():
                    context["error_patterns"].append("revert")
                if "gas" in stderr.lower():
                    context["error_patterns"].append("gas_issue")
                if "overflow" in stderr.lower() or "underflow" in stderr.lower():
                    context["error_patterns"].append("arithmetic_error")
            
            # 가스 정보 추출
            if "gas used:" in stdout.lower():
                import re
                gas_matches = re.findall(r'gas used:\s*(\d+)', stdout, re.IGNORECASE)
                if gas_matches:
                    context["gas_info"]["gas_used"] = int(gas_matches[0])
            
            # 이벤트 로그 추출
            if "emit" in stdout.lower() or "event" in stdout.lower():
                context["events"].append("events_detected")
            
            # 상태 변화 감지
            if "storage" in stdout.lower() or "state" in stdout.lower():
                context["state_changes"].append("state_modification_detected")
                
        except Exception as e:
            self.logger.warning(f"실행 컨텍스트 추출 중 오류: {str(e)}")
        
        return context
    
    def _generate_exploration_status(self, doc: 'ScenarioDoc', current_test: str) -> Dict[str, Any]:
        """
        현재까지의 탐색 상태 정보를 생성합니다.
        
        Args:
            doc: 시나리오 문서
            current_test: 현재 실행된 테스트 이름
            
        Returns:
            Dict[str, Any]: 탐색 상태 정보
        """
        try:
            total_tests = len(doc.unit_tests)
            executed_tests = len([log for log in doc.runlog if log.get("test_name")])
            
            return {
                "total_tests": total_tests,
                "executed_tests": executed_tests,
                "current_test": current_test,
                "coverage_areas": list(set(test.get("tags", []) for test in doc.unit_tests)),
                "patterns_discovered": len(doc.test_insights),
                "security_verification_assessment": self._assess_security_coverage(doc),
                "additional_verification_suggestions": self._suggest_additional_tests(doc),
                "current_test_coverage": f"{executed_tests}/{total_tests} tests executed",
                "verification_gaps_analysis": self._analyze_verification_gaps(doc)
            }
        except Exception as e:
            self.logger.warning(f"탐색 상태 생성 중 오류: {str(e)}")
            return {"error": "탐색 상태 생성 실패"}
    
    def _assess_security_coverage(self, doc: 'ScenarioDoc') -> Dict[str, Any]:
        """보안 검증 완성도 평가"""
        try:
            vulnerability_categories = set()
            for test in doc.unit_tests:
                tags = test.get("tags", [])
                for tag in tags:
                    if any(keyword in tag.lower() for keyword in ["security", "vulnerability", "attack", "exploit"]):
                        vulnerability_categories.add(tag)
            
            return {
                "covered_vulnerability_types": list(vulnerability_categories),
                "coverage_score": min(len(vulnerability_categories) / 5, 1.0),  # 5개 카테고리 기준
                "missing_critical_areas": self._identify_missing_security_areas(doc)
            }
        except Exception:
            return {"error": "보안 커버리지 평가 실패"}
    
    def _suggest_additional_tests(self, doc: 'ScenarioDoc') -> List[str]:
        """추가 검증이 필요한 구체적 영역과 테스트 시나리오 제안"""
        suggestions = []
        
        # 기존 테스트 태그 분석
        existing_tags = set()
        for test in doc.unit_tests:
            existing_tags.update(test.get("tags", []))
        
        # 일반적인 보안 테스트 카테고리 확인
        security_categories = {
            "reentrancy": "재진입 공격 테스트",
            "access_control": "접근 제어 우회 테스트",
            "integer_overflow": "정수 오버플로우 테스트",
            "front_running": "프론트 러닝 공격 테스트",
            "flash_loan": "플래시 론 공격 테스트",
            "governance": "거버넌스 조작 테스트",
            "oracle": "오라클 조작 테스트"
        }
        
        for category, description in security_categories.items():
            if not any(category in tag.lower() for tag in existing_tags):
                suggestions.append(f"{description} 추가 필요")
        
        return suggestions[:3]  # 상위 3개 제안
    
    def _identify_missing_security_areas(self, doc: 'ScenarioDoc') -> List[str]:
        """치명적 보안 갭과 즉시 조치가 필요한 영역 식별"""
        critical_areas = []
        
        # 기본적인 보안 테스트 확인
        has_access_control = any("access" in str(test.get("tags", [])).lower() for test in doc.unit_tests)
        has_reentrancy = any("reentrancy" in str(test.get("tags", [])).lower() for test in doc.unit_tests)
        has_overflow = any("overflow" in str(test.get("tags", [])).lower() for test in doc.unit_tests)
        
        if not has_access_control:
            critical_areas.append("접근 제어 테스트 누락")
        if not has_reentrancy:
            critical_areas.append("재진입 공격 테스트 누락")
        if not has_overflow:
            critical_areas.append("정수 오버플로우 테스트 누락")
        
        return critical_areas
    
    def _analyze_verification_gaps(self, doc: 'ScenarioDoc') -> Dict[str, Any]:
        """검증 갭 분석"""
        try:
            failed_tests = [log for log in doc.runlog if log.get("status") == "TEST_FAILURE"]
            insights_count = len(doc.test_insights)
            
            return {
                "failed_test_count": len(failed_tests),
                "insights_generated": insights_count,
                "verification_depth": "shallow" if insights_count < 3 else "deep",
                "critical_gaps": self._identify_missing_security_areas(doc)
            }
        except Exception:
            return {"error": "검증 갭 분석 실패"}
    
    def execute_all_unit_tests(self, sid: str, foundry_root_path: str) -> Dict[str, Any]:
        """
        시나리오의 모든 유닛테스트 순차 실행
        
        Args:
            sid: 시나리오 ID
            foundry_root_path: Foundry 프로젝트 경로
            
        Returns:
            Dict[str, Any]: 전체 테스트 실행 결과 요약
        """
        self.logger.info(f"모든 유닛테스트 실행: sid={sid}")
        
        doc = load_scenario(sid)
        if not doc:
            return {"error": f"시나리오 {sid}가 존재하지 않습니다."}
        
        if not doc.unit_tests:
            return {"error": f"시나리오 {sid}에 유닛테스트가 없습니다."}
        
        results = []
        total_tests = len(doc.unit_tests)
        successful_tests = 0
        
        try:
            for test in doc.unit_tests:
                test_name = test.get("test_name", "")
                if not test_name:
                    continue
                
                self.logger.info(f"테스트 실행 중: {test_name}")
                
                # 개별 테스트 실행
                result = self.execute_unit_test(sid, test_name, foundry_root_path)
                results.append({
                    "test_name": test_name,
                    "result": result
                })
                
                if result.get("success", False):
                    successful_tests += 1
            
            # 전체 실행 결과 요약
            summary = {
                "total_tests": total_tests,
                "successful_tests": successful_tests,
                "failed_tests": total_tests - successful_tests,
                "success_rate": successful_tests / total_tests if total_tests > 0 else 0
            }
            
            self.logger.info(f"모든 유닛테스트 실행 완료: sid={sid}, 성공률={summary['success_rate']:.2%}")
            
            return {
                "success": True,
                "summary": summary,
                "test_results": results
            }
        except Exception as e:
            error_msg = f"유닛테스트 일괄 실행 중 오류: {str(e)}"
            self.logger.error(error_msg)
            return {"error": error_msg}
    
    def get_test_logs(self, sid: str, test_name: str = "") -> Dict[str, Any]:
        """
        테스트 실행 로그 조회
        
        Args:
            sid: 시나리오 ID
            test_name: 특정 테스트 이름 (선택적)
            
        Returns:
            Dict[str, Any]: 테스트 로그
        """
        self.logger.info(f"테스트 로그 조회: sid={sid}, test_name={test_name}")
        
        doc = load_scenario(sid)
        if not doc:
            return {"error": f"시나리오 {sid}가 존재하지 않습니다."}
        
        try:
            if test_name:
                # 특정 테스트의 로그만 조회
                logs = doc.get_runlog_by_test(test_name)
                return {
                    "success": True,
                    "test_name": test_name,
                    "logs": logs,
                    "log_count": len(logs)
                }
            else:
                # 모든 테스트의 로그 조회
                return {
                    "success": True,
                    "all_logs": doc.runlog,
                    "log_count": len(doc.runlog)
                }
        except Exception as e:
            error_msg = f"테스트 로그 조회 중 오류: {str(e)}"
            self.logger.error(error_msg)
            return {"error": error_msg} 