"""
Data normalizer for audit_agent scenarios

이 모듈은 시나리오 데이터의 정규화 기능을 제공합니다.
입력 데이터를 표준 스키마 형식으로 변환하고, 누락된 필드를 기본값으로 채웁니다.
"""

import json
from typing import Any, Dict, List, Optional

from config.logging_config import get_logger

logger = get_logger("validation")


class Normalizer:
    """
    시나리오 데이터 정규화 클래스
    
    입력 데이터를 표준 스키마 형식으로 변환하고,
    누락된 필드를 기본값으로 채우는 기능을 제공합니다.
    """
    
    def __init__(self):
        """Normalizer 초기화"""
        self.logger = logger
    
    def normalize_scenario_data(self, scenario_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        시나리오 데이터의 스키마 유효성을 검증하고 누락된 필드를 기본값으로 채웁니다.
        
        Args:
            scenario_data: 검증할 시나리오 데이터
            
        Returns:
            dict: 검증 결과와 정규화된 데이터
        """
        result = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "normalized_data": None
        }
        
        try:
            # 깊은 복사로 원본 데이터 보존
            normalized = json.loads(json.dumps(scenario_data))
            
            # 1. 필수 최상위 섹션 확인
            self._normalize_top_level_sections(normalized, result)
            
            # 2. 각 섹션별 정규화
            self._normalize_meta_section(normalized, result)
            self._normalize_spec_section(normalized, result)
            self._normalize_code_section(normalized, result)
            self._normalize_unit_tests_section(normalized, result)
            self._normalize_hints_section(normalized, result)
            self._normalize_optional_sections(normalized, result)
            
            result["normalized_data"] = normalized
            
        except Exception as e:
            result["valid"] = False
            result["errors"].append(f"Schema validation error: {str(e)}")
            self.logger.error(f"정규화 과정에서 오류 발생: {e}")
        
        return result
    
    def _normalize_top_level_sections(self, normalized: Dict[str, Any], result: Dict[str, Any]):
        """필수 최상위 섹션 확인"""
        required_sections = ["meta", "spec", "code", "unit_tests"]
        for section in required_sections:
            if section not in normalized:
                normalized[section] = {}
                result["warnings"].append(f"Missing required section '{section}', initialized with empty dict")
    
    def _normalize_meta_section(self, normalized: Dict[str, Any], result: Dict[str, Any]):
        """meta 섹션 정규화"""
        meta = normalized.get("meta", {})
        meta_defaults = {
            "id": "",
            "title": "",
            "category": "",
            "severity": "",
            "tags": [],
            "author": "",
            "created": ""
        }
        
        for key, default_value in meta_defaults.items():
            if key not in meta:
                meta[key] = default_value
                result["warnings"].append(f"Missing meta.{key}, set to default")
        
        # meta.id 필수 검증
        if not meta.get("id"):
            result["errors"].append("meta.id is required and cannot be empty")
            result["valid"] = False
        
        normalized["meta"] = meta
    
    def _normalize_spec_section(self, normalized: Dict[str, Any], result: Dict[str, Any]):
        """spec 섹션 정규화"""
        spec = normalized.get("spec", {})
        spec_defaults = {
            "description": "",
            "actors": [],
            "assets": [],
            "attack_vectors": [],  # 새로 추가
            "trust_boundaries": [],  # 유연한 구조 지원
            "components": [],
            "data_flows": [],
            "behaviors": [],
        }
        
        # 기본값만 설정하고, 기존 필드는 보존
        for key, default_value in spec_defaults.items():
            if key not in spec:
                spec[key] = default_value
        
        # precondition, action, expected 필드는 있으면 유지, 없으면 빈 문자열
        optional_spec_fields = ["precondition", "action", "expected"]
        for field in optional_spec_fields:
            if field not in spec:
                spec[field] = ""
        
        # actors 구조 정규화
        self._normalize_actors(spec, result)
        
        # assets 구조 정규화
        self._normalize_assets(spec, result)
        
        normalized["spec"] = spec
    
    def _normalize_actors(self, spec: Dict[str, Any], result: Dict[str, Any]):
        """actors 필드 정규화"""
        if spec["actors"]:
            for i, actor in enumerate(spec["actors"]):
                if not isinstance(actor, dict):
                    result["errors"].append(f"spec.actors[{i}] must be an object")
                    result["valid"] = False
                    continue
                    
                actor_defaults = {"id": "", "role": "", "trust_level": "untrusted"}
                for key, default_value in actor_defaults.items():
                    if key not in actor:
                        actor[key] = default_value
    
    def _normalize_assets(self, spec: Dict[str, Any], result: Dict[str, Any]):
        """assets 필드 정규화"""
        if spec["assets"]:
            for i, asset in enumerate(spec["assets"]):
                if not isinstance(asset, dict):
                    result["errors"].append(f"spec.assets[{i}] must be an object")
                    result["valid"] = False
                    continue
                    
                asset_defaults = {"name": "", "type": "", "critical": False}
                for key, default_value in asset_defaults.items():
                    if key not in asset:
                        asset[key] = default_value
    
    def _normalize_code_section(self, normalized: Dict[str, Any], result: Dict[str, Any]):
        """code 섹션 정규화"""
        code = normalized.get("code", {})
        code_defaults = {
            "poc_contract": "",
            "target_contract_name": "",
            "deployment_script": "",
            "vulnerable_functions": [],  # 새로 추가
            "vulnerability_pattern": "",  # 새로 추가
        }
        
        # 기본값만 설정하고 기존 필드들은 모두 보존
        for key, default_value in code_defaults.items():
            if key not in code:
                code[key] = default_value
        
        # 추가 필드들 (key_parameters 등)은 그대로 유지
        # 기존에 있던 다른 필드들도 모두 보존
        
        normalized["code"] = code
    
    def _normalize_unit_tests_section(self, normalized: Dict[str, Any], result: Dict[str, Any]):
        """unit_tests 섹션 정규화"""
        unit_tests = normalized.get("unit_tests", [])
        if not isinstance(unit_tests, list):
            unit_tests = []
            result["warnings"].append("unit_tests must be an array, reset to empty array")
        
        for i, test in enumerate(unit_tests):
            if not isinstance(test, dict):
                result["errors"].append(f"unit_tests[{i}] must be an object")
                result["valid"] = False
                continue
                
            test_defaults = {
                "test_name": "",
                "description": "",
                "test_code": "",
                "expected_behavior": "",
                "tags": []
            }
            
            for key, default_value in test_defaults.items():
                if key not in test:
                    test[key] = default_value
        
        normalized["unit_tests"] = unit_tests
    
    def _normalize_hints_section(self, normalized: Dict[str, Any], result: Dict[str, Any]):
        """hints 섹션 정규화"""
        hints = normalized.get("hints", {})
        hints_defaults = {
            "compiler": {"errors": [], "warnings": []},
            "runtime": {"last_run_id": "", "revert_info": "", "decoded_logs": []},
            "gas": {"used": 0},
            "vulnerability_details": {  # 새로 추가
                "root_cause": "",
                "attack_flow": "",
                "impact": ""
            },
            "mitigation": {  # 새로 추가
                "reentrancy_guard": "",
                "checks_effects_interactions": "",
                "pull_over_push": "",
                "additional_measures": []
            }
        }
        
        # 기본값 설정하되 기존 필드들은 모두 보존
        for key, default_value in hints_defaults.items():
            if key not in hints:
                hints[key] = default_value
            elif isinstance(default_value, dict) and isinstance(hints[key], dict):
                # 중첩된 딕셔너리의 경우 재귀적으로 기본값 설정하되 기존 필드 보존
                for sub_key, sub_default in default_value.items():
                    if sub_key not in hints[key]:
                        hints[key][sub_key] = sub_default
        
        # 사용자가 제공한 추가 hints 필드들 (governance_parameters, real_world_evidence 등)은 그대로 유지
        
        normalized["hints"] = hints
    
    def _normalize_optional_sections(self, normalized: Dict[str, Any], result: Dict[str, Any]):
        """선택적 섹션들 초기화"""
        optional_sections = {
            "patches": [],
            "runlog": [],
            "test_insights": [],
            "test_code_snapshots": {}
        }
        
        for section, default_value in optional_sections.items():
            if section not in normalized:
                normalized[section] = default_value
    
    def normalize_input_form(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        실제 입력 폼 데이터를 스키마 형식으로 정규화
        
        Args:
            input_data: 입력 폼 데이터
            
        Returns:
            dict: 정규화된 시나리오 데이터
        """
        # scenario 래퍼가 있는 경우 제거
        if "scenario" in input_data:
            scenario_data = input_data["scenario"]
        else:
            scenario_data = input_data
        
        # 스키마 검증 및 정규화 수행
        validation_result = self.normalize_scenario_data(scenario_data)
        
        if not validation_result["valid"]:
            raise ValueError(f"Schema validation failed: {validation_result['errors']}")
        
        return validation_result["normalized_data"]
    
    def apply_smart_defaults(self, normalized_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        스마트 기본값을 적용합니다.
        시나리오의 특성에 따라 적절한 기본값을 설정합니다.
        
        Args:
            normalized_data: 정규화된 데이터
            
        Returns:
            Dict[str, Any]: 스마트 기본값이 적용된 데이터
        """
        # 카테고리에 따른 기본 설정
        category = normalized_data.get("meta", {}).get("category", "").lower()
        
        if "reentrancy" in category:
            self._apply_reentrancy_defaults(normalized_data)
        elif "overflow" in category or "underflow" in category:
            self._apply_overflow_defaults(normalized_data)
        elif "access" in category:
            self._apply_access_control_defaults(normalized_data)
        
        return normalized_data
    
    def _apply_reentrancy_defaults(self, data: Dict[str, Any]):
        """재진입 공격 시나리오의 기본값 적용"""
        hints = data.setdefault("hints", {})
        hints.setdefault("vulnerability_details", {})
        
        if not hints["vulnerability_details"].get("root_cause"):
            hints["vulnerability_details"]["root_cause"] = "External call을 통한 재진입 가능성"
        
        if not hints["vulnerability_details"].get("attack_flow"):
            hints["vulnerability_details"]["attack_flow"] = "1. 공격자가 함수 호출 -> 2. External call 실행 -> 3. 공격자 컨트랙트에서 재진입"
    
    def _apply_overflow_defaults(self, data: Dict[str, Any]):
        """오버플로우/언더플로우 시나리오의 기본값 적용"""
        hints = data.setdefault("hints", {})
        hints.setdefault("vulnerability_details", {})
        
        if not hints["vulnerability_details"].get("root_cause"):
            hints["vulnerability_details"]["root_cause"] = "SafeMath 라이브러리 미사용으로 인한 정수 오버플로우/언더플로우"
    
    def _apply_access_control_defaults(self, data: Dict[str, Any]):
        """접근 제어 시나리오의 기본값 적용"""
        hints = data.setdefault("hints", {})
        hints.setdefault("vulnerability_details", {})
        
        if not hints["vulnerability_details"].get("root_cause"):
            hints["vulnerability_details"]["root_cause"] = "접근 제어 메커니즘의 부재 또는 잘못된 구현"


# 편의 함수 (기존 호환성 유지)
def normalize_input_form(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    실제 입력 폼 데이터를 스키마 형식으로 정규화하는 편의 함수
    
    Args:
        input_data: 입력 폼 데이터
        
    Returns:
        dict: 정규화된 시나리오 데이터
    """
    normalizer = Normalizer()
    return normalizer.normalize_input_form(input_data)


def validate_scenario_schema(scenario_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    시나리오 데이터의 스키마 유효성을 검증하고 누락된 필드를 기본값으로 채우는 편의 함수
    
    Args:
        scenario_data: 검증할 시나리오 데이터
        
    Returns:
        dict: 검증 결과와 정규화된 데이터
    """
    normalizer = Normalizer()
    return normalizer.normalize_scenario_data(scenario_data) 