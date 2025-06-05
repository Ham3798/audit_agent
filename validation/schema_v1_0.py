"""
Schema 1.0 validator for audit_agent scenarios

이 모듈은 schema_1.0.yaml 버전에 특화된 시나리오 검증 로직을 제공합니다.
기존 schema_validator.py의 _validate_v1_0 메서드 로직을 분리하여 구현했습니다.
"""

import datetime
from typing import Any, Dict, List, Optional

from config.logging_config import get_logger
from .base_validator import BaseValidator, ValidationResult

logger = get_logger("validation")


class SchemaV1Validator(BaseValidator):
    """
    Schema 1.0 버전에 특화된 시나리오 검증기
    
    schema_1.0.yaml에 정의된 구조에 맞는 시나리오 검증을 수행합니다.
    1 시나리오 = 1 PoC + n개 유닛테스트 구조를 지원합니다.
    """
    
    def validate(self, scenario: Dict[str, Any], schema_path: Optional[str] = None) -> ValidationResult:
        """
        Schema 1.0 버전에 맞는 시나리오 검증을 수행합니다.
        
        Args:
            scenario: 검증할 시나리오 데이터
            schema_path: 스키마 파일 경로 (None인 경우 기본값 사용)
            
        Returns:
            ValidationResult: 검증 결과
        """
        try:
            # 스키마 로드
            schema_data = self.load_schema(schema_path)
            schema_version = schema_data.get("schema_version", "scenario-schema-1.0")
            
            result = ValidationResult(schema_version=schema_version)
            
            # 기본 구조 검증
            required_sections = ["meta", "spec", "code", "unit_tests", "hints", "patches", "runlog", "test_insights"]
            basic_result = self.validate_basic_structure(scenario, required_sections)
            result.merge(basic_result)
            
            # 각 섹션별 상세 검증
            if result.valid:  # 기본 구조가 유효한 경우에만 상세 검증 진행
                result.merge(self._validate_meta_section(scenario))
                result.merge(self._validate_spec_section(scenario))
                result.merge(self._validate_code_section(scenario))
                result.merge(self._validate_unit_tests_section(scenario))
                result.merge(self._validate_hints_section(scenario))
                result.merge(self._validate_patches_section(scenario))
                result.merge(self._validate_runlog_section(scenario))
                result.merge(self._validate_test_insights_section(scenario))
                
                # 일치성 검증
                result.merge(self._validate_cross_references(scenario))
            
            return result
            
        except Exception as e:
            logger.error(f"검증 과정에서 오류 발생: {e}")
            error_result = ValidationResult(valid=False)
            error_result.add_error(f"검증 과정에서 오류 발생: {str(e)}")
            return error_result
    
    def _validate_meta_section(self, scenario: Dict[str, Any]) -> ValidationResult:
        """meta 섹션 검증"""
        result = ValidationResult()
        
        # 섹션 타입 검증
        section_result = self.validate_section_type(scenario, "meta", dict)
        result.merge(section_result)
        
        if "meta" in scenario and isinstance(scenario["meta"], dict):
            meta = scenario["meta"]
            
            # 필수 필드 검증
            required_fields = ["id", "title", "category", "severity"]
            field_result = self.validate_required_fields(meta, required_fields, "meta.")
            result.merge(field_result)
            
            # 선택적 필드 타입 검증
            if "tags" in meta:
                tags_result = self.validate_field_type(meta, "tags", list, "meta.")
                result.merge(tags_result)
            
            # 날짜 형식 검증
            if "created" in meta and meta["created"]:
                try:
                    datetime.datetime.fromisoformat(meta["created"].replace('Z', '+00:00'))
                except (ValueError, TypeError):
                    result.add_error("'meta.created'는 유효한 ISO8601 형식(YYYY-MM-DDTHH:MM:SS+TZ)이어야 합니다.")
        
        return result
    
    def _validate_spec_section(self, scenario: Dict[str, Any]) -> ValidationResult:
        """spec 섹션 검증"""
        result = ValidationResult()
        
        # 섹션 타입 검증
        section_result = self.validate_section_type(scenario, "spec", dict)
        result.merge(section_result)
        
        if "spec" in scenario and isinstance(scenario["spec"], dict):
            spec = scenario["spec"]
            
            # 필수 문자열 필드 검증 (유연하게 처리)
            string_fields = ["description", "precondition", "action", "expected"]
            for field in string_fields:
                if field in spec:
                    field_result = self.validate_field_type(spec, field, str, "spec.")
                    result.merge(field_result)
                    if field in spec and not spec[field]:
                        result.add_warning(f"'spec.{field}'이(가) 비어 있습니다.")
            
            # 리스트 필드 검증 (유연하게 처리)
            list_fields = ["actors", "assets", "components", "trust_boundaries", "data_flows", "behaviors", "attack_vectors"]
            for field in list_fields:
                if field in spec:
                    field_result = self.validate_field_type(spec, field, list, "spec.")
                    result.merge(field_result)
            
            # actors 상세 검증
            if "actors" in spec and isinstance(spec["actors"], list):
                result.merge(self._validate_actors(spec["actors"]))
            
            # assets 상세 검증
            if "assets" in spec and isinstance(spec["assets"], list):
                result.merge(self._validate_assets(spec["assets"]))
        
        return result
    
    def _validate_actors(self, actors: List[Dict[str, Any]]) -> ValidationResult:
        """actors 필드 상세 검증"""
        result = ValidationResult()
        
        for i, actor in enumerate(actors):
            if not isinstance(actor, dict):
                result.add_error(f"'spec.actors[{i}]'는 객체(object)여야 합니다.")
                continue
            
            # 필수 필드 검증
            required_fields = ["id", "role", "trust_level"]
            for field in required_fields:
                if field not in actor:
                    result.add_error(f"'spec.actors[{i}]'에 필수 필드 '{field}'이(가) 없습니다.")
                elif not actor[field]:
                    result.add_error(f"'spec.actors[{i}].{field}'이(가) 비어 있습니다.")
        
        return result
    
    def _validate_assets(self, assets: List[Dict[str, Any]]) -> ValidationResult:
        """assets 필드 상세 검증"""
        result = ValidationResult()
        
        for i, asset in enumerate(assets):
            if not isinstance(asset, dict):
                result.add_error(f"'spec.assets[{i}]'는 객체(object)여야 합니다.")
                continue
            
            # 필수 필드 검증
            required_fields = ["name", "type"]
            for field in required_fields:
                if field not in asset:
                    result.add_error(f"'spec.assets[{i}]'에 필수 필드 '{field}'이(가) 없습니다.")
                elif not asset[field]:
                    result.add_error(f"'spec.assets[{i}].{field}'이(가) 비어 있습니다.")
        
        return result
    
    def _validate_code_section(self, scenario: Dict[str, Any]) -> ValidationResult:
        """code 섹션 검증"""
        result = ValidationResult()
        
        # 섹션 타입 검증
        section_result = self.validate_section_type(scenario, "code", dict)
        result.merge(section_result)
        
        if "code" in scenario and isinstance(scenario["code"], dict):
            code = scenario["code"]
            
            # 선택적 필드 타입 검증
            string_fields = ["poc_contract", "target_contract_name", "deployment_script", "vulnerability_pattern"]
            for field in string_fields:
                if field in code:
                    field_result = self.validate_field_type(code, field, str, "code.")
                    result.merge(field_result)
            
            # 리스트 필드 검증
            if "vulnerable_functions" in code:
                field_result = self.validate_field_type(code, "vulnerable_functions", list, "code.")
                result.merge(field_result)
        
        return result
    
    def _validate_unit_tests_section(self, scenario: Dict[str, Any]) -> ValidationResult:
        """unit_tests 섹션 검증"""
        result = ValidationResult()
        
        # 섹션 타입 검증
        section_result = self.validate_section_type(scenario, "unit_tests", list)
        result.merge(section_result)
        
        if "unit_tests" in scenario and isinstance(scenario["unit_tests"], list):
            unit_tests = scenario["unit_tests"]
            test_names = set()
            
            for i, test in enumerate(unit_tests):
                if not isinstance(test, dict):
                    result.add_error(f"'unit_tests[{i}]'는 객체(object)여야 합니다.")
                    continue
                
                # 필수 필드 검증 (유연하게 처리)
                required_fields = ["test_name", "description"]
                for field in required_fields:
                    if field not in test:
                        result.add_error(f"'unit_tests[{i}]'에 필수 필드 '{field}'이(가) 없습니다.")
                    elif not isinstance(test[field], str):
                        result.add_error(f"'unit_tests[{i}].{field}'는 문자열이어야 합니다.")
                
                # test_code 또는 test_file_path 중 하나는 있어야 함
                if "test_code" not in test and "test_file_path" not in test:
                    result.add_warning(f"'unit_tests[{i}]'에 'test_code' 또는 'test_file_path' 중 하나는 있어야 합니다.")
                
                # tags 필드 검증
                if "tags" in test:
                    field_result = self.validate_field_type(test, "tags", list, f"unit_tests[{i}].")
                    result.merge(field_result)
                
                # test_name 중복 검증
                test_name = test.get("test_name", "")
                if test_name:
                    if test_name in test_names:
                        result.add_error(f"'unit_tests[{i}].test_name' '{test_name}'이(가) 중복됩니다.")
                    else:
                        test_names.add(test_name)
        
        return result
    
    def _validate_hints_section(self, scenario: Dict[str, Any]) -> ValidationResult:
        """hints 섹션 검증"""
        result = ValidationResult()
        
        # 섹션 타입 검증
        section_result = self.validate_section_type(scenario, "hints", dict)
        result.merge(section_result)
        
        if "hints" in scenario and isinstance(scenario["hints"], dict):
            hints = scenario["hints"]
            
            # compiler 섹션 검증
            if "compiler" in hints:
                if not isinstance(hints["compiler"], dict):
                    result.add_error("'hints.compiler'는 객체(object)여야 합니다.")
                else:
                    compiler = hints["compiler"]
                    for field in ["errors", "warnings"]:
                        if field in compiler:
                            field_result = self.validate_field_type(compiler, field, list, "hints.compiler.")
                            result.merge(field_result)
            
            # runtime 섹션 검증
            if "runtime" in hints:
                if not isinstance(hints["runtime"], dict):
                    result.add_error("'hints.runtime'는 객체(object)여야 합니다.")
                else:
                    runtime = hints["runtime"]
                    if "decoded_logs" in runtime:
                        field_result = self.validate_field_type(runtime, "decoded_logs", list, "hints.runtime.")
                        result.merge(field_result)
            
            # gas 섹션 검증
            if "gas" in hints:
                if not isinstance(hints["gas"], dict):
                    result.add_error("'hints.gas'는 객체(object)여야 합니다.")
                else:
                    gas = hints["gas"]
                    if "used" in gas and not (isinstance(gas["used"], (int, float)) or 
                                           (isinstance(gas["used"], str) and gas["used"].isdigit())):
                        result.add_error("'hints.gas.used'는 숫자 또는 숫자 문자열이어야 합니다.")
        
        return result
    
    def _validate_patches_section(self, scenario: Dict[str, Any]) -> ValidationResult:
        """patches 섹션 검증"""
        result = ValidationResult()
        
        # 섹션 타입 검증
        section_result = self.validate_section_type(scenario, "patches", list)
        result.merge(section_result)
        
        if "patches" in scenario and isinstance(scenario["patches"], list):
            patches = scenario["patches"]
            for i, patch in enumerate(patches):
                if not isinstance(patch, dict):
                    result.add_error(f"'patches[{i}]'는 객체(object)여야 합니다.")
                    continue
                
                # 필수 필드 검증
                required_fields = ["ts", "author", "reason", "diff"]
                for field in required_fields:
                    if field not in patch:
                        result.add_error(f"'patches[{i}]'에 필수 필드 '{field}'이(가) 없습니다.")
                
                # 타임스탬프 형식 검증
                if "ts" in patch and patch["ts"]:
                    try:
                        datetime.datetime.fromisoformat(patch["ts"].replace('Z', '+00:00'))
                    except (ValueError, TypeError):
                        result.add_error(f"'patches[{i}].ts'는 유효한 ISO8601 형식이어야 합니다.")
        
        return result
    
    def _validate_runlog_section(self, scenario: Dict[str, Any]) -> ValidationResult:
        """runlog 섹션 검증"""
        result = ValidationResult()
        
        # 섹션 타입 검증
        section_result = self.validate_section_type(scenario, "runlog", list)
        result.merge(section_result)
        
        if "runlog" in scenario and isinstance(scenario["runlog"], list):
            runlog = scenario["runlog"]
            for i, log in enumerate(runlog):
                if not isinstance(log, dict):
                    result.add_error(f"'runlog[{i}]'는 객체(object)여야 합니다.")
                    continue
                
                # 필수 필드 검증
                required_fields = ["run_id", "ts", "test_name", "status", "diff"]
                for field in required_fields:
                    if field not in log:
                        result.add_error(f"'runlog[{i}]'에 필수 필드 '{field}'이(가) 없습니다.")
                
                # 타임스탬프 형식 검증
                if "ts" in log and log["ts"]:
                    try:
                        datetime.datetime.fromisoformat(log["ts"].replace('Z', '+00:00'))
                    except (ValueError, TypeError):
                        result.add_error(f"'runlog[{i}].ts'는 유효한 ISO8601 형식이어야 합니다.")
                
                # status 값 검증
                if "status" in log and log["status"] not in ["success", "failure", "error", "SUCCESS", "TEST_FAILURE", "ERROR"]:
                    result.add_warning(f"'runlog[{i}].status'의 값이 표준 상태값이 아닙니다: {log['status']}")
        
        return result
    
    def _validate_test_insights_section(self, scenario: Dict[str, Any]) -> ValidationResult:
        """test_insights 섹션 검증"""
        result = ValidationResult()
        
        # 섹션 타입 검증
        section_result = self.validate_section_type(scenario, "test_insights", list)
        result.merge(section_result)
        
        if "test_insights" in scenario and isinstance(scenario["test_insights"], list):
            insights = scenario["test_insights"]
            for i, insight in enumerate(insights):
                if not isinstance(insight, dict):
                    result.add_error(f"'test_insights[{i}]'는 객체(object)여야 합니다.")
                    continue
                
                # 필수 필드 검증
                required_fields = ["run_id", "ts", "test_name", "precondition", "state_changes", 
                                 "patterns", "security_implications", "additional_info", "confidence"]
                for field in required_fields:
                    if field not in insight:
                        result.add_error(f"'test_insights[{i}]'에 필수 필드 '{field}'이(가) 없습니다.")
                
                # 타임스탬프 형식 검증
                if "ts" in insight and insight["ts"]:
                    try:
                        datetime.datetime.fromisoformat(insight["ts"].replace('Z', '+00:00'))
                    except (ValueError, TypeError):
                        result.add_error(f"'test_insights[{i}].ts'는 유효한 ISO8601 형식이어야 합니다.")
                
                # confidence 값 검증
                if "confidence" in insight:
                    confidence = insight["confidence"]
                    if not isinstance(confidence, (int, float)):
                        try:
                            confidence = float(confidence)
                        except (ValueError, TypeError):
                            result.add_error(f"'test_insights[{i}].confidence'는 숫자여야 합니다.")
                            continue
                    
                    if confidence < 0.0 or confidence > 1.0:
                        result.add_error(f"'test_insights[{i}].confidence'는 0.0과 1.0 사이의 값이어야 합니다.")
        
        return result
    
    def _validate_cross_references(self, scenario: Dict[str, Any]) -> ValidationResult:
        """섹션 간 일치성 검증"""
        result = ValidationResult()
        
        # unit_tests에서 test_name 수집
        unit_test_names = set()
        if "unit_tests" in scenario and isinstance(scenario["unit_tests"], list):
            for test in scenario["unit_tests"]:
                if isinstance(test, dict) and "test_name" in test:
                    unit_test_names.add(test["test_name"])
        
        # runlog의 test_name 일치성 검증
        if "runlog" in scenario and isinstance(scenario["runlog"], list):
            for i, log in enumerate(scenario["runlog"]):
                if isinstance(log, dict) and "test_name" in log and log["test_name"]:
                    test_name = log["test_name"]
                    if test_name not in unit_test_names and test_name != "":
                        result.add_warning(f"'runlog[{i}].test_name' '{test_name}'이(가) unit_tests에 정의되지 않았습니다.")
        
        # test_insights의 test_name 일치성 검증
        if "test_insights" in scenario and isinstance(scenario["test_insights"], list):
            for i, insight in enumerate(scenario["test_insights"]):
                if isinstance(insight, dict) and "test_name" in insight and insight["test_name"]:
                    test_name = insight["test_name"]
                    if test_name not in unit_test_names and test_name != "":
                        result.add_warning(f"'test_insights[{i}].test_name' '{test_name}'이(가) unit_tests에 정의되지 않았습니다.")
        
        return result


# 편의 함수 (기존 호환성 유지)
def validate_scenario(scenario: Dict[str, Any], schema_path: Optional[str] = None) -> Dict[str, Any]:
    """
    시나리오가 스키마에 맞는지 검증하는 편의 함수
    
    Args:
        scenario: 검증할 시나리오 데이터
        schema_path: 스키마 파일 경로 (None인 경우 기본값 사용)
        
    Returns:
        Dict[str, Any]: 검증 결과
    """
    validator = SchemaV1Validator(default_schema_path=schema_path or "schemas/schema_1.0.yaml")
    result = validator.validate(scenario)
    return result.to_dict() 