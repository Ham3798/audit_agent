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

    def runUnitTest(self, test_contract_name=None, foundry_root_path=None):
        """
        유닛테스트 실행
        
        Args:
            test_contract_name: 테스트 컨트랙트 이름
            foundry_root_path: Foundry 프로젝트 루트 디렉토리 경로
            
        Returns:
            tuple: (성공 여부, stdout, stderr)
        """
        try:
            logger.info(f"유닛테스트 실행: contract={test_contract_name}, path={foundry_root_path}")
            cmd = ["forge", "test", "-vvvv"]
            if test_contract_name:
                cmd.extend(["--match-contract", test_contract_name])
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=foundry_root_path if foundry_root_path else None
            )
            
            success = result.returncode == 0
            
            # 결과 로깅
            log_msg = f"테스트 실행 결과: {'SUCCESS' if success else 'FAILURE'}, contract={test_contract_name}"
            if not success:
                logger.warning(f"{log_msg}, stderr={result.stderr[:200]}...")
            else:
                logger.info(log_msg)
                
            return success, result.stdout, result.stderr
            
        except Exception as e:
            error_msg = f"테스트 실행 오류: {str(e)}"
            logger.error(error_msg)
            return False, "", error_msg


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
        if os.path.isabs(file_path):
            # 이미 절대 경로인 경우
            return file_path
        
        # 상대 경로 처리
        if workspace_root:
            # workspace_root 기준으로 해결
            resolved_path = os.path.join(workspace_root, file_path)
        else:
            # 현재 디렉토리 기준으로 해결
            resolved_path = os.path.abspath(file_path)
        
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
        self.logger.info(f"유닛테스트 추가: sid={sid}, test_name={test_name}")
        
        doc = load_scenario(sid)
        if not doc:
            return {"error": f"시나리오 {sid}가 존재하지 않습니다."}
        
        # 테스트 파일 경로 정규화 및 존재 확인
        test_file_path = self._resolve_file_path(test_file_path, workspace_root)
        
        if not os.path.exists(test_file_path):
            return {
                "error": f"테스트 파일이 존재하지 않습니다: {test_file_path}",
                "hint": "파일 경로를 다시 확인해주세요. 상대 경로 또는 절대 경로 모두 사용 가능합니다."
            }
        
        try:
            # 테스트 함수 존재 확인
            with open(test_file_path, 'r', encoding='utf-8') as f:
                file_content = f.read()
            
            if f"function {test_name}" not in file_content:
                return {"error": f"테스트 함수 '{test_name}'이 파일 {test_file_path}에서 찾을 수 없습니다."}
            
            # 테스트 참조 추가
            new_test = doc.add_unit_test_reference(test_name, description, test_file_path, expected_behavior, tags or [])
            save_scenario(doc)
            
            self.logger.info(f"유닛테스트 추가 완료: sid={sid}, test_name={test_name}")
            return {
                "success": True,
                "message": f"유닛테스트 '{test_name}'이 시나리오 {sid}에 등록되었습니다.",
                "test_info": new_test,
                "file_path": test_file_path
            }
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
        self.logger.info(f"유닛테스트 실행: sid={sid}, test_name={test_name}")
        
        doc = load_scenario(sid)
        if not doc:
            return {"error": f"시나리오 {sid}가 존재하지 않습니다."}
        
        # 테스트 존재 확인
        test_info = doc.get_unit_test(test_name)
        if not test_info:
            return {"error": f"테스트 '{test_name}'이 시나리오 {sid}에 존재하지 않습니다."}
        
        try:
            # Foundry 테스트 실행
            success, stdout, stderr = self.forge_tool.runUnitTest(
                test_contract_name=None,
                foundry_root_path=foundry_root_path
            )
            
            # 실행 결과 저장
            status = "SUCCESS" if success else "TEST_FAILURE"
            diff_for_runlog = f"[{sid}] execute_unit_test: {test_name}"
            run_id = str(uuid.uuid4())
            
            # 시나리오에 로그 추가
            doc.add_run_log(
                run_id=run_id,
                status=status,
                diff=diff_for_runlog,
                stdout=stdout,
                stderr=stderr,
                test_name=test_name
            )
            
            # 힌트 업데이트 및 저장
            doc.update_hints_from_run(run_id, status, stdout, stderr)
            save_scenario(doc)
            
            # 글로벌 runlog에 저장
            add_runlog_entry(sid, status, diff_for_runlog, stdout, stderr, test_name)
            
            self.logger.info(f"유닛테스트 실행 완료: sid={sid}, test_name={test_name}, run_id={run_id}")
            
            return {
                "success": success,
                "test_name": test_name,
                "stdout": stdout,
                "stderr": stderr,
                "run_id": run_id,
                "status": status
            }
        except Exception as e:
            error_msg = f"유닛테스트 실행 중 오류: {str(e)}"
            self.logger.error(error_msg)
            return {"error": error_msg}
    
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