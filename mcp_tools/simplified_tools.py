"""
Simplified MCP tools for streamlined workflow

복잡한 순차적 프로세스를 단순화한 통합 MCP 도구들입니다.
사용자 피드백을 바탕으로 핵심 기능만 남기고 사용성을 개선했습니다.
"""

from typing import Any, Dict, List, Optional
from mcp.server.fastmcp import FastMCP

from config.logging_config import get_logger
from services import ScenarioService, TestService, PocService
from file_monitor import FileMonitor

logger = get_logger("mcp_tools.simplified")


class SimplifiedMCPTools:
    """
    단순화된 MCP 도구 컬렉션
    
    핵심 워크플로우:
    1. 시나리오 등록
    2. 테스트 실행 & 검증  
    3. PoC 생성
    4. 결과 정리
    """
    
    def __init__(self):
        self.file_monitor = FileMonitor()
        self.scenario_service = ScenarioService()
        self.test_service = TestService(self.file_monitor)
        self.poc_service = PocService()
        self.logger = logger
    
    def register_tools(self, mcp_instance):
        """통합된 MCP 도구들을 등록합니다."""
        
        @mcp_instance.tool()
        async def quick_scenario_test(
            scenario_data: dict, 
            test_files: List[str], 
            foundry_root_path: str,
            workspace_root: str = None
        ) -> dict:
            """
            🚀 **원클릭 시나리오 검증: 올인원 워크플로우**
            
            시나리오 등록부터 테스트 실행, PoC 생성까지 한 번에 처리하는 통합 도구입니다.
            복잡한 순차적 프로세스를 제거하고 핵심 워크플로우만 제공합니다.
            
            Args:
                scenario_data: 시나리오 정보 (register_scenario와 동일 형식)
                test_files: 테스트 파일 경로 목록 (상대/절대 경로 모두 지원)
                foundry_root_path: Foundry 프로젝트 루트 경로
                workspace_root: 워크스페이스 루트 경로 (상대경로 해결용)
            
            Returns:
                dict: 전체 워크플로우 결과
                - scenario_registered: 시나리오 등록 성공 여부
                - tests_executed: 실행된 테스트 목록
                - poc_generated: 생성된 PoC 정보
                - summary: 전체 결과 요약
            """
            self.logger.info(f"[quick_scenario_test] 통합 워크플로우 시작: {scenario_data.get('meta', {}).get('id')}")
            
            result = {
                "scenario_registered": False,
                "tests_executed": [],
                "poc_generated": None,
                "summary": {},
                "errors": []
            }
            
            try:
                # 1. 시나리오 등록
                scenario_result = self.scenario_service.register_scenario(scenario_data)
                if scenario_result.get("success"):
                    result["scenario_registered"] = True
                    sid = scenario_data["meta"]["id"]
                    self.logger.info(f"✅ 시나리오 등록 성공: {sid}")
                else:
                    result["errors"].append(f"시나리오 등록 실패: {scenario_result}")
                    return result
                
                # 2. 테스트 파일들 등록 및 실행
                successful_tests = 0
                for i, test_file in enumerate(test_files):
                    test_name = f"test_{i+1}"
                    
                    # 테스트 등록
                    add_result = self.test_service.add_unit_test(
                        sid=sid,
                        test_name=test_name,
                        description=f"Auto-added test from {test_file}",
                        test_file_path=test_file,
                        workspace_root=workspace_root
                    )
                    
                    if add_result.get("success"):
                        # 테스트 실행
                        exec_result = self.test_service.execute_unit_test(
                            sid=sid,
                            test_name=test_name,
                            foundry_root_path=foundry_root_path
                        )
                        
                        result["tests_executed"].append({
                            "test_file": test_file,
                            "test_name": test_name,
                            "success": exec_result.get("success", False),
                            "run_id": exec_result.get("run_id"),
                            "summary": exec_result.get("stdout", "")[:200] + "..." if exec_result.get("stdout") else ""
                        })
                        
                        if exec_result.get("success"):
                            successful_tests += 1
                    else:
                        result["errors"].append(f"테스트 등록 실패 {test_file}: {add_result}")
                
                # 3. PoC 생성 (테스트가 하나라도 성공한 경우)
                if successful_tests > 0:
                    poc_result = self.poc_service.generate_poc_code(
                        sid=sid,
                        foundry_root_path=foundry_root_path,
                        poc_type="contract"
                    )
                    
                    if poc_result.get("success"):
                        result["poc_generated"] = {
                            "file_path": poc_result.get("file_path"),
                            "poc_type": poc_result.get("poc_type"),
                            "success": True
                        }
                    else:
                        result["errors"].append(f"PoC 생성 실패: {poc_result}")
                
                # 4. 결과 요약
                result["summary"] = {
                    "total_tests": len(test_files),
                    "successful_tests": successful_tests,
                    "failed_tests": len(test_files) - successful_tests,
                    "poc_generated": result["poc_generated"] is not None,
                    "overall_success": successful_tests > 0 and len(result["errors"]) == 0
                }
                
                return result
                
            except Exception as e:
                self.logger.error(f"통합 워크플로우 오류: {str(e)}")
                result["errors"].append(f"예상치 못한 오류: {str(e)}")
                return result
        
        @mcp_instance.tool()
        async def run_test(test_file: str, test_function: str = None, foundry_root: str = ".") -> dict:
            """
            🧪 **간단한 테스트 실행**
            
            복잡한 등록 과정 없이 테스트 파일을 바로 실행합니다.
            
            Args:
                test_file: 테스트 파일 경로
                test_function: 특정 테스트 함수 (None이면 전체 실행)
                foundry_root: Foundry 프로젝트 루트
            
            Returns:
                dict: 테스트 실행 결과
            """
            self.logger.info(f"[run_test] 간단 테스트 실행: {test_file}")
            
            # FoundryTool 직접 사용
            from services.test_service import FoundryTool
            forge_tool = FoundryTool()
            
            success, stdout, stderr = forge_tool.runUnitTest(
                test_contract_name=test_file.replace('.t.sol', '').split('/')[-1],
                foundry_root_path=foundry_root
            )
            
            return {
                "success": success,
                "stdout": stdout,
                "stderr": stderr,
                "test_file": test_file,
                "test_function": test_function
            }
        
        @mcp_instance.tool()
        async def get_scenario_summary(sid: str) -> dict:
            """
            📋 **시나리오 요약 보기**
            
            시나리오의 전체 상태를 한눈에 볼 수 있는 요약 정보를 제공합니다.
            
            Args:
                sid: 시나리오 ID
            
            Returns:
                dict: 시나리오 요약 정보
            """
            self.logger.info(f"[get_scenario_summary] 시나리오 요약: {sid}")
            
            scenario = self.scenario_service.get_scenario(sid)
            if not scenario:
                return {"error": f"시나리오 {sid}를 찾을 수 없습니다."}
            
            # 테스트 요약
            test_summary = self.test_service.get_unit_tests(sid)
            
            # 실행 로그 요약  
            logs = self.test_service.get_unit_test_logs(sid)
            
            return {
                "scenario_info": {
                    "id": scenario.get("meta", {}).get("id"),
                    "title": scenario.get("meta", {}).get("title"),
                    "category": scenario.get("meta", {}).get("category"),
                    "severity": scenario.get("meta", {}).get("severity")
                },
                "test_summary": test_summary,
                "execution_summary": {
                    "total_runs": len(logs) if isinstance(logs, list) else 0,
                    "recent_activity": logs[-3:] if isinstance(logs, list) and len(logs) > 0 else []
                },
                "status": "active" if test_summary.get("unit_tests") else "new"
            }
        
        @mcp_instance.tool()
        async def validate_poc(sid: str, foundry_root: str) -> dict:
            """
            ✅ **빠른 PoC 검증**
            
            생성된 PoC가 실제로 컴파일되고 실행되는지 빠르게 검증합니다.
            
            Args:
                sid: 시나리오 ID
                foundry_root: Foundry 프로젝트 루트
            
            Returns:
                dict: PoC 검증 결과
            """
            self.logger.info(f"[validate_poc] PoC 검증: {sid}")
            
            # PoC 파일 찾기
            import os
            possible_paths = [
                os.path.join(foundry_root, "src", f"{sid}.sol"),
                os.path.join(foundry_root, "script", f"{sid}.s.sol"),
                os.path.join(foundry_root, "test", f"{sid}_Exploit.t.sol")
            ]
            
            poc_file = None
            for path in possible_paths:
                if os.path.exists(path):
                    poc_file = path
                    break
            
            if not poc_file:
                return {
                    "success": False,
                    "error": "PoC 파일을 찾을 수 없습니다.",
                    "searched_paths": possible_paths
                }
            
            # 컴파일 테스트
            import subprocess
            try:
                result = subprocess.run(
                    ["forge", "build"],
                    capture_output=True,
                    text=True,
                    cwd=foundry_root
                )
                
                compile_success = result.returncode == 0
                
                return {
                    "success": compile_success,
                    "poc_file": poc_file,
                    "compile_output": result.stdout if compile_success else result.stderr,
                    "status": "verified" if compile_success else "compile_error"
                }
                
            except Exception as e:
                return {
                    "success": False,
                    "error": f"컴파일 테스트 실패: {str(e)}",
                    "poc_file": poc_file
                } 