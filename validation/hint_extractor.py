"""
Hint extractor for audit_agent test results

이 모듈은 테스트 실행 결과에서 유용한 힌트를 추출하는 기능을 제공합니다.
Forge 출력, Slither 분석 결과 등을 파싱하여 시나리오의 hints 섹션을 업데이트합니다.
"""

import re
from typing import Any, Dict, List, Optional

from config.logging_config import get_logger

logger = get_logger("validation")


class HintExtractor:
    """
    테스트 실행 결과에서 힌트를 추출하는 클래스
    
    Forge 출력, Slither 분석 결과 등을 파싱하여 시나리오에 유용한 힌트를 추출합니다.
    추출된 힌트는 시나리오의 hints 섹션에 저장됩니다.
    """
    
    def __init__(self):
        """HintExtractor 초기화"""
        self.logger = logger
    
    def extract_hints_from_results(self, scenario_data: Dict[str, Any], forge_output: str, slither_output: str = None) -> Dict[str, Any]:
        """
        테스트 실행 결과에서 힌트를 추출하여 시나리오에 업데이트합니다.
        
        Args:
            scenario_data: 시나리오 데이터 딕셔너리
            forge_output: Forge 테스트 출력 결과
            slither_output: Slither 분석 결과 (선택적)
            
        Returns:
            Dict[str, Any]: 업데이트된 시나리오 데이터
        """
        try:
            # hints 섹션 초기화
            self._initialize_hints_section(scenario_data)
            
            # Forge 출력 파싱
            if forge_output:
                self._extract_forge_hints(scenario_data, forge_output)
            
            # Slither 분석 결과 파싱
            if slither_output:
                self._extract_slither_hints(scenario_data, slither_output)
            
            # 힌트 정리 및 중복 제거
            self._cleanup_hints(scenario_data)
            
            hints = scenario_data["hints"]
            self.logger.info(f"힌트 추출 완료: runtime={len(hints['runtime'])}, compiler={len(hints['compiler'])}, gas={len(hints['gas'])}")
            return scenario_data
            
        except Exception as e:
            self.logger.error(f"힌트 추출 중 오류 발생: {e}")
            # 원본 시나리오 반환
            return scenario_data
    
    def _initialize_hints_section(self, scenario_data: Dict[str, Any]):
        """hints 섹션을 초기화합니다."""
        if "hints" not in scenario_data:
            scenario_data["hints"] = {}
        
        hints = scenario_data["hints"]
        if "runtime" not in hints:
            hints["runtime"] = {}
        if "compiler" not in hints:
            hints["compiler"] = {}
        if "gas" not in hints:
            hints["gas"] = {}
    
    def _extract_forge_hints(self, scenario_data: Dict[str, Any], forge_output: str):
        """Forge 출력에서 힌트를 추출합니다."""
        hints = scenario_data["hints"]
        
        # 1. 디코딩된 로그 추출
        decoded_logs = self._extract_decoded_logs(forge_output)
        if decoded_logs:
            hints["runtime"]["decoded_logs"] = decoded_logs
        
        # 2. Revert 정보 파싱
        revert_info = self._extract_revert_info(forge_output)
        if revert_info:
            hints["runtime"]["revert_info"] = revert_info
        
        # 3. Gas 사용량 추출
        gas_usage = self._extract_gas_usage(forge_output)
        if gas_usage:
            hints["gas"]["used"] = gas_usage
        
        # 4. 이벤트 로그 추출
        event_logs = self._extract_event_logs(forge_output)
        if event_logs:
            hints["runtime"]["event_logs"] = event_logs
        
        # 5. 컨트랙트 주소 추출
        contract_addresses = self._extract_contract_addresses(forge_output)
        if contract_addresses:
            hints["runtime"]["contract_addresses"] = contract_addresses
    
    def _extract_decoded_logs(self, forge_output: str) -> List[str]:
        """디코딩된 로그를 추출합니다."""
        decoded_logs = []
        
        for line in forge_output.splitlines():
            # CONSOLE 로그 추출
            if "CONSOLE:" in line:
                log_content = line.split("CONSOLE:", 1)[1].strip()
                decoded_logs.append(log_content)
            
            # console.log 패턴 추출
            elif "console.log" in line.lower():
                decoded_logs.append(f"CONSOLE_LOG: {line.strip()}")
        
        return decoded_logs
    
    def _extract_revert_info(self, forge_output: str) -> Optional[str]:
        """Revert 정보를 추출합니다."""
        revert_lines = []
        
        for line in forge_output.splitlines():
            if "Reverted" in line or "revert" in line.lower():
                revert_lines.append(line.strip())
        
        if revert_lines:
            return revert_lines[0]  # 첫 번째 revert 정보 반환
        
        return None
    
    def _extract_gas_usage(self, forge_output: str) -> Optional[int]:
        """Gas 사용량을 추출합니다."""
        for line in forge_output.splitlines():
            if "gas" in line.lower() and "used" in line.lower():
                # "gas used: 123456" 패턴 매칭
                gas_match = re.search(r"gas\s+used:\s+(\d+)", line.lower())
                if gas_match:
                    return int(gas_match.group(1))
                
                # "Gas used: 123456" 패턴 매칭
                gas_match = re.search(r"gas\s+used:\s*(\d+)", line, re.IGNORECASE)
                if gas_match:
                    return int(gas_match.group(1))
        
        return None
    
    def _extract_event_logs(self, forge_output: str) -> List[str]:
        """이벤트 로그를 추출합니다."""
        event_logs = []
        
        for line in forge_output.splitlines():
            # emit 키워드가 포함된 라인
            if "emit" in line.lower():
                event_logs.append(f"EVENT: {line.strip()}")
            
            # Event 패턴 매칭
            event_match = re.search(r"Event:\s*(.+)", line, re.IGNORECASE)
            if event_match:
                event_logs.append(f"EVENT: {event_match.group(1)}")
        
        return event_logs
    
    def _extract_contract_addresses(self, forge_output: str) -> Dict[str, str]:
        """컨트랙트 주소를 추출합니다."""
        addresses = {}
        
        for line in forge_output.splitlines():
            # "Contract deployed at: 0x123..." 패턴
            deploy_match = re.search(r"deployed\s+at:\s*(0x[a-fA-F0-9]{40})", line, re.IGNORECASE)
            if deploy_match:
                addresses["deployed"] = deploy_match.group(1)
            
            # "Address: 0x123..." 패턴
            addr_match = re.search(r"address:\s*(0x[a-fA-F0-9]{40})", line, re.IGNORECASE)
            if addr_match:
                addresses["address"] = addr_match.group(1)
        
        return addresses
    
    def _extract_slither_hints(self, scenario_data: Dict[str, Any], slither_output: str):
        """Slither 분석 결과에서 힌트를 추출합니다."""
        hints = scenario_data["hints"]
        
        compiler_errors = []
        compiler_warnings = []
        security_issues = []
        
        for line in slither_output.splitlines():
            line = line.strip()
            
            # 컴파일러 에러 추출
            if "Error:" in line or "error:" in line.lower():
                compiler_errors.append(line)
            
            # 컴파일러 경고 추출
            elif "Warning:" in line or "warning:" in line.lower():
                compiler_warnings.append(line)
            
            # 보안 이슈 추출
            elif any(keyword in line.lower() for keyword in ["reentrancy", "overflow", "underflow", "delegatecall"]):
                security_issues.append(line)
        
        if compiler_errors:
            hints["compiler"]["errors"] = compiler_errors
        
        if compiler_warnings:
            hints["compiler"]["warnings"] = compiler_warnings
        
        if security_issues:
            hints["compiler"]["security_issues"] = security_issues
    
    def _cleanup_hints(self, scenario_data: Dict[str, Any]):
        """힌트를 정리하고 중복을 제거합니다."""
        hints = scenario_data["hints"]
        
        # runtime 섹션 정리
        if "runtime" in hints:
            runtime = hints["runtime"]
            
            # decoded_logs 중복 제거
            if "decoded_logs" in runtime and isinstance(runtime["decoded_logs"], list):
                runtime["decoded_logs"] = list(set(runtime["decoded_logs"]))
            
            # event_logs 중복 제거
            if "event_logs" in runtime and isinstance(runtime["event_logs"], list):
                runtime["event_logs"] = list(set(runtime["event_logs"]))
        
        # compiler 섹션 정리
        if "compiler" in hints:
            compiler = hints["compiler"]
            
            # errors 중복 제거
            if "errors" in compiler and isinstance(compiler["errors"], list):
                compiler["errors"] = list(set(compiler["errors"]))
            
            # warnings 중복 제거
            if "warnings" in compiler and isinstance(compiler["warnings"], list):
                compiler["warnings"] = list(set(compiler["warnings"]))
    
    def extract_vulnerability_patterns(self, forge_output: str, slither_output: str = None) -> Dict[str, Any]:
        """
        취약점 패턴을 추출합니다.
        
        Args:
            forge_output: Forge 테스트 출력
            slither_output: Slither 분석 결과
            
        Returns:
            Dict[str, Any]: 추출된 취약점 패턴 정보
        """
        patterns = {
            "reentrancy": False,
            "overflow": False,
            "underflow": False,
            "access_control": False,
            "gas_issues": False,
            "custom_patterns": []
        }
        
        combined_output = forge_output + (slither_output or "")
        
        # 재진입 패턴 감지
        if any(keyword in combined_output.lower() for keyword in ["reentrancy", "reentrant", "call.value"]):
            patterns["reentrancy"] = True
        
        # 오버플로우/언더플로우 패턴 감지
        if any(keyword in combined_output.lower() for keyword in ["overflow", "underflow", "safeMath"]):
            patterns["overflow"] = True
            patterns["underflow"] = True
        
        # 접근 제어 패턴 감지
        if any(keyword in combined_output.lower() for keyword in ["onlyOwner", "require", "modifier", "access"]):
            patterns["access_control"] = True
        
        # 가스 관련 이슈 감지
        if any(keyword in combined_output.lower() for keyword in ["out of gas", "gas limit", "gas used"]):
            patterns["gas_issues"] = True
        
        return patterns


# 편의 함수 (기존 호환성 유지)
def extract_hints(scenario_data: Dict[str, Any], forge_output: str, slither_output: str = None) -> Dict[str, Any]:
    """
    테스트 실행 결과에서 힌트를 추출하는 편의 함수
    
    Args:
        scenario_data: 시나리오 데이터 딕셔너리
        forge_output: Forge 테스트 출력 결과
        slither_output: Slither 분석 결과 (선택적)
        
    Returns:
        Dict[str, Any]: 업데이트된 시나리오 데이터
    """
    extractor = HintExtractor()
    return extractor.extract_hints_from_results(scenario_data, forge_output, slither_output) 