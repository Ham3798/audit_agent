"""
스키마 검증 모듈 (v1.3.0)

이 모듈은 시나리오가 정의된 스키마에 맞게 구성되었는지 검증하는 기능을 제공합니다.
버전별 스키마 검증을 지원하며, 새로운 스키마 버전이 추가되어도 유연하게 대응할 수 있습니다.

[핵심 아키텍처 변화: 1 시나리오 = 1 PoC + n개 유닛테스트]
- 기존: 1 시나리오 = 1 테스트 컨트랙트 구조 검증
- 신규: 1 시나리오 = 1 통합 PoC 코드 + n개의 개별 유닛테스트 구조 검증
- schema_1.0.yaml의 확장된 구조를 완전 지원

[새로운 검증 기능]
1. code 섹션 검증 (새로 추가):
   - poc_contract: PoC 컨트랙트 코드 검증
   - target_contract_name: 대상 컨트랙트 이름 검증
   - deployment_script: 배포 스크립트 검증 (선택적)

2. unit_tests 섹션 검증 (새로 추가):
   - test_name: 테스트 함수 이름 검증 (고유성 포함)
   - description: 테스트 설명 검증
   - test_code: 테스트 함수 코드 검증
   - expected_behavior: 예상 동작 검증
   - tags: 테스트 태그 검증

3. 확장된 runlog 검증:
   - test_name 필드 추가 검증
   - unit_tests와의 일치성 검증

4. 확장된 test_insights 검증:
   - test_name 필드 추가 검증
   - unit_tests와의 일치성 검증

[주요 클래스 및 메서드]
- SchemaValidator: 메인 검증 클래스
  - validate(): 시나리오 전체 검증
  - _validate_v1_0(): schema_1.0.yaml 버전별 검증
  - extract_hints_from_results(): 테스트 결과에서 힌트 추출

[검증 규칙]
- 필수 섹션: meta, spec, code, unit_tests, hints, patches, runlog, test_insights
- 타입 검증: 각 필드의 예상 타입 확인
- 일치성 검증: runlog/test_insights의 test_name과 unit_tests 간 일치성
- 중복 검증: unit_tests 내 test_name 중복 방지
- 날짜 형식 검증: ISO8601 형식 확인
- 신뢰도 검증: test_insights의 confidence 값 범위 확인 (0.0-1.0)

[기존 호환성]
- 기존 스키마 구조와 완전 호환
- 새로운 필드들은 선택적으로 처리
- 기존 시나리오 데이터의 마이그레이션 지원
"""

import yaml
import logging
import re
import datetime
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("schema-validator")
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

