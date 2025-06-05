"""
Foundry related utilities

Foundry 테스트 실행 및 관련 유틸리티 함수들을 제공합니다.
main.py에서 분리된 FoundryTool 클래스와 Foundry 관련 헬퍼 함수들을 포함합니다.
"""

import subprocess
from typing import Tuple

from config.logging_config import get_logger

logger = get_logger("utils.foundry")


class FoundryUtils:
    """
    Foundry 관련 유틸리티 클래스
    
    주요 기능:
    - run_unit_test: Foundry forge test 명령어 실행
    - 기타 Foundry 관련 유틸리티 함수들
    """
    
    @staticmethod
    def run_unit_test(test_contract_name: str = None, foundry_root_path: str = None) -> Tuple[bool, str, str]:
        """
        유닛테스트 실행
        
        Args:
            test_contract_name: 테스트 컨트랙트 이름 (없으면 전체 테스트 실행)
            foundry_root_path: Foundry 프로젝트 루트 디렉토리 경로
            
        Returns:
            Tuple[bool, str, str]: (성공 여부, stdout, stderr)
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
    
    @staticmethod
    def run_specific_test(test_contract_name: str, test_function_name: str, foundry_root_path: str = None) -> Tuple[bool, str, str]:
        """
        특정 테스트 함수 실행
        
        Args:
            test_contract_name: 테스트 컨트랙트 이름
            test_function_name: 테스트 함수 이름
            foundry_root_path: Foundry 프로젝트 루트 디렉토리 경로
            
        Returns:
            Tuple[bool, str, str]: (성공 여부, stdout, stderr)
        """
        try:
            logger.info(f"특정 테스트 실행: contract={test_contract_name}, function={test_function_name}")
            cmd = ["forge", "test", "-vvvv", "--match-contract", test_contract_name, "--match-test", test_function_name]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=foundry_root_path if foundry_root_path else None
            )
            
            success = result.returncode == 0
            
            # 결과 로깅
            log_msg = f"특정 테스트 실행 결과: {'SUCCESS' if success else 'FAILURE'}, {test_contract_name}::{test_function_name}"
            if not success:
                logger.warning(f"{log_msg}, stderr={result.stderr[:200]}...")
            else:
                logger.info(log_msg)
                
            return success, result.stdout, result.stderr
            
        except Exception as e:
            error_msg = f"특정 테스트 실행 오류: {str(e)}"
            logger.error(error_msg)
            return False, "", error_msg
    
    @staticmethod
    def check_foundry_installation() -> bool:
        """
        Foundry 설치 여부 확인
        
        Returns:
            bool: Foundry가 설치되어 있으면 True
        """
        try:
            result = subprocess.run(
                ["forge", "--version"],
                capture_output=True,
                text=True
            )
            return result.returncode == 0
        except Exception:
            return False
    
    @staticmethod
    def compile_contracts(foundry_root_path: str = None) -> Tuple[bool, str, str]:
        """
        컨트랙트 컴파일
        
        Args:
            foundry_root_path: Foundry 프로젝트 루트 디렉토리 경로
            
        Returns:
            Tuple[bool, str, str]: (성공 여부, stdout, stderr)
        """
        try:
            logger.info(f"컨트랙트 컴파일: path={foundry_root_path}")
            cmd = ["forge", "build"]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=foundry_root_path if foundry_root_path else None
            )
            
            success = result.returncode == 0
            
            if not success:
                logger.warning(f"컴파일 실패: stderr={result.stderr[:200]}...")
            else:
                logger.info("컴파일 성공")
                
            return success, result.stdout, result.stderr
            
        except Exception as e:
            error_msg = f"컴파일 오류: {str(e)}"
            logger.error(error_msg)
            return False, "", error_msg


# 하위 호환성을 위한 기존 클래스명 유지
class FoundryTool(FoundryUtils):
    """
    하위 호환성을 위한 기존 FoundryTool 클래스
    
    @deprecated: FoundryUtils를 사용하세요
    """
    
    def runUnitTest(self, test_contract_name=None, foundry_root_path=None):
        """
        하위 호환성을 위한 메서드
        
        @deprecated: FoundryUtils.run_unit_test()를 사용하세요
        """
        return self.run_unit_test(test_contract_name, foundry_root_path) 