"""
File handling utilities

파일 처리, 경로 관리, 파일 시스템 작업 등의 유틸리티 함수들을 제공합니다.
"""

import os
import glob
from typing import List, Optional, Tuple

from config.logging_config import get_logger

logger = get_logger("utils.file")


class FileUtils:
    """
    파일 처리 관련 유틸리티 클래스
    
    주요 기능:
    - 파일 존재 확인
    - 경로 탐색
    - 파일 읽기/쓰기
    - 디렉토리 관리
    """
    
    @staticmethod
    def find_test_file(foundry_root_path: str, test_contract_name: str, sid: str) -> Optional[str]:
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
                logger.info(f"테스트 파일 발견: {path}")
                return path
        
        logger.warning(f"테스트 파일을 찾을 수 없음. 시도한 경로들:")
        for path in possible_paths:
            logger.warning(f"  - {path}")
        
        return None
    
    @staticmethod
    def ensure_directory_exists(directory_path: str) -> bool:
        """
        디렉토리가 없으면 생성
        
        Args:
            directory_path: 생성할 디렉토리 경로
            
        Returns:
            bool: 생성 성공 여부
        """
        try:
            os.makedirs(directory_path, exist_ok=True)
            return True
        except Exception as e:
            logger.error(f"디렉토리 생성 실패: {directory_path} - {str(e)}")
            return False
    
    @staticmethod
    def read_file_safe(file_path: str, encoding: str = "utf-8") -> Tuple[bool, str]:
        """
        안전한 파일 읽기
        
        Args:
            file_path: 파일 경로
            encoding: 인코딩 (기본값: utf-8)
            
        Returns:
            Tuple[bool, str]: (성공 여부, 파일 내용 또는 에러 메시지)
        """
        try:
            with open(file_path, "r", encoding=encoding) as f:
                content = f.read()
            logger.debug(f"파일 읽기 성공: {file_path}")
            return True, content
        except Exception as e:
            error_msg = f"파일 읽기 실패: {file_path} - {str(e)}"
            logger.error(error_msg)
            return False, error_msg
    
    @staticmethod
    def write_file_safe(file_path: str, content: str, encoding: str = "utf-8") -> Tuple[bool, str]:
        """
        안전한 파일 쓰기
        
        Args:
            file_path: 파일 경로
            content: 파일 내용
            encoding: 인코딩 (기본값: utf-8)
            
        Returns:
            Tuple[bool, str]: (성공 여부, 성공 메시지 또는 에러 메시지)
        """
        try:
            # 디렉토리가 없으면 생성
            directory = os.path.dirname(file_path)
            if directory:
                FileUtils.ensure_directory_exists(directory)
            
            with open(file_path, "w", encoding=encoding) as f:
                f.write(content)
            
            success_msg = f"파일 쓰기 성공: {file_path}"
            logger.info(success_msg)
            return True, success_msg
        except Exception as e:
            error_msg = f"파일 쓰기 실패: {file_path} - {str(e)}"
            logger.error(error_msg)
            return False, error_msg
    
    @staticmethod
    def find_files_by_pattern(directory: str, pattern: str) -> List[str]:
        """
        패턴으로 파일 찾기
        
        Args:
            directory: 검색할 디렉토리
            pattern: 파일 패턴 (예: "*.yaml")
            
        Returns:
            List[str]: 발견된 파일 경로 목록
        """
        try:
            search_pattern = os.path.join(directory, pattern)
            files = glob.glob(search_pattern)
            logger.debug(f"패턴 '{pattern}'으로 {len(files)}개 파일 발견: {directory}")
            return files
        except Exception as e:
            logger.error(f"파일 패턴 검색 실패: {directory}/{pattern} - {str(e)}")
            return []
    
    @staticmethod
    def get_file_extension(file_path: str) -> str:
        """
        파일 확장자 추출
        
        Args:
            file_path: 파일 경로
            
        Returns:
            str: 파일 확장자 (점 포함, 예: ".sol")
        """
        return os.path.splitext(file_path)[1]
    
    @staticmethod
    def get_filename_without_extension(file_path: str) -> str:
        """
        확장자 없는 파일명 추출
        
        Args:
            file_path: 파일 경로
            
        Returns:
            str: 확장자 없는 파일명
        """
        basename = os.path.basename(file_path)
        return os.path.splitext(basename)[0]
    
    @staticmethod
    def is_solidity_file(file_path: str) -> bool:
        """
        Solidity 파일인지 확인
        
        Args:
            file_path: 파일 경로
            
        Returns:
            bool: Solidity 파일이면 True
        """
        return FileUtils.get_file_extension(file_path).lower() == ".sol"
    
    @staticmethod
    def is_test_file(file_path: str) -> bool:
        """
        테스트 파일인지 확인
        
        Args:
            file_path: 파일 경로
            
        Returns:
            bool: 테스트 파일이면 True (*.t.sol 패턴)
        """
        filename = os.path.basename(file_path)
        return filename.endswith(".t.sol") 