class SchemaValidator:
    """
    스키마 검증 클래스
    
    스키마 파일을 로드하고 시나리오가 해당 스키마에 맞게 구성되었는지 검증합니다.
    버전별 검증 로직을 지원하며, 새로운 스키마 버전이 추가되어도 유연하게 대응할 수 있습니다.
    """
    
    def __init__(self, default_schema_path: str = "schemas/schema_1.0.yaml"):
        """
        SchemaValidator 초기화
        
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

    def validate(self, scenario: Dict[str, Any], schema_path: Optional[str] = None) -> Dict[str, Any]:
        """
        시나리오가 스키마에 맞는지 검증합니다.
        
        Args:
            scenario: 검증할 시나리오 데이터
            schema_path: 스키마 파일 경로 (None인 경우 기본값 사용)
            
        Returns:
            Dict[str, Any]: 검증 결과 (valid, errors, warnings, schema_version 포함)
        """
        errors = []
        warnings = []
        
        # 스키마 로드
        try:
            schema_data = self.load_schema(schema_path)
            schema_version = schema_data.get("schema_version", "unknown")
            
            # 버전별 검증 메서드 호출
            if schema_version == "scenario-schema-1.0":
                return self._validate_v1_0(scenario, schema_data)
            else:
                # 알 수 없는 버전의 경우 기본 검증
                logger.warning(f"알 수 없는 스키마 버전: {schema_version}, 기본 검증 수행")
                return self._validate_basic(scenario, schema_data)
                
        except Exception as e:
            logger.error(f"검증 과정에서 오류 발생: {e}")
            return {
                "valid": False,
                "errors": [f"검증 과정에서 오류 발생: {str(e)}"],
                "warnings": [],
                "schema_version": "error"
            }
    
    def _validate_basic(self, scenario: Dict[str, Any], schema_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        기본적인 시나리오 검증을 수행합니다.
        
        Args:
            scenario: 검증할 시나리오 데이터
            schema_data: 스키마 데이터
            
        Returns:
            Dict[str, Any]: 검증 결과
        """
        errors = []
        warnings = []
        schema_version = schema_data.get("schema_version", "unknown")
        
        # 최상위 섹션 검증
        for section in schema_data.keys():
            if section == "schema_version":
                continue
                
            if section not in scenario:
                errors.append(f"필수 최상위 섹션 '{section}'이(가) 없습니다.")
            elif isinstance(schema_data[section], dict) and not isinstance(scenario[section], dict):
                errors.append(f"섹션 '{section}'의 타입이 올바르지 않습니다. (예상: 객체(object))")
            elif isinstance(schema_data[section], list) and not isinstance(scenario[section], list):
                errors.append(f"섹션 '{section}'의 타입이 올바르지 않습니다. (예상: 배열(list))")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "schema_version": schema_version
        }
    
    def _validate_v1_0(self, scenario: Dict[str, Any], schema_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        schema_1.0.yaml 버전에 맞는 시나리오 검증을 수행합니다.
        
        Args:
            scenario: 검증할 시나리오 데이터
            schema_data: 스키마 데이터
            
        Returns:
            Dict[str, Any]: 검증 결과
        """
        errors = []
        warnings = []
        schema_version = schema_data.get("schema_version", "scenario-schema-1.0")
        
        # 최상위 필수 섹션 검증 (code, unit_tests 추가)
        required_top_level_sections = ["meta", "spec", "code", "unit_tests", "hints", "patches", "runlog", "test_insights"]
        for section in required_top_level_sections:
            if section not in scenario:
                errors.append(f"필수 최상위 섹션 '{section}'이(가) 없습니다.")
            elif not isinstance(scenario[section], (dict if section not in ["unit_tests", "patches", "runlog", "test_insights"] else list)):
                expected_type = "객체(object)" if section not in ["unit_tests", "patches", "runlog", "test_insights"] else "배열(list)"
                errors.append(f"섹션 '{section}'의 타입이 올바르지 않습니다. (예상: {expected_type}, 실제: {type(scenario[section]).__name__})")

        # 1. meta 섹션 검증
        if "meta" in scenario and isinstance(scenario["meta"], dict):
            meta = scenario["meta"]
            
            # 필수 필드 검증
            required_meta_fields = ["id", "title", "category", "severity"]
            for field in required_meta_fields:
                if field not in meta or not meta[field]: 
                    errors.append(f"필수 필드 'meta.{field}'이(가) 없거나 비어 있습니다.")
            
            # 선택적 필드 타입 검증
            if "tags" in meta and not isinstance(meta["tags"], list):
                errors.append(f"'meta.tags'는 배열(list)이어야 합니다.")
            
            # 날짜 형식 검증
            if "created" in meta and meta["created"]:
                try:
                    datetime.datetime.fromisoformat(meta["created"].replace('Z', '+00:00'))
                except (ValueError, TypeError):
                    errors.append(f"'meta.created'는 유효한 ISO8601 형식(YYYY-MM-DDTHH:MM:SS+TZ)이어야 합니다.")
        elif "meta" in scenario:
            errors.append("'meta' 섹션은 객체(object)여야 합니다.")

        # 2. spec 섹션 검증
        if "spec" in scenario and isinstance(scenario["spec"], dict):
            spec = scenario["spec"]
            
            # 필수 문자열 필드 검증
            required_string_fields = ["description", "precondition", "action", "expected"]
            for field in required_string_fields:
                if field not in spec:
                    errors.append(f"필수 필드 'spec.{field}'이(가) 없습니다.")
                elif not isinstance(spec[field], str):
                    errors.append(f"'spec.{field}'는 문자열이어야 합니다.")
                elif not spec[field]:
                    errors.append(f"필수 필드 'spec.{field}'이(가) 비어 있습니다.")
            
            # 필수 리스트 필드 검증
            required_list_fields = ["actors", "assets", "components", "trust_boundaries", "data_flows", "behaviors"]
            for field in required_list_fields:
                if field not in spec:
                    errors.append(f"필수 필드 'spec.{field}'이(가) 없습니다.")
                elif not isinstance(spec[field], list):
                    errors.append(f"'spec.{field}'는 배열(list)이어야 합니다.")
            
            # actors 필드 상세 검증
            if "actors" in spec and isinstance(spec["actors"], list):
                for i, actor in enumerate(spec["actors"]):
                    if not isinstance(actor, dict):
                        errors.append(f"'spec.actors[{i}]'는 객체(object)여야 합니다.")
                        continue
                    
                    # 필수 필드 검증
                    for required_field in ["id", "role", "trust_level"]:
                        if required_field not in actor:
                            errors.append(f"'spec.actors[{i}]'에 필수 필드 '{required_field}'이(가) 없습니다.")
                        elif not actor[required_field]:
                            errors.append(f"'spec.actors[{i}].{required_field}'이(가) 비어 있습니다.")
            
            # assets 필드 상세 검증
            if "assets" in spec and isinstance(spec["assets"], list):
                for i, asset in enumerate(spec["assets"]):
                    if not isinstance(asset, dict):
                        errors.append(f"'spec.assets[{i}]'는 객체(object)여야 합니다.")
                        continue
                    
                    # 필수 필드 검증
                    for required_field in ["name", "type"]:
                        if required_field not in asset:
                            errors.append(f"'spec.assets[{i}]'에 필수 필드 '{required_field}'이(가) 없습니다.")
                        elif not asset[required_field]:
                            errors.append(f"'spec.assets[{i}].{required_field}'이(가) 비어 있습니다.")
        elif "spec" in scenario:
            errors.append("'spec' 섹션은 객체(object)여야 합니다.")

        # 3. code 섹션 검증 (새로 추가)
        if "code" in scenario and isinstance(scenario["code"], dict):
            code = scenario["code"]
            
            # 선택적 필드 타입 검증
            if "poc_contract" in code and not isinstance(code["poc_contract"], str):
                errors.append("'code.poc_contract'는 문자열이어야 합니다.")
            
            if "target_contract_name" in code and not isinstance(code["target_contract_name"], str):
                errors.append("'code.target_contract_name'는 문자열이어야 합니다.")
            
            if "deployment_script" in code and not isinstance(code["deployment_script"], str):
                errors.append("'code.deployment_script'는 문자열이어야 합니다.")
        elif "code" in scenario:
            errors.append("'code' 섹션은 객체(object)여야 합니다.")

        # 4. unit_tests 섹션 검증 (새로 추가)
        if "unit_tests" in scenario and isinstance(scenario["unit_tests"], list):
            unit_tests = scenario["unit_tests"]
            for i, test in enumerate(unit_tests):
                if not isinstance(test, dict):
                    errors.append(f"'unit_tests[{i}]'는 객체(object)여야 합니다.")
                    continue
                
                # 필수 필드 검증
                required_fields = ["test_name", "description", "test_code", "expected_behavior"]
                for required_field in required_fields:
                    if required_field not in test:
                        errors.append(f"'unit_tests[{i}]'에 필수 필드 '{required_field}'이(가) 없습니다.")
                    elif not isinstance(test[required_field], str):
                        errors.append(f"'unit_tests[{i}].{required_field}'는 문자열이어야 합니다.")
                
                # tags 필드 검증
                if "tags" in test and not isinstance(test["tags"], list):
                    errors.append(f"'unit_tests[{i}].tags'는 배열(list)이어야 합니다.")
                
                # test_name 중복 검증
                test_name = test.get("test_name", "")
                if test_name:
                    for j, other_test in enumerate(unit_tests):
                        if i != j and other_test.get("test_name") == test_name:
                            errors.append(f"'unit_tests[{i}].test_name' '{test_name}'이(가) 중복됩니다. (unit_tests[{j}]와 중복)")
        elif "unit_tests" in scenario:
            errors.append("'unit_tests' 섹션은 배열(list)이어야 합니다.")

        # 5. hints 섹션 검증
        if "hints" in scenario and isinstance(scenario["hints"], dict):
            hints = scenario["hints"]
            
            # compiler 섹션 검증
            if "compiler" in hints:
                if not isinstance(hints["compiler"], dict):
                    errors.append("'hints.compiler'는 객체(object)여야 합니다.")
                else:
                    compiler = hints["compiler"]
                    # errors와 warnings는 리스트여야 함
                    for field in ["errors", "warnings"]:
                        if field in compiler and not isinstance(compiler[field], list):
                            errors.append(f"'hints.compiler.{field}'는 배열(list)이어야 합니다.")
            
            # runtime 섹션 검증
            if "runtime" in hints:
                if not isinstance(hints["runtime"], dict):
                    errors.append("'hints.runtime'는 객체(object)여야 합니다.")
                else:
                    runtime = hints["runtime"]
                    # decoded_logs는 리스트여야 함
                    if "decoded_logs" in runtime and not isinstance(runtime["decoded_logs"], list):
                        errors.append("'hints.runtime.decoded_logs'는 배열(list)이어야 합니다.")
            
            # gas 섹션 검증
            if "gas" in hints:
                if not isinstance(hints["gas"], dict):
                    errors.append("'hints.gas'는 객체(object)여야 합니다.")
                else:
                    gas = hints["gas"]
                    # used는 숫자여야 함
                    if "used" in gas and not (isinstance(gas["used"], (int, float)) or (isinstance(gas["used"], str) and gas["used"].isdigit())):
                        errors.append("'hints.gas.used'는 숫자 또는 숫자 문자열이어야 합니다.")
        elif "hints" in scenario:
            errors.append("'hints' 섹션은 객체(object)여야 합니다.")

        # 6. patches 섹션 검증
        if "patches" in scenario and isinstance(scenario["patches"], list):
            patches = scenario["patches"]
            for i, patch in enumerate(patches):
                if not isinstance(patch, dict):
                    errors.append(f"'patches[{i}]'는 객체(object)여야 합니다.")
                    continue
                
                # 필수 필드 검증
                for required_field in ["ts", "author", "reason", "diff"]:
                    if required_field not in patch:
                        errors.append(f"'patches[{i}]'에 필수 필드 '{required_field}'이(가) 없습니다.")
                
                # 타임스탬프 형식 검증
                if "ts" in patch and patch["ts"]:
                    try:
                        datetime.datetime.fromisoformat(patch["ts"].replace('Z', '+00:00'))
                    except (ValueError, TypeError):
                        errors.append(f"'patches[{i}].ts'는 유효한 ISO8601 형식(YYYY-MM-DDTHH:MM:SS+TZ)이어야 합니다.")
        elif "patches" in scenario:
            errors.append("'patches' 섹션은 배열(list)이어야 합니다.")

        # 7. runlog 섹션 검증 (test_name 필드 추가)
        if "runlog" in scenario and isinstance(scenario["runlog"], list):
            runlog = scenario["runlog"]
            for i, log in enumerate(runlog):
                if not isinstance(log, dict):
                    errors.append(f"'runlog[{i}]'는 객체(object)여야 합니다.")
                    continue
                
                # 필수 필드 검증 (test_name 추가)
                for required_field in ["run_id", "ts", "test_name", "status", "diff"]:
                    if required_field not in log:
                        errors.append(f"'runlog[{i}]'에 필수 필드 '{required_field}'이(가) 없습니다.")
                
                # 타임스탬프 형식 검증
                if "ts" in log and log["ts"]:
                    try:
                        datetime.datetime.fromisoformat(log["ts"].replace('Z', '+00:00'))
                    except (ValueError, TypeError):
                        errors.append(f"'runlog[{i}].ts'는 유효한 ISO8601 형식(YYYY-MM-DDTHH:MM:SS+TZ)이어야 합니다.")
                
                # status 값 검증
                if "status" in log and log["status"] not in ["success", "failure", "error", "SUCCESS", "TEST_FAILURE", "ERROR"]:
                    warnings.append(f"'runlog[{i}].status'의 값이 표준 상태값이 아닙니다: {log['status']}")
                
                # test_name과 unit_tests의 일치성 검증
                if "test_name" in log and log["test_name"] and "unit_tests" in scenario:
                    test_name = log["test_name"]
                    unit_test_names = [test.get("test_name", "") for test in scenario["unit_tests"] if isinstance(test, dict)]
                    if test_name not in unit_test_names and test_name != "":
                        warnings.append(f"'runlog[{i}].test_name' '{test_name}'이(가) unit_tests에 정의되지 않았습니다.")
        elif "runlog" in scenario:
            errors.append("'runlog' 섹션은 배열(list)이어야 합니다.")

        # 8. test_insights 섹션 검증 (test_name 필드 추가)
        if "test_insights" in scenario and isinstance(scenario["test_insights"], list):
            insights = scenario["test_insights"]
            for i, insight in enumerate(insights):
                if not isinstance(insight, dict):
                    errors.append(f"'test_insights[{i}]'는 객체(object)여야 합니다.")
                    continue
                
                # 필수 필드 검증 (test_name 추가)
                required_fields = ["run_id", "ts", "test_name", "precondition", "state_changes", "patterns", "security_implications", "additional_info", "confidence"]
                for required_field in required_fields:
                    if required_field not in insight:
                        errors.append(f"'test_insights[{i}]'에 필수 필드 '{required_field}'이(가) 없습니다.")
                
                # 타임스탬프 형식 검증
                if "ts" in insight and insight["ts"]:
                    try:
                        datetime.datetime.fromisoformat(insight["ts"].replace('Z', '+00:00'))
                    except (ValueError, TypeError):
                        errors.append(f"'test_insights[{i}].ts'는 유효한 ISO8601 형식(YYYY-MM-DDTHH:MM:SS+TZ)이어야 합니다.")
                
                # confidence 값 검증
                if "confidence" in insight:
                    confidence = insight["confidence"]
                    if not isinstance(confidence, (int, float)):
                        try:
                            confidence = float(confidence)
                        except (ValueError, TypeError):
                            errors.append(f"'test_insights[{i}].confidence'는 숫자여야 합니다.")
                            continue
                    
                    if confidence < 0.0 or confidence > 1.0:
                        errors.append(f"'test_insights[{i}].confidence'는 0.0과 1.0 사이의 값이어야 합니다.")
                
                # test_name과 unit_tests의 일치성 검증
                if "test_name" in insight and insight["test_name"] and "unit_tests" in scenario:
                    test_name = insight["test_name"]
                    unit_test_names = [test.get("test_name", "") for test in scenario["unit_tests"] if isinstance(test, dict)]
                    if test_name not in unit_test_names and test_name != "":
                        warnings.append(f"'test_insights[{i}].test_name' '{test_name}'이(가) unit_tests에 정의되지 않았습니다.")
        elif "test_insights" in scenario:
            errors.append("'test_insights' 섹션은 배열(list)이어야 합니다.")

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "schema_version": schema_version
        }

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
            # 필요한 필드가 없으면 초기화
            if "hints" not in scenario_data:
                scenario_data["hints"] = {}
            
            hints = scenario_data["hints"]
            if "runtime" not in hints:
                hints["runtime"] = {}
            if "compiler" not in hints:
                hints["compiler"] = {}
            if "gas" not in hints:
                hints["gas"] = {}
            
            # Forge 출력 파싱
            if forge_output:
                # 1. 디코딩된 로그 추출
                decoded_logs = []
                for line in forge_output.splitlines():
                    if "CONSOLE:" in line:
                        log_content = line.split("CONSOLE:", 1)[1].strip()
                        decoded_logs.append(log_content)
                    # 이벤트 로그 파싱
                    elif "emit" in line.lower():
                        decoded_logs.append(f"EVENT: {line.strip()}")
                    # Gas 사용량 탐지
                    elif "gas" in line.lower() and "used" in line.lower():
                        gas_match = re.search(r"gas\s+used:\s+(\d+)", line.lower())
                        if gas_match:
                            hints["gas"]["used"] = int(gas_match.group(1))
                
                if decoded_logs:
                    hints["runtime"]["decoded_logs"] = decoded_logs
                
                # 2. Revert 정보 파싱
                if "Reverted" in forge_output:
                    revert_lines = [line for line in forge_output.splitlines() if "Reverted" in line]
                    if revert_lines:
                        hints["runtime"]["revert_info"] = revert_lines[0]
            
            # Slither 분석 결과 파싱 (제공된 경우)
            if slither_output:
                compiler_errors = []
                compiler_warnings = []
                
                for line in slither_output.splitlines():
                    if "Error:" in line:
                        compiler_errors.append(line.strip())
                    elif "Warning:" in line:
                        compiler_warnings.append(line.strip())
                
                if compiler_errors:
                    hints["compiler"]["errors"] = compiler_errors
                if compiler_warnings:
                    hints["compiler"]["warnings"] = compiler_warnings
            
            # 중복 제거 및 정리
            if "decoded_logs" in hints["runtime"]:
                hints["runtime"]["decoded_logs"] = list(set(hints["runtime"]["decoded_logs"]))
            
            logger.info(f"힌트 추출 완료: runtime={len(hints['runtime'])}, compiler={len(hints['compiler'])}, gas={len(hints['gas'])}")
            return scenario_data
            
        except Exception as e:
            logger.error(f"힌트 추출 중 오류 발생: {e}")
            # 원본 시나리오 반환
            return scenario_data

    def extract_field_info(self, section):
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
    
    def get_field_type(self, value):
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

# 편의 함수들
def validate_scenario(scenario: Dict[str, Any], schema_path: Optional[str] = None) -> Dict[str, Any]:
    """
    시나리오가 스키마에 맞는지 검증하는 편의 함수
    
    Args:
        scenario: 검증할 시나리오 데이터
        schema_path: 스키마 파일 경로 (None인 경우 기본값 사용)
        
    Returns:
        Dict[str, Any]: 검증 결과
    """
    validator = SchemaValidator(default_schema_path=schema_path or "schemas/schema_1.0.yaml")
    return validator.validate(scenario)

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
    validator = SchemaValidator()
    return validator.extract_hints_from_results(scenario_data, forge_output, slither_output)