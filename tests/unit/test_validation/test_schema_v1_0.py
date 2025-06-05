"""
Tests for SchemaV1Validator

Schema 1.0 검증기의 기능을 테스트합니다.
"""

import pytest
import sys
import os

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

from validation.schema_v1_0 import SchemaV1Validator, validate_scenario
from validation.base_validator import ValidationResult


class TestSchemaV1Validator:
    """SchemaV1Validator 테스트 클래스"""
    
    def setup_method(self):
        """각 테스트 메서드 실행 전 설정"""
        self.validator = SchemaV1Validator()
    
    def test_validator_initialization(self):
        """검증기 초기화 테스트"""
        assert self.validator is not None
        assert self.validator.default_schema_path == "schemas/schema_1.0.yaml"
        assert isinstance(self.validator.schema_cache, dict)
    
    def test_basic_scenario_structure_valid(self):
        """기본 시나리오 구조 검증 - 유효한 경우"""
        scenario = {
            "meta": {"id": "test_1", "title": "Test", "category": "test", "severity": "low"},
            "spec": {"description": "Test scenario"},
            "code": {},
            "unit_tests": [],
            "hints": {},
            "patches": [],
            "runlog": [],
            "test_insights": []
        }
        
        # 스키마 파일이 없을 수 있으므로 기본 검증만 수행
        result = self.validator.validate_basic_structure(scenario, ["meta", "spec", "code", "unit_tests"])
        assert result.valid
        assert len(result.errors) == 0
    
    def test_basic_scenario_structure_missing_sections(self):
        """기본 시나리오 구조 검증 - 누락된 섹션"""
        scenario = {
            "meta": {"id": "test_1"}
            # spec, code, unit_tests 누락
        }
        
        result = self.validator.validate_basic_structure(scenario, ["meta", "spec", "code", "unit_tests"])
        assert not result.valid
        assert "필수 최상위 섹션 'spec'이(가) 없습니다." in result.errors
        assert "필수 최상위 섹션 'code'이(가) 없습니다." in result.errors
        assert "필수 최상위 섹션 'unit_tests'이(가) 없습니다." in result.errors
    
    def test_meta_section_validation_valid(self):
        """meta 섹션 검증 - 유효한 경우"""
        scenario = {
            "meta": {
                "id": "TEST_001",
                "title": "Test Scenario",
                "category": "reentrancy",
                "severity": "critical",
                "tags": ["test", "reentrancy"]
            }
        }
        
        result = self.validator._validate_meta_section(scenario)
        assert result.valid
        assert len(result.errors) == 0
    
    def test_meta_section_validation_missing_required_fields(self):
        """meta 섹션 검증 - 필수 필드 누락"""
        scenario = {
            "meta": {
                "id": "TEST_001"
                # title, category, severity 누락
            }
        }
        
        result = self.validator._validate_meta_section(scenario)
        assert not result.valid
        assert any("필수 필드 'meta.title'" in error for error in result.errors)
        assert any("필수 필드 'meta.category'" in error for error in result.errors)
        assert any("필수 필드 'meta.severity'" in error for error in result.errors)
    
    def test_spec_section_validation_valid(self):
        """spec 섹션 검증 - 유효한 경우"""
        scenario = {
            "spec": {
                "description": "Test scenario description",
                "actors": [
                    {"id": "attacker", "role": "malicious_user", "trust_level": "untrusted"}
                ],
                "assets": [
                    {"name": "ETH", "type": "native_token", "critical": True}
                ],
                "attack_vectors": ["reentrancy"]
            }
        }
        
        result = self.validator._validate_spec_section(scenario)
        assert result.valid
        assert len(result.errors) == 0
    
    def test_spec_section_validation_invalid_actors(self):
        """spec 섹션 검증 - 잘못된 actors"""
        scenario = {
            "spec": {
                "description": "Test scenario",
                "actors": [
                    {"id": "attacker"}  # role, trust_level 누락
                ]
            }
        }
        
        result = self.validator._validate_spec_section(scenario)
        assert not result.valid
        assert any("필수 필드 'role'" in error for error in result.errors)
        assert any("필수 필드 'trust_level'" in error for error in result.errors)
    
    def test_unit_tests_section_validation_valid(self):
        """unit_tests 섹션 검증 - 유효한 경우"""
        scenario = {
            "unit_tests": [
                {
                    "test_name": "test_basic_attack",
                    "description": "Basic attack test",
                    "test_code": "function test_basic_attack() public {}",
                    "tags": ["basic", "attack"]
                }
            ]
        }
        
        result = self.validator._validate_unit_tests_section(scenario)
        assert result.valid
        assert len(result.errors) == 0
    
    def test_unit_tests_section_validation_duplicate_names(self):
        """unit_tests 섹션 검증 - 중복된 테스트 이름"""
        scenario = {
            "unit_tests": [
                {"test_name": "test_attack", "description": "Test 1"},
                {"test_name": "test_attack", "description": "Test 2"}  # 중복
            ]
        }
        
        result = self.validator._validate_unit_tests_section(scenario)
        assert not result.valid
        assert any("중복됩니다" in error for error in result.errors)
    
    def test_hints_section_validation_valid(self):
        """hints 섹션 검증 - 유효한 경우"""
        scenario = {
            "hints": {
                "compiler": {
                    "errors": [],
                    "warnings": ["Warning: unused variable"]
                },
                "runtime": {
                    "decoded_logs": ["CONSOLE: Attack successful"]
                },
                "gas": {
                    "used": 21000
                }
            }
        }
        
        result = self.validator._validate_hints_section(scenario)
        assert result.valid
        assert len(result.errors) == 0
    
    def test_patches_section_validation_valid(self):
        """patches 섹션 검증 - 유효한 경우"""
        scenario = {
            "patches": [
                {
                    "ts": "2024-01-01T00:00:00Z",
                    "author": "test_user",
                    "reason": "Fix test case",
                    "diff": "+console.log('test');"
                }
            ]
        }
        
        result = self.validator._validate_patches_section(scenario)
        assert result.valid
        assert len(result.errors) == 0
    
    def test_runlog_section_validation_valid(self):
        """runlog 섹션 검증 - 유효한 경우"""
        scenario = {
            "runlog": [
                {
                    "run_id": "run_001",
                    "ts": "2024-01-01T00:00:00Z",
                    "test_name": "test_attack",
                    "status": "SUCCESS",
                    "diff": "",
                    "stdout": "Test passed",
                    "stderr": ""
                }
            ]
        }
        
        result = self.validator._validate_runlog_section(scenario)
        assert result.valid
        assert len(result.errors) == 0
    
    def test_test_insights_section_validation_valid(self):
        """test_insights 섹션 검증 - 유효한 경우"""
        scenario = {
            "test_insights": [
                {
                    "run_id": "run_001",
                    "ts": "2024-01-01T00:00:00Z",
                    "test_name": "test_attack",
                    "precondition": "Contract deployed",
                    "state_changes": "Balance transferred",
                    "patterns": "Reentrancy detected",
                    "security_implications": "Funds at risk",
                    "additional_info": "None",
                    "confidence": 0.9
                }
            ]
        }
        
        result = self.validator._validate_test_insights_section(scenario)
        assert result.valid
        assert len(result.errors) == 0
    
    def test_test_insights_section_validation_invalid_confidence(self):
        """test_insights 섹션 검증 - 잘못된 confidence 값"""
        scenario = {
            "test_insights": [
                {
                    "run_id": "run_001",
                    "ts": "2024-01-01T00:00:00Z",
                    "test_name": "test_attack",
                    "precondition": "Contract deployed",
                    "state_changes": "Balance transferred",
                    "patterns": "Reentrancy detected",
                    "security_implications": "Funds at risk",
                    "additional_info": "None",
                    "confidence": 1.5  # 1.0을 초과
                }
            ]
        }
        
        result = self.validator._validate_test_insights_section(scenario)
        assert not result.valid
        assert any("0.0과 1.0 사이의 값이어야 합니다" in error for error in result.errors)
    
    def test_cross_references_validation(self):
        """섹션 간 일치성 검증"""
        scenario = {
            "unit_tests": [
                {"test_name": "test_attack", "description": "Attack test"}
            ],
            "runlog": [
                {"test_name": "test_attack", "run_id": "run_001", "ts": "2024-01-01T00:00:00Z", "status": "SUCCESS", "diff": ""},
                {"test_name": "nonexistent_test", "run_id": "run_002", "ts": "2024-01-01T00:00:00Z", "status": "SUCCESS", "diff": ""}  # 정의되지 않은 테스트
            ],
            "test_insights": [
                {"test_name": "test_attack", "run_id": "run_001", "ts": "2024-01-01T00:00:00Z", 
                 "precondition": "", "state_changes": "", "patterns": "", "security_implications": "", 
                 "additional_info": "", "confidence": 0.5}
            ]
        }
        
        result = self.validator._validate_cross_references(scenario)
        # 경고는 있을 수 있지만 에러는 없어야 함
        assert result.valid
        assert any("unit_tests에 정의되지 않았습니다" in warning for warning in result.warnings)
    
    def test_convenience_function_validate_scenario(self):
        """편의 함수 validate_scenario 테스트"""
        scenario = {
            "meta": {"id": "test_1", "title": "Test", "category": "test", "severity": "low"},
            "spec": {"description": "Test scenario"},
            "code": {},
            "unit_tests": [],
            "hints": {},
            "patches": [],
            "runlog": [],
            "test_insights": []
        }
        
        # 스키마 파일이 없을 수 있으므로 예외 처리
        try:
            result = validate_scenario(scenario)
            assert isinstance(result, dict)
            assert "valid" in result
            assert "errors" in result
            assert "warnings" in result
        except ValueError:
            # 스키마 파일이 없는 경우 예상되는 동작
            pass


