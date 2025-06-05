"""
String processing utilities

문자열 처리, 포맷팅, 변환 등의 유틸리티 함수들을 제공합니다.
"""

import re
from typing import List, Optional

from config.logging_config import get_logger

logger = get_logger("utils.string")


class StringUtils:
    """
    문자열 처리 관련 유틸리티 클래스
    
    주요 기능:
    - 문자열 포맷팅
    - 패턴 추출
    - 문자열 변환
    - 검증
    """
    
    @staticmethod
    def truncate_string(text: str, max_length: int = 200, suffix: str = "...") -> str:
        """
        문자열 잘라내기
        
        Args:
            text: 원본 문자열
            max_length: 최대 길이
            suffix: 잘렸을 때 추가할 접미사
            
        Returns:
            str: 잘라낸 문자열
        """
        if len(text) <= max_length:
            return text
        return text[:max_length] + suffix
    
    @staticmethod
    def extract_contract_name(file_path: str) -> str:
        """
        파일 경로에서 컨트랙트 이름 추출
        
        Args:
            file_path: 파일 경로
            
        Returns:
            str: 컨트랙트 이름 (확장자 제거)
        """
        import os
        filename = os.path.basename(file_path)
        # .t.sol 또는 .sol 확장자 제거
        if filename.endswith(".t.sol"):
            return filename[:-6]  # ".t.sol" 제거
        elif filename.endswith(".sol"):
            return filename[:-4]  # ".sol" 제거
        return filename
    
    @staticmethod
    def extract_function_names(solidity_code: str) -> List[str]:
        """
        Solidity 코드에서 함수 이름 추출
        
        Args:
            solidity_code: Solidity 코드 문자열
            
        Returns:
            List[str]: 추출된 함수 이름 목록
        """
        pattern = r'function\s+([a-zA-Z_][a-zA-Z0-9_]*)'
        matches = re.findall(pattern, solidity_code)
        return matches
    
    @staticmethod
    def extract_test_function_names(solidity_code: str) -> List[str]:
        """
        Solidity 코드에서 테스트 함수 이름 추출 (test_로 시작하는 함수들)
        
        Args:
            solidity_code: Solidity 코드 문자열
            
        Returns:
            List[str]: 추출된 테스트 함수 이름 목록
        """
        pattern = r'function\s+(test[a-zA-Z0-9_]*)'
        matches = re.findall(pattern, solidity_code)
        return matches
    
    @staticmethod
    def extract_import_statements(solidity_code: str) -> List[str]:
        """
        Solidity 코드에서 import 문 추출
        
        Args:
            solidity_code: Solidity 코드 문자열
            
        Returns:
            List[str]: 추출된 import 문 목록
        """
        pattern = r'import\s+.*?;'
        matches = re.findall(pattern, solidity_code, re.MULTILINE)
        return matches
    
    @staticmethod
    def clean_whitespace(text: str) -> str:
        """
        불필요한 공백 정리
        
        Args:
            text: 원본 문자열
            
        Returns:
            str: 공백이 정리된 문자열
        """
        # 여러 공백을 하나로 통합
        text = re.sub(r'\s+', ' ', text)
        # 앞뒤 공백 제거
        return text.strip()
    
    @staticmethod
    def format_error_message(error: str, context: str = "") -> str:
        """
        에러 메시지 포맷팅
        
        Args:
            error: 에러 메시지
            context: 추가 컨텍스트 정보
            
        Returns:
            str: 포맷팅된 에러 메시지
        """
        if context:
            return f"[{context}] {error}"
        return error
    
    @staticmethod
    def extract_severity_level(text: str) -> Optional[str]:
        """
        텍스트에서 심각도 레벨 추출
        
        Args:
            text: 분석할 텍스트
            
        Returns:
            Optional[str]: 추출된 심각도 레벨 또는 None
        """
        text_lower = text.lower()
        
        if any(word in text_lower for word in ["critical", "high", "severe"]):
            return "critical"
        elif any(word in text_lower for word in ["medium", "moderate"]):
            return "medium"
        elif any(word in text_lower for word in ["low", "minor", "info"]):
            return "low"
        
        return None
    
    @staticmethod
    def extract_keywords(text: str, min_length: int = 3) -> List[str]:
        """
        텍스트에서 키워드 추출
        
        Args:
            text: 분석할 텍스트
            min_length: 최소 키워드 길이
            
        Returns:
            List[str]: 추출된 키워드 목록
        """
        # 알파벳 단어만 추출
        words = re.findall(r'[a-zA-Z]+', text.lower())
        
        # 최소 길이 이상의 단어만 필터링
        keywords = [word for word in words if len(word) >= min_length]
        
        # 중복 제거하면서 순서 유지
        seen = set()
        unique_keywords = []
        for keyword in keywords:
            if keyword not in seen:
                seen.add(keyword)
                unique_keywords.append(keyword)
        
        return unique_keywords
    
    @staticmethod
    def is_valid_identifier(name: str) -> bool:
        """
        유효한 식별자인지 확인 (변수명, 함수명 등)
        
        Args:
            name: 확인할 이름
            
        Returns:
            bool: 유효한 식별자이면 True
        """
        # 영문자나 언더스코어로 시작하고, 영문자, 숫자, 언더스코어만 포함
        pattern = r'^[a-zA-Z_][a-zA-Z0-9_]*$'
        return bool(re.match(pattern, name))
    
    @staticmethod
    def camel_to_snake(camel_str: str) -> str:
        """
        CamelCase를 snake_case로 변환
        
        Args:
            camel_str: CamelCase 문자열
            
        Returns:
            str: snake_case 문자열
        """
        # CamelCase를 snake_case로 변환
        s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', camel_str)
        return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()
    
    @staticmethod
    def snake_to_camel(snake_str: str) -> str:
        """
        snake_case를 CamelCase로 변환
        
        Args:
            snake_str: snake_case 문자열
            
        Returns:
            str: CamelCase 문자열
        """
        components = snake_str.split('_')
        return ''.join(word.capitalize() for word in components) 