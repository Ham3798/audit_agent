"""
Base validator for audit_agent scenarios

이 모듈은 시나리오 검증을 위한 기본 클래스와 인터페이스를 정의합니다.
모든 버전별 검증기는 이 기본 클래스를 상속받아 구현해야 합니다.
"""

import yaml
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple

from config.logging_config import get_logger

logger = get_logger("validation")


class ValidationResult:
    """검증 결과를 나타내는 클래스"""
    
    def __init__(self, valid: bool = True, errors: List[str] = None, warnings: List[str] = None, schema_version: str = "unknown"):
        self.valid = valid
        self.errors = errors or []
        self.warnings = warnings or []
        self.schema_version = schema_version
    
    def to_dict(self) -> Dict[str, Any]:
        """검증 결과를 딕셔너리로 변환"""
        return {
            "valid": self.valid,
            "errors": self.errors,
            "warnings": self.warnings,
            "schema_version": self.schema_version
        }
    
    def add_error(self, error: str):
        """에러 추가"""
        self.errors.append(error)
        self.valid = False
    
    def add_warning(self, warning: str):
        """경고 추가"""
        self.warnings.append(warning)
    
    def merge(self, other: 'ValidationResult'):
        """다른 검증 결과와 병합"""
        self.errors.extend(other.errors)
        self.warnings.extend(other.warnings)
        if not other.valid:
            self.valid = False


class BaseValidator(ABC):
    """
    시나리오 검증을 위한 기본 클래스
    
    모든 버전별 검증기는 이 클래스를 상속받아 구현해야 합니다.
    스키마 로딩, 캐싱, 기본 검증 로직을 제공합니다.
    """
    
    def __init__(self, default_schema_path: str = "schemas/schema_1.0.yaml"):
        """
        BaseValidator 초기화
        
        Args:
            default_schema_path: 기본 스키마 파일 경로
        """
        self.default_schema_path = default_schema_path
        self.schema_cache = {}  # 스키마 파일 캐싱
    
    def load_schema(self, schema_path: Optional[str] = None) -> Dict[str, Any]:
        """
        스키마 파일을 로드하고 캐싱합니다.
        
        Args:
            schema_path: 스키마 파일 경로 (None인 경우 기본값 사용)
            
        Returns:
            Dict[str, Any]: 로드된 스키마 데이터
        """
        schema_path = schema_path or self.default_schema_path
        
        # 캐싱된 스키마가 있으면 반환
        if schema_path in self.schema_cache:
            return self.schema_cache[schema_path]
        
        try:
            with open(schema_path, "r", encoding="utf-8") as f:
                schema_data = yaml.safe_load(f)
            
            self.schema_cache[schema_path] = schema_data
            logger.info(f"스키마 파일 로드 성공: {schema_path}, 버전: {schema_data.get('schema_version', 'unknown')}")
            return schema_data
        except Exception as e:
            logger.error(f"스키마 파일 로드 오류: {e}")
            raise ValueError(f"스키마 파일 '{schema_path}'을 로드할 수 없습니다: {str(e)}")

    @abstractmethod
    def validate(self, scenario: Dict[str, Any], schema_path: Optional[str] = None) -> ValidationResult:
        """
        시나리오가 스키마에 맞는지 검증합니다.
        
        Args:
            scenario: 검증할 시나리오 데이터
            schema_path: 스키마 파일 경로 (None인 경우 기본값 사용)
            
        Returns:
            ValidationResult: 검증 결과
        """
        pass
    
    def validate_basic_structure(self, scenario: Dict[str, Any], required_sections: List[str]) -> ValidationResult:
        """
        시나리오의 기본 구조를 검증합니다.
        
        Args:
            scenario: 검증할 시나리오 데이터
            required_sections: 필수 섹션 목록
            
        Returns:
            ValidationResult: 기본 구조 검증 결과
        """
        result = ValidationResult()
        
        # 시나리오가 딕셔너리인지 확인
        if not isinstance(scenario, dict):
            result.add_error("시나리오 데이터는 객체(object)여야 합니다.")
            return result
        
        # 필수 섹션 존재 여부 확인
        for section in required_sections:
            if section not in scenario:
                result.add_error(f"필수 최상위 섹션 '{section}'이(가) 없습니다.")
        
        return result
    
    def validate_section_type(self, scenario: Dict[str, Any], section_name: str, expected_type: type) -> ValidationResult:
        """
        특정 섹션의 타입을 검증합니다.
        
        Args:
            scenario: 시나리오 데이터
            section_name: 섹션 이름
            expected_type: 예상 타입 (dict, list 등)
            
        Returns:
            ValidationResult: 타입 검증 결과
        """
        result = ValidationResult()
        
        if section_name in scenario:
            if not isinstance(scenario[section_name], expected_type):
                expected_type_name = "객체(object)" if expected_type == dict else "배열(list)" if expected_type == list else expected_type.__name__
                actual_type_name = type(scenario[section_name]).__name__
                result.add_error(f"섹션 '{section_name}'의 타입이 올바르지 않습니다. (예상: {expected_type_name}, 실제: {actual_type_name})")
        
        return result
    
    def validate_required_fields(self, data: Dict[str, Any], required_fields: List[str], section_prefix: str = "") -> ValidationResult:
        """
        필수 필드들을 검증합니다.
        
        Args:
            data: 검증할 데이터
            required_fields: 필수 필드 목록
            section_prefix: 섹션 접두사 (에러 메시지용)
            
        Returns:
            ValidationResult: 필드 검증 결과
        """
        result = ValidationResult()
        
        for field in required_fields:
            if field not in data:
                result.add_error(f"필수 필드 '{section_prefix}{field}'이(가) 없습니다.")
            elif not data[field]:  # 빈 문자열, None, 빈 리스트 등
                result.add_error(f"필수 필드 '{section_prefix}{field}'이(가) 비어 있습니다.")
        
        return result
    
    def validate_field_type(self, data: Dict[str, Any], field_name: str, expected_type: type, section_prefix: str = "") -> ValidationResult:
        """
        특정 필드의 타입을 검증합니다.
        
        Args:
            data: 검증할 데이터
            field_name: 필드 이름
            expected_type: 예상 타입
            section_prefix: 섹션 접두사
            
        Returns:
            ValidationResult: 타입 검증 결과
        """
        result = ValidationResult()
        
        if field_name in data and not isinstance(data[field_name], expected_type):
            expected_type_name = expected_type.__name__
            result.add_error(f"'{section_prefix}{field_name}'는 {expected_type_name}이어야 합니다.")
        
        return result
    
    def extract_field_info(self, section: Any) -> Any:
        """
        스키마 섹션의 필드 정보를 추출합니다.
        
        Args:
            section: 스키마 섹션 데이터
            
        Returns:
            dict, list, 또는 타입명: 추출된 필드 정보
        """
        if isinstance(section, dict):
            return {k: self.get_field_type(v) for k, v in section.items()}
        elif isinstance(section, list) and section and isinstance(section[0], dict):
            # 리스트 안의 첫 항목으로 구조 추정
            return [self.extract_field_info(section[0])]
        else:
            return type(section).__name__
    
    def get_field_type(self, value: Any) -> Any:
        """
        값의 타입 정보를 추출합니다.
        
        Args:
            value: 값
            
        Returns:
            dict, list, 또는 타입명: 값의 타입 정보
        """
        if isinstance(value, dict):
            return {k: self.get_field_type(v) for k, v in value.items()}
        elif isinstance(value, list):
            if value and all(isinstance(x, dict) for x in value):
                return [self.get_field_type(value[0])]
            else:
                return "list"
        else:
            return type(value).__name__ 