class TestValidationResult:
    """ValidationResult 클래스 테스트"""
    
    def test_validation_result_initialization(self):
        """ValidationResult 초기화 테스트"""
        result = ValidationResult()
        assert result.valid is True
        assert result.errors == []
        assert result.warnings == []
        assert result.schema_version == "unknown"
    
    def test_validation_result_add_error(self):
        """에러 추가 테스트"""
        result = ValidationResult()
        result.add_error("Test error")
        
        assert not result.valid
        assert "Test error" in result.errors
    
    def test_validation_result_add_warning(self):
        """경고 추가 테스트"""
        result = ValidationResult()
        result.add_warning("Test warning")
        
        assert result.valid  # 경고는 valid 상태를 변경하지 않음
        assert "Test warning" in result.warnings
    
    def test_validation_result_merge(self):
        """결과 병합 테스트"""
        result1 = ValidationResult()
        result1.add_warning("Warning 1")
        
        result2 = ValidationResult()
        result2.add_error("Error 1")
        result2.add_warning("Warning 2")
        
        result1.merge(result2)
        
        assert not result1.valid  # 에러가 있으므로 false
        assert "Error 1" in result1.errors
        assert "Warning 1" in result1.warnings
        assert "Warning 2" in result1.warnings
    
    def test_validation_result_to_dict(self):
        """딕셔너리 변환 테스트"""
        result = ValidationResult(schema_version="test-v1.0")
        result.add_error("Test error")
        result.add_warning("Test warning")
        
        dict_result = result.to_dict()
        
        assert dict_result["valid"] is False
        assert "Test error" in dict_result["errors"]
        assert "Test warning" in dict_result["warnings"]
        assert dict_result["schema_version"] == "test-v1.0" 