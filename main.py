################################################################################
# MCP 서버
# v1.1.0 (2024-07-01)
# 최종 업데이트: DB 관련 코드 분리 및 모듈화
################################################################################
#
# 이 MCP 서버는 스마트컨트랙트 보안 검증 자동화의 핵심 백엔드입니다.
#
# [역할 및 구조]
# - MCP는 '테스트 우선' 접근 방식을 지원하여, 기존 시나리오가 없어도 최초 유닛테스트부터
#   시작하여 보안 검증을 수행할 수 있습니다.
# - 최초 유닛테스트 검증 후 LLM이 분석하여 생성한 메타데이터와 스펙을 
#   register_scenario로 등록하는 흐름을 주로 지원합니다.
# - 모든 "추론"(시나리오 생성/수정/피드백/코드 diff 해석 등)은 LLM(상위 계층)이 담당하며,
#   MCP는 LLM이 넘겨준 dict(시나리오, 변경사항 등)를 그대로 DB에 저장/업데이트/로깅만 합니다.
# - MCP는 입력값의 의미 해석, 적합성 판단, 자동 보정/생성 등은 일절 하지 않습니다.
#
# [주요 툴 및 사용 흐름]
#
# 1. execute_single_unit_test(sid, test_contract_name, foundry_root_path)
#    - 기존에 등록된 시나리오가 있는 경우에만 이 방식으로 테스트 실행
#    - 시나리오가 없으면 에러 반환(추가 시나리오를 먼저 등록해야 함)
#
# 2. register_scenario(scenario: dict)
#    - 유닛테스트 분석 후 LLM이 schema_1.0.yaml 구조에 맞게 추론한 시나리오를 등록
#    - meta, spec, code 등 모든 필드를 LLM이 완성해야 하며, MCP는 단순 저장만 함
#
# 3. update_scenario(sid: str, update_dict: dict)
#    - LLM이 추론한 시나리오 변경사항(피드백 등)을 입력받아 해당 시나리오를 업데이트
#    - MCP는 단순히 DB에 반영만 하며, 의미 해석/적합성 판단은 하지 않음
#
# 4. detect_test_code_diff(sid, test_contract_name, foundry_root_path)
#    - 테스트 코드(.t.sol) 변경(diff)을 감지하고 patch log에 기록합니다.
#    - MCP는 테스트 코드의 변경(diff) 자체만 patch log에 기록하며, 변경의 의미 해석/정합성 판단/추론은 하지 않습니다.
#    - 변경된 diff의 의미 해석, 시나리오와의 정합성 판단, 추가 피드백 등은 반드시 LLM(상위 계층)이 담당해야 합니다.
#    - MCP는 단순히 이전 스냅샷과 현재 파일을 비교하여 diff가 있으면 patch log에 남기고, 없으면 아무 기록도 하지 않습니다.
#    - LLM은 이 툴을 통해 테스트 코드의 변경 사항을 추적하고, 필요한 경우 시나리오 업데이트나 추가 분석을 수행할 수 있습니다.
#
# 5. analyze_test_results(sid, run_id, insights: Dict[str, Any]) -> dict
#    - 테스트 실행 결과에 대한 심층 분석을 수행하고 구조화된 인사이트를 저장합니다.
#    - LLM은 이 단계에서 다음과 같은 순차적 사고 과정을 거쳐야 합니다:
#      1. 심층 분석 (Deep Analysis):
#          - 실행 흐름 추적: 테스트가 어떤 단계를 거쳤는지 분석
#          - 상태 변화 감지: 계약 상태가 어떻게 변했는지 파악
#          - 조건부 행동 파악: 특정 조건에서의 동작 방식 이해
#          - 트리거 포인트 식별: 취약점이 발현되는 조건 파악
#      2. 가설 형성 (Hypothesis Formation):
#          - 동작 가설 수립: 관찰된 동작에 대한 원인과 메커니즘 제시
#          - 보안 영향 평가: 취약점의 잠재적 영향 평가
#          - 패턴 일반화: 특정 케이스에서 일반적인 취약점 패턴으로 확장
#      3. 가설 검증 (Hypothesis Verification):
#          - 데이터 재검토: 로그를 다시 검토하여 가설 지원 여부 확인
#          - 대안 가설 고려: 다른 설명 가능성 검토 및 배제
#          - 증거 기반 결론: 증거에 기반한 검증된 결론 도출
#      4. 인사이트 도출 (Insight Extraction):
#          - 핵심 발견 사항 정리: 검증된 핵심 인사이트 요약
#          - 구조화된 형식으로 변환: 아래 양식에 맞게 인사이트 구성
#          - 신뢰도 평가: 각 인사이트에 대한 신뢰도 수준 평가
#    - 이전 단계에서 수집한 테스트 결과에 대한 심층 분석을 수행합니다
#    - 순차적 사고 과정을 통해 발견한 인사이트를 구조화된 형태로 저장합니다
#    - 다음 단계인 메타 분석을 위한 기초 데이터를 제공합니다
#
# [순차적 사고 과정을 통한 분석 프로세스]
# 1. 초기 관찰 단계: 테스트 로그를 검토하고 기본적인 패턴 식별
# 2. 심층 분석 단계: 실행 흐름, 상태 변화, 조건부 행동 분석
# 3. 가설 형성 단계: 시스템 동작 및 보안 영향에 대한 가설 수립
# 4. 가설 검증 단계: 데이터를 재검토하여 가설 검증 및 대안 고려
# 5. 인사이트 도출 단계: 검증된 발견 사항을 구조화된 형태로 정리
#
# [모듈 구조]
# - main.py: MCP 서버의 주요 도구와 API 엔드포인트 제공
# - db_manager.py: 데이터베이스 관련 기능 (ScenarioDoc 클래스, CRUD 작업)
# - schema_validator.py: 스키마 검증 및 힌트 추출 기능
#
# [참고]
# - 각 필드/입력 구조/예시는 schema_1.0.yaml 및 실제 시나리오 예시(D-3.1.yaml 등) 참고
#
################################################################################

################################################################################
# 0. imports & logger
################################################################################
import os, json, uuid, sqlite3, datetime, logging, subprocess, glob, yaml, difflib
from dataclasses import dataclass, asdict, field, fields
from typing import Any, Dict, List, Optional

from mcp.server.fastmcp import FastMCP
# 외부 모듈 가져오기
from schema_validator import SchemaValidator, validate_scenario, extract_hints
from db_manager import ScenarioDoc, save_scenario, load_scenario, update_scenario_partial, delete_scenario, list_ids, add_runlog_entry, init_db

# 로거 설정
logger = logging.getLogger("dyn-schema-mcp")
logger.setLevel(logging.INFO)
logger.handlers.clear()  # 기존 핸들러 제거
file_handler = logging.FileHandler("mcp-server.log")
file_handler.setLevel(logging.INFO)
logger.addHandler(file_handler)

mcp = FastMCP("dyn-schema-mcp")

################################################################################
# 1. DB 설정 - _DB 환경 변수만 유지
################################################################################
_DB = os.getenv("SCENARIO_DB", "scenario_dyn.db")
# 나머지 DB 관련 기능은 db_manager.py로 이동

################################################################################
# 2. MCP tools (DB 기반 시나리오 관리, YAML은 import/export 용도만)
################################################################################

@mcp.tool()
async def get_scenario(sid: str) -> Dict[str, Any]:
    """
    [MCP 시스템 컨텍스트]
    DB에서 특정 시나리오의 전체 정보를 JSON 형태로 반환합니다.
    시나리오 기반 검증 및 분석에 사용되며, LLM은 이 정보를 바탕으로 시나리오를 이해하거나
    테스트 결과를 해석하고 새로운 인사이트를 도출할 수 있습니다.
    """
    logger.info(f"[get_scenario] 호출: {sid}")
    doc = load_scenario(sid)
    return json.loads(doc.to_json()) if doc else {}

@mcp.tool()
async def list_scenarios() -> List[str]:
    """
    [MCP 시스템 컨텍스트]
    DB에 저장된 모든 시나리오의 ID 목록을 반환합니다.
    사용자가 검증 대상을 선택하거나 전체 시나리오 현황을 파악하는 데 도움을 줍니다.
    """
    logger.info(f"[list_scenarios] 호출")
    return list_ids()

@mcp.tool()
def export_scenario_to_yaml(sid: str, path: str) -> str:
    """
    [MCP 시스템 컨텍스트]
    DB에 저장된 특정 시나리오를 YAML 파일 형태로 내보냅니다.
    시나리오의 외부 공유나 백업 목적으로 사용되며, 감사 중에는 DB를 기준으로 작업해야 합니다.
    """
    doc = load_scenario(sid)
    if not doc:
        raise ValueError("해당 시나리오가 없습니다.")
    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(json.loads(doc.to_json()), f, allow_unicode=True)
    logger.info(f"시나리오 {sid}를 {path}로 export 완료")
    return f"exported {sid} to {path}"

@mcp.tool()
async def bootstrap_from_yaml_files(folder="scenarios"):
    """
    [MCP 시스템 컨텍스트]
    지정된 폴더 내의 YAML 파일들을 읽어와 각 시나리오 정보를 DB에 일괄적으로 저장합니다.
    시스템 초기 설정이나 대량의 시나리오 마이그레이션에 사용되며, 
    이후에는 DB를 통해 시나리오를 관리합니다.
    """
    import glob as glob_module
    success, failed = [], []
    for fp in glob_module.glob(os.path.join(folder, "*.yaml")):
        try:
            with open(fp, "r") as f:
                raw = yaml.safe_load(f)
            doc = ScenarioDoc.from_json(json.dumps(raw))
            save_scenario(doc)
            success.append(os.path.basename(fp))
        except Exception as e:
            logger.error(f"bootstrap error: {fp} - {e}")
            failed.append({"file": os.path.basename(fp), "error": str(e)})
    logger.info(f"bootstrap complete: {len(success)} success, {len(failed)} failed")
    return {
        "success_count": len(success),
        "failed_count": len(failed),
        "success_files": success,
        "failed_files": failed
    }

################################################################################
# 3. MCP Foundry/UnitTest/ScenarioValidation 도구 클래스 구조
################################################################################

class FoundryTool:
    """
    Foundry 관련 도구: 유닛테스트 실행 및 로그 수집
    """

    def runUnitTest(self, test_contract_name=None, foundry_root_path=None, sid=None):
        """
        유닛테스트 실행 및 결과를 runlog에 자동 저장
        
        Args:
            test_contract_name: 테스트 컨트랙트 이름 (없으면 전체 테스트 실행)
            foundry_root_path: 테스트 파일이 위치한 디렉토리 경로
            sid: 시나리오 ID (runlog 기록용)
            
        Returns:
            tuple: (성공 여부, stdout, stderr)
        """
        try:
            logger.info(f"유닛테스트 실행: contract={test_contract_name}, path={foundry_root_path}")
            cmd = ["forge", "test", "-vvv"]
            if test_contract_name:
                cmd.extend(["--match-contract", test_contract_name])
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=foundry_root_path if foundry_root_path else None
            )
            
            success = result.returncode == 0
            status = "SUCCESS" if success else "TEST_FAILURE"
            diff = f"runUnitTest 실행: {test_contract_name if test_contract_name else '전체 테스트'}"
            
            # 결과 로깅
            log_msg = f"테스트 실행 결과: {status}, contract={test_contract_name}"
            if not success:
                logger.warning(f"{log_msg}, stderr={result.stderr[:200]}...")
            else:
                logger.info(log_msg)
            
            # 시나리오 ID가 제공되면 runlog에 기록
            if sid:
                run_id = add_runlog_entry(sid, status, diff, result.stdout, result.stderr)
                logger.info(f"테스트 결과 저장 완료: sid={sid}, run_id={run_id}")
                
            return success, result.stdout, result.stderr
            
        except Exception as e:
            error_msg = f"테스트 실행 오류: {str(e)}"
            logger.error(error_msg)
            if sid:
                add_runlog_entry(sid, "ERROR", "runUnitTest 실행 중 오류", "", str(e))
            return False, "", error_msg

    def collectForgeLogs(self, sid=None):
        """
        실행 로그를 DB(runlog) 또는 시나리오 객체의 runlog에서 수집
        
        Args:
            sid: 시나리오 ID (없으면 최신 전체 로그)
            
        Returns:
            dict: 실행 로그 정보
        """
        try:
            logger.info(f"Forge 로그 수집: sid={sid if sid else '(최신)'}")
            
            if sid:
                doc = load_scenario(sid)
                if doc and doc.runlog:
                    # 최신 실행 로그 반환
                    latest_log = doc.runlog[-1]
                    logger.info(f"시나리오 {sid}의 최신 로그 반환: run_id={latest_log.get('run_id')}")
                    return latest_log
                else:
                    logger.warning(f"시나리오 {sid}의 실행 로그가 없습니다.")
                    return {"error": f"해당 시나리오({sid})의 실행 로그가 없습니다."}
            else:
                # 전체 로그에서 최신 로그 조회
                from db_manager import _conn
                cx = _conn()
                row = cx.execute("SELECT * FROM runlog ORDER BY ts DESC LIMIT 1").fetchone()
                if row:
                    logger.info(f"전체 로그 중 최신 로그 반환: run_id={row['run_id']}")
                    return dict(row)
                else:
                    logger.warning("실행 로그가 없습니다.")
                    return {"error": "실행 로그가 없습니다."}
                    
        except Exception as e:
            error_msg = f"로그 수집 오류: {str(e)}"
            logger.error(error_msg)
            return {"error": error_msg}

class UnitTestGenTool:
    """
    시나리오 spec 기반 테스트 코드 생성 도구 (현재 비활성화됨)
    """
    def __init__(self):
        # 기존 템플릿 주석 처리 - 현재 사용되지 않음
        pass

    def generateTestCode(self, spec: dict):
        """테스트 코드 생성 (현재 비활성화됨)"""
        logger.warning("UnitTestGenTool.generateTestCode는 현재 비활성화되어 있습니다.")
        return "disabled_test.t.sol", "// 테스트 코드 생성 기능이 비활성화되었습니다." 

class ScenarioValidationTool:
    """
    시나리오와 forge 로그 기반 검증 도구
    """
    def __init__(self):
        self.schema_validator = SchemaValidator()
        
    def buildValidationPrompt(self, scenarioInfo: dict, forgeLogs: str):
        """
        검증용 프롬프트 생성
        
        Args:
            scenarioInfo: 시나리오 정보
            forgeLogs: Forge 실행 로그
            
        Returns:
            str: 검증 프롬프트
        """
        prompt = f"""
시나리오 ID: {scenarioInfo['meta']['id']}
카테고리: {scenarioInfo['meta']['category']}
설명: {scenarioInfo['spec']['description']}
전제조건: {scenarioInfo['spec'].get('precondition', '')}
수행동작: {scenarioInfo['spec'].get('action', '')}
기대결과: {scenarioInfo['spec'].get('expected', '')}

Forge 테스트 결과 로그:
{forgeLogs[:2000]}...  # 로그가 너무 긴 경우 일부만 포함

위 시나리오와 테스트 결과를 분석하여 다음을 판단해주세요:
1. 테스트가 성공적으로 실행되었는가?
2. 시나리오의 기대 결과와 실제 결과가 일치하는가?
3. 보안 취약점이 효과적으로 검증되었는가?
4. 개선이 필요한 부분이 있다면 무엇인가?
"""
        return prompt

    def runValidation(self, unittest_path: str):
        """
        unittest(.t.sol) 실행 및 검증
        
        Args:
            unittest_path: 테스트 파일 경로
            
        Returns:
            tuple: (상태, 메시지, 표준출력, 표준에러)
        """
        try:
            # Forge 테스트 실행
            forge_tool = FoundryTool()
            test_contract_name = os.path.basename(unittest_path).replace(".t.sol", "")
            success, stdout, stderr = forge_tool.runUnitTest(test_contract_name)
            
            # 결과 분석
            if success:
                return "SUCCESS", "테스트가 성공적으로 실행되었습니다.", stdout, stderr
            else:
                return "FAILURE", "테스트 실행 중 오류가 발생했습니다.", stdout, stderr
        except Exception as e:
            logger.error(f"검증 실행 오류: {e}")
            return "ERROR", f"검증 과정에서 오류 발생: {str(e)}", "", str(e)

# SchemaAnalysisTool 클래스를 외부 SchemaValidator를 사용하도록 대체
class SchemaAnalysisTool:
    """
    스키마 파일 분석 및 정보 추출 도구
    schema_validator.py의 SchemaValidator를 활용
    """
    def __init__(self):
        self.validator = SchemaValidator()
    
    def loadSchemaFile(self, schema_path: str = "mcp-server/schemas/schema_1.0.yaml") -> Dict[str, Any]:
        """
        스키마 파일을 로드하고 구조를 분석
        
        Args:
            schema_path: 스키마 파일 경로
            
        Returns:
            dict: 스키마 구조 정보
        """
        try:
            schema_data = self.validator.load_schema(schema_path)
            
            logger.info(f"스키마 파일 로드 성공: {schema_path}")
            return {
                "success": True,
                "schema_version": schema_data.get("schema_version", "unknown"),
                "structure": {
                    "meta": self.validator.extract_field_info(schema_data.get("meta", {})),
                    "spec": self.validator.extract_field_info(schema_data.get("spec", {})),
                    "hints": self.validator.extract_field_info(schema_data.get("hints", {})),
                    "patches": self.validator.extract_field_info(schema_data.get("patches", [])),
                    "runlog": self.validator.extract_field_info(schema_data.get("runlog", [])),
                    "test_insights": self.validator.extract_field_info(schema_data.get("test_insights", []))
                },
                "schema_data": schema_data  # 전체 스키마 데이터
            }
        except Exception as e:
            logger.error(f"스키마 파일 로드 오류: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def validateScenario(self, scenario: Dict[str, Any], schema_path: str = "schemas/schema_1.0.yaml") -> Dict[str, Any]:
        """
        시나리오가 스키마 구조에 맞는지 검증
        
        Args:
            scenario: 검증할 시나리오 데이터
            schema_path: 스키마 파일 경로
            
        Returns:
            dict: 검증 결과
        """
        return validate_scenario(scenario, schema_path)

    def extractHintsFromResults(self, scenario_data: dict, forge_output: str, slither_output: str = None):
        """
        테스트 결과에서 힌트 추출하여 시나리오 업데이트
        
        Args:
            scenario_data: 시나리오 데이터
            forge_output: Forge 실행 결과
            slither_output: Slither 분석 결과 (선택적)
            
        Returns:
            dict: 힌트가 업데이트된 시나리오 데이터
        """
        return extract_hints(scenario_data, forge_output, slither_output)

# sid → 컨트랙트/테스트 파일명 변환 함수
def sid_to_contract_name(sid: str) -> str:
    """
    시나리오 ID(sid)를 기반으로 유효한 테스트 파일명 생성
    
    Args:
        sid: 시나리오 ID
        
    Returns:
        str: 테스트 파일명 (예: D_3_1 → D_3_1.t.sol)
    """
    return f"{sid}.t.sol"

class LocalMCPServer:
    """
    MCP 서버: 시나리오 처리 및 도구 디스패치
    """
    
    def __init__(self):
        """도구 객체 초기화"""
        logger.info("LocalMCPServer 초기화")
        self.foundry_tool = FoundryTool()
        self.unittest_gen_tool = UnitTestGenTool()
        self.validation_tool = ScenarioValidationTool()
        self.schema_tool = SchemaAnalysisTool()

    def process_single_scenario_test(self, sid: str, test_contract_name: str, foundry_root_path: str) -> dict:
        """
        단일 시나리오 단위 테스트 실행 및 결과 기록
        
        Args:
            sid: 시나리오 ID
            test_contract_name: 테스트 컨트랙트 이름
            foundry_root_path: Foundry 프로젝트 루트 경로
            
        Returns:
            dict: 테스트 실행 결과
        """
        logger.info(f"단일 시나리오 테스트 처리: sid={sid}, contract={test_contract_name}")
        
        # 시나리오 로드 및 확인
        doc = load_scenario(sid)
        if not doc:
            error_msg = f"시나리오 {sid}를 찾을 수 없습니다."
            logger.error(error_msg)
            return {
                "success": False,
                "message": error_msg,
                "stdout": "",
                "stderr": "Scenario not found"
            }
            
        try:
            # 1. 현재 테스트 코드 읽기
            test_file_relative_path = os.path.join("test", "generated", sid_to_contract_name(sid))
            test_file_full_path = os.path.join(foundry_root_path, test_file_relative_path)
            
            current_code = ""
            try:
                with open(test_file_full_path, "r", encoding="utf-8") as f:
                    current_code = f.read()
                logger.info(f"테스트 코드 로드 완료: {test_file_full_path}")
            except FileNotFoundError:
                logger.warning(f"테스트 파일 {test_file_full_path}를 찾을 수 없습니다. 일반 테스트 파일로 계속합니다.")
                # 일반 테스트 파일 경로 시도
                test_file_alt_path = os.path.join(foundry_root_path, "test", f"{test_contract_name}.t.sol")
                try:
                    with open(test_file_alt_path, "r", encoding="utf-8") as f:
                        current_code = f.read()
                    logger.info(f"일반 테스트 코드 로드 완료: {test_file_alt_path}")
                except FileNotFoundError:
                    logger.warning(f"일반 테스트 파일 {test_file_alt_path}도 찾을 수 없습니다. 빈 코드로 진행합니다.")
                
            # 2. 코드 변경 감지 및 기록 (test_code_snapshots 필드 직접 사용)
            last_known_code = doc.test_code_snapshots.get(test_contract_name, "")
            
            if last_known_code != current_code:
                import difflib
                diff = difflib.unified_diff(
                    last_known_code.splitlines(),
                    current_code.splitlines(),
                    fromfile=f"previous_{test_contract_name}",
                    tofile=f"current_{test_contract_name}",
                    lineterm="\n"
                )
                diff_text = "".join(diff)
                
                if diff_text:
                    logger.info(f"테스트 코드 변경 감지: {test_contract_name}")
                    doc.add_patch(
                        author="user", # 또는 system-auto-detect 등 상황에 맞게
                        reason=f"{test_contract_name} 변경 감지",
                        diff_text=diff_text
                    )
                doc.test_code_snapshots[test_contract_name] = current_code
                
            # 3. 유닛테스트 실행
            contract_name = test_contract_name.replace('.t.sol','')
            logger.info(f"유닛테스트 실행: {contract_name}")
            
            test_result = self.foundry_tool.runUnitTest(test_contract_name=contract_name, foundry_root_path=foundry_root_path)
            success, stdout, stderr = test_result if isinstance(test_result, tuple) else (False, "", "Tool execution failed")
            
            # 4. runlog 기록
            status = "SUCCESS" if success else "TEST_FAILURE"
            diff_for_runlog = f"[{sid}] process_single_scenario_test 실행: {contract_name}"
            
            # 직접 runlog에 추가하고 save_scenario 호출
            run_id = doc.add_run_log(
                run_id=str(uuid.uuid4()), 
                status=status, 
                diff=diff_for_runlog, 
                stdout=stdout, 
                stderr=stderr
            )
            
            # 5. hints 업데이트
            doc.update_hints_from_run(run_id, status, stdout, stderr)
            
            # 6. 변경사항 DB에 저장
            save_scenario(doc)
            
            logger.info(f"단일 시나리오 테스트 완료: sid={sid}, run_id={run_id}, status={status}")
            return {
                "success": success,
                "stdout": stdout,
                "stderr": stderr,
                "run_id": run_id
            }
            
        except Exception as e:
            error_msg = f"단일 시나리오 테스트 처리 중 오류: {str(e)}"
            logger.error(error_msg)
            return {
                "success": False,
                "message": error_msg,
                "stdout": "",
                "stderr": str(e)
            }

    # --- 도구 디스패치 ---
    def dispatchTool(self, toolName: str, **kwargs):
        """
        도구 이름에 따라 해당 도구 실행
        
        Args:
            toolName: 실행할 도구 이름
            **kwargs: 도구별 필요한 매개변수
            
        Returns:
            다양한 형태의 도구 실행 결과
        """
        logger.info(f"도구 디스패치: {toolName}, params={kwargs}")
        
        tools = {
            # Foundry 도구
            "test": self.foundry_tool.runUnitTest,
            "logs": self.foundry_tool.collectForgeLogs,
            # 테스트 생성 및 검증 도구
            "validate": self.validation_tool.runValidation,
            # 스키마 분석 도구
            "analyze_schema": self.schema_tool.loadSchemaFile,
            "validate_schema": self.schema_tool.validateScenario,
            "extract_hints": self.schema_tool.extractHintsFromResults,
            "validate_scenario": self.validateScenarioAgainstSchema,
            # 통합 시나리오 처리
            "process_single_scenario_test": self.process_single_scenario_test
        }
        
        if toolName not in tools:
            error_msg = f"알 수 없는 도구: {toolName}"
            logger.error(error_msg)
            return {
                "status": "ERROR",
                "message": error_msg
            }
            
        try:
            # 도구 실행
            result = tools[toolName](**kwargs)
            
            # runlog에 기록 (sid가 제공된 경우)
            sid = kwargs.get("sid", None)
            if sid and isinstance(result, dict) and "status" in result:
                status = result.get("status", "UNKNOWN")
                message = result.get("message", "")
                stdout = result.get("stdout", "")
                stderr = result.get("stderr", "")
                diff = f"{toolName} 실행: {message}"
                add_runlog_entry(sid, status, diff, stdout, stderr)
                
            logger.info(f"도구 실행 완료: {toolName}")
            return result
            
        except Exception as e:
            error_msg = f"{toolName} 도구 실행 오류: {str(e)}"
            logger.error(error_msg)
            
            # runlog에 기록 (sid가 제공된 경우)
            sid = kwargs.get("sid", None)
            if sid:
                diff = f"{toolName} 도구 실행 중 오류 발생"
                add_runlog_entry(sid, "ERROR", diff, "", str(e))
                
            return {
                "status": "ERROR",
                "message": error_msg
            }

    def createScenarioTemplate(self):
        """
        새로운 시나리오 템플릿 생성
        
        Returns:
            dict: 기본 시나리오 템플릿
        """
        return self.schema_tool.createScenarioTemplate()
    
    def extractHintsFromResults(self, scenario_id: str, forge_output: str, slither_output: str = None):
        """
        테스트 결과에서 힌트 추출하여 시나리오 업데이트
        
        Args:
            scenario_id: 시나리오 ID
            forge_output: Forge 실행 결과
            slither_output: Slither 분석 결과 (선택적)
            
        Returns:
            dict: 힌트가 업데이트된 시나리오 데이터
        """
        try:
            # 시나리오 로드
            scenario_doc = load_scenario(scenario_id)
            if not scenario_doc:
                return {
                    "success": False,
                    "message": f"시나리오 ID '{scenario_id}'를 찾을 수 없습니다."
                }
            
            # JSON으로 변환
            scenario_data = json.loads(scenario_doc.to_json())
            
            # 힌트 추출 및 업데이트 - schema_validator.py 사용
            updated_scenario = extract_hints(scenario_data, forge_output, slither_output)
            
            # 업데이트된 시나리오 저장
            updated_doc = ScenarioDoc.from_json(json.dumps(updated_scenario))
            save_scenario(updated_doc)
            
            return {
                "success": True,
                "message": f"시나리오 '{scenario_id}'의 힌트가 업데이트되었습니다."
            }
        except Exception as e:
            logger.error(f"힌트 추출 중 오류 발생: {e}")
            return {
                "success": False,
                "message": f"힌트 추출 중 오류 발생: {str(e)}"
            }
    
    def validateScenarioAgainstSchema(self, scenario_id: str):
        """
        시나리오가 스키마에 맞는지 검증
        
        Args:
            scenario_id: 시나리오 ID
            
        Returns:
            dict: 검증 결과
        """
        try:
            # 시나리오 로드
            scenario_doc = load_scenario(scenario_id)
            if not scenario_doc:
                return {
                    "valid": False,
                    "errors": [f"시나리오 ID '{scenario_id}'를 찾을 수 없습니다."]
                }
            
            # JSON으로 변환
            scenario_data = json.loads(scenario_doc.to_json())
            
            # 스키마 검증 - schema_validator.py 직접 사용
            validation_result = validate_scenario(scenario_data)
            
            return validation_result
        except Exception as e:
            logger.error(f"스키마 검증 중 오류 발생: {e}")
            return {
                "valid": False,
                "errors": [f"스키마 검증 중 오류 발생: {str(e)}"]
            }

@mcp.tool()
async def scenario_context(sid: str, test_contract_name: str, foundry_root_path: str) -> Dict[str, Any]:
    """
    [MCP 시스템 컨텍스트]
    [순차적 검증 프로세스: 1단계 - 시나리오 컨텍스트 이해]
    
    스마트 컨트랙트 순차적 검증 프로세스의 첫 번째 단계로, 시나리오의 전체 컨텍스트를 로드합니다.
    주어진 시나리오 ID(sid)에 해당하는 테스트 시나리오의 모든 메타데이터, 스펙, 코드 조각, 힌트, 
    실행 로그, 누적 인사이트 등을 종합적으로 제공합니다.
    
    [테스트 우선 접근법에서의 중요 참고사항]
    - 이 함수는 이미 등록된 시나리오에만 사용할 수 있습니다
    - 최초 유닛테스트 분석 시에는 먼저 테스트 코드를 직접 검토한 후 register_scenario로 시나리오를 등록해야 합니다
    - 시나리오가 등록되지 않은 상태에서 호출 시 빈 dict({})가 반환됩니다
    
    이 도구는 순차적 검증 프로세스에서 다음과 같은 역할을 합니다:
    1. 분석할 시나리오의 기본 정보와 취약점 유형을 이해합니다
    2. 시나리오의 예상 동작과 테스트 목적을 파악합니다
    3. 후속 단계(테스트 실행, 분석 등)의 기반이 되는 컨텍스트를 설정합니다
    
    이 단계에서 LLM은 순차적 사고의 초기 관찰 단계를 준비하며, 시나리오에 대한
    전반적인 이해를 구축해야 합니다.
    
    [시나리오가 없는 경우의 워크플로우]
    1. 최초 유닛테스트 코드를 직접 분석
    2. register_scenario로 시나리오 등록 
    3. 이후 scenario_context로 등록된 시나리오 조회
    
    [다음 단계]
    - 컨텍스트 이해 후 execute_single_unit_test 도구를 사용하여 테스트를 실행하세요.
    
    [매개변수]
    - sid: 시나리오 ID (예: "D_3_1")
    - test_contract_name: 테스트 컨트랙트 이름 (예: "MCPTest_D_3_1")
    - foundry_root_path: Foundry 프로젝트 디렉토리 경로 (예: "/foundry_project")
    """
    logger.info(f"[scenario_context] 호출: sid={sid}, test_contract_name={test_contract_name}, foundry_root_path={foundry_root_path}")
    doc = load_scenario(sid)
    if doc:
        logger.info(f"시나리오 {sid} 발견. 컨텍스트 반환.")
        return json.loads(doc.to_json())
    else:
        logger.info(f"시나리오 {sid} 없음. 빈 dict 반환.")
        return {}

@mcp.tool()
async def execute_single_unit_test(sid: str, test_contract_name: str, foundry_root_path: str):
    """
    [MCP 시스템 컨텍스트]
    [순차적 검증 프로세스: 2단계 - 테스트 실행 및 기초 데이터 수집]
    
    스마트 컨트랙트 순차적 검증 프로세스의 두 번째 단계로, 시나리오에 대한 테스트를 실행하고
    분석을 위한 기초 데이터를 수집합니다.
    
    이 도구는 순차적 검증 프로세스에서 다음과 같은 역할을 합니다:
    1. 지정된 테스트 컨트랙트에 대한 Foundry 유닛 테스트를 실행합니다
    2. 테스트 실행 결과(stdout, stderr, 상태 등)를 수집합니다
    3. 결과를 DB의 runlog에 기록하고 run_id를 생성합니다
    
    [중요: 테스트 우선 접근법]
    - 이 함수는 반드시 DB에 등록된 시나리오가 있어야 작동합니다
    - 최초 분석 시에는 먼저 유닛테스트를 실행/분석한 후 register_scenario로 시나리오를 등록해야 합니다
    - 시나리오가 등록되지 않은 상태에서 이 함수 호출 시 에러가 발생합니다
    
    [이전 단계]
    - scenario_context 도구를 통해 시나리오의 전체 컨텍스트를 이해했어야 합니다
    - 또는 최초 검증 시에는 시나리오를 register_scenario로 먼저 등록했어야 합니다
    
    [다음 단계]
    - get_single_unit_test_log 도구를 사용하여 반환된 run_id로 상세 실행 결과를 조회하세요
    - 그 후 analyze_test_results 도구를 사용하여 순차적 사고 과정을 통한 분석을 수행하세요
    
    [중요]
    - 반환되는 run_id 값을 기록해두세요 - 이는 다음 단계들에서 사용됩니다
    - 이 툴은 테스트 실행만 담당하며, 테스트 코드 생성이나 시나리오 자동 수정은 하지 않습니다
    
    [매개변수]
    - sid: 시나리오 ID (실행 로그 기록용)
    - test_contract_name: 테스트 컨트랙트 이름 (예: MCPTest_D_3_1)
    - foundry_root_path: foundry 프로젝트 디렉토리 경로 (예: /foundry_project)
    
    [반환 값]
    - success: 테스트 성공 여부
    - stdout: 테스트 표준 출력
    - stderr: 테스트 표준 에러
    - run_id: 실행 ID (다음 단계에서 사용)
    """
    logger.info(f"[execute_single_unit_test] 호출: sid={sid}, test_contract_name={test_contract_name}")
    doc = load_scenario(sid)
    if not doc:
        error_msg = f"시나리오 {sid}가 DB에 존재하지 않습니다. 먼저 시나리오를 등록하세요."
        logger.error(error_msg)
        return {"error": error_msg}
    
    try:
        # 1. 테스트 실행을 위한 준비
        contract_name = test_contract_name.replace('.t.sol','')
        logger.info(f"유닛테스트 실행 준비: {contract_name}")
        
        # 2. Foundry 테스트 실행
        forge_tool = FoundryTool()
        success, stdout, stderr = forge_tool.runUnitTest(
            test_contract_name=contract_name, 
            foundry_root_path=foundry_root_path
        )
        
        # 3. 결과 저장을 위한 정보 설정
        status = "SUCCESS" if success else "TEST_FAILURE"
        diff_for_runlog = f"[{sid}] execute_single_unit_test: {contract_name}"
        run_id = str(uuid.uuid4())  # 새 run_id 생성
        
        # 4. 시나리오 객체에 직접 로그 추가
        doc.add_run_log(
            run_id=run_id,
            status=status,
            diff=diff_for_runlog,
            stdout=stdout,
            stderr=stderr
        )
        
        # 5. 로그 정보를 바탕으로 힌트 업데이트
        doc.update_hints_from_run(run_id, status, stdout, stderr)
        
        # 6. 시나리오 저장
        success_save = save_scenario(doc)
        if not success_save:
            logger.warning(f"시나리오 {sid} 저장 실패")
        
        # 7. 글로벌 runlog 테이블에도 로그 저장
        add_runlog_entry(sid, status, diff_for_runlog, stdout, stderr)
        
        logger.info(f"실행 완료: sid={sid}, run_id={run_id}, status={status}")
        
        # 8. 결과 반환
        return {
            "success": success,
            "stdout": stdout,
            "stderr": stderr,
            "run_id": run_id
        }
    except Exception as e:
        error_msg = f"테스트 실행 중 오류 발생: {str(e)}"
        logger.error(error_msg)
        return {
            "success": False,
            "message": error_msg,
            "stdout": "",
            "stderr": str(e)
        }

@mcp.tool()
async def get_unit_test_logs(sid: str) -> list:
    """
    [MCP 시스템 컨텍스트]
    특정 시나리오 ID(sid)에 대한 모든 유닛테스트 실행 결과(runlog) 기록들을 시간순으로 조회합니다.
    LLM은 이 로그들을 바탕으로 테스트 히스토리를 파악하거나, 특정 실행 결과를 분석할 수 있습니다.
    
    [반환값]
    - 시나리오의 `runlog` 필드에 저장된 모든 실행 로그 목록 (각 로그는 run_id, 상태, stdout, stderr 등 포함)
    """
    doc = load_scenario(sid)
    if not doc:
        return {"error": f"시나리오 {sid}를 찾을 수 없습니다."}
    return doc.runlog

@mcp.tool()
def register_scenario(scenario: dict) -> dict:
    """
    [MCP 시스템 컨텍스트]
    [테스트 우선 접근법을 위한 핵심 도구]
    
    최초 유닛테스트를 분석한 후 LLM이 생성한 시나리오를 등록하는 도구입니다.
    이는 테스트 우선 워크플로우의 핵심 단계로, 유닛테스트 분석을 시나리오화하여 
    이후 체계적인 검증이 가능하게 합니다.
    
    - LLM은 테스트 코드와 실행 결과를 분석하여 schema_1.0.yaml의 구조(meta, spec, code, hints 등)에 
      맞는 시나리오 dict를 생성해야 합니다.
    - MCP는 입력값을 그대로 DB에 등록만 하며, 자동 추론/보정은 하지 않습니다.
    - meta.id는 반드시 고유해야 하며, 이미 등록된 id는 에러가 발생합니다.
    - 모든 필드는 schema_1.0.yaml의 타입/예시를 참고하여 생성해야 합니다.
    - 값이 없는 경우에도 빈 값(""), [], {{}} 등으로 명시해야 합니다.
    
    [테스트 우선 워크플로우에서의 위치]
    1. 최초 유닛테스트 실행 및 분석 완료
    2. ➡️ 현재 단계: 시나리오 등록
    3. 이후 execute_single_unit_test 등으로 체계적 검증 진행
    
    [필요한 입력 구조]
    {
      "meta": {
        "id": "고유 시나리오 ID",
        "title": "시나리오 제목",
        "category": "취약점 카테고리",
        "severity": "심각도 수준",
        ...
      },
      "spec": {
        "description": "시나리오 설명",
        "actors": [...],
        "assets": [...],
        ...
      },
      "code": {
        "target_contract_name": "대상 컨트랙트명",
        ...
      },
      ...
    }
    
    [반환값]
    - success: 등록 성공 여부
    - message: 상태 메시지
    """
    sid = scenario.get("meta", {}).get("id")
    if not sid:
        return {"error": "meta.id 필드는 필수입니다."}
    if load_scenario(sid):
        return {"error": f"시나리오 {sid}가 이미 존재합니다."}
    save_scenario(ScenarioDoc.from_json(json.dumps(scenario)))
    return {"success": True, "message": f"시나리오 {sid}가 등록되었습니다."}

@mcp.tool()
def update_scenario(sid: str, update_dict: dict) -> dict:
    """
    [MCP 시스템 컨텍스트]
    [순차적 검증 프로세스: 선택적 최종 단계 - 시나리오 개선]
    
    스마트 컨트랙트 순차적 검증 프로세스의 선택적 최종 단계로, 분석 과정에서 얻은 
    깊은 이해를 바탕으로 시나리오 자체를 개선하고 발전시킵니다.
    
    - 이 도구는 순차적 검증 프로세스에서 다음과 같은 역할을 합니다:
      1. 누적된 인사이트와 메타 분석 결과를 바탕으로 시나리오 정보를 업데이트합니다
      2. 더 정확한 취약점 모델링, 테스트 개선, 실행 관련 정보 등을 갱신합니다
      3. 순환적 검증 과정의 연결고리 역할을 하여 지속적 개선을 가능하게 합니다
    
    - 중요] 시나리오의 핵심 정의인 `meta` 및 `spec` 필드는 고정이며, 이 툴을 통해 수정할 수 없습니다.
    이 툴은 주로 시나리오 실행 및 분석 과정에서 파생되는 정보들을 `code`, `hints`, `test_insights` 
    등의 필드에 누적하거나 업데이트하기 위한 목적입니다.
    
    LLM은 이 단계에서 다음과 같은 과정을 수행할 수 있습니다:
    
    1. 테스트 코드 개선:
       - 메타 분석을 통해 식별된 추가 테스트 케이스 구현
       - 더 효과적인 검증을 위한 테스트 로직 개선
       - 엣지 케이스 및 코너 케이스 처리 추가
    
    2. 힌트 정보 업데이트:
       - 실행 과정에서 발견된 중요 패턴 기록
       - 특정 조건에서의 동작 방식 문서화
       - 가스 사용량, 상태 변화 등의 런타임 정보 기록
    
    3. 시나리오 문서 강화:
       - 발견된 취약점 메커니즘의 더 정확한 설명 추가
       - 근본 원인 및 영향에 대한 심층 분석 기록
       - 관련 취약점 패턴 및 참조 정보 추가
    
    [이전 단계]
    - get_cumulative_insights 도구를 통해 누적 인사이트에 대한 메타 분석을 수행했어야 합니다
    
    [다음 단계 - 순환적 프로세스]
    - 개선된 시나리오를 바탕으로 새로운 테스트를 실행하고 추가 인사이트를 수집할 수 있습니다
    - scenario_context 도구로 다시 시작하여 개선된 컨텍스트에서 전체 검증 프로세스를 반복합니다
    
    [매개변수]
    - sid: 시나리오 ID
    - update_dict: 업데이트할 필드와 값을 포함하는 딕셔너리
      * 업데이트 가능한 최상위 필드: hints, patches, runlog, extras, test_insights, test_code_snapshots
      * 예시: {"hints": {"runtime": {"new_hint": "value"}}, "patches": [{"author": "user", "reason": "reason", "diff": "diff"}], "runlog": [{"run_id": "run_id", "status": "status", "diff": "diff", "stdout": "stdout", "stderr": "stderr"}], "extras": {"new_extra": "value"}, "test_insights": [{"run_id": "run_id", "insight": {"precondition": "precondition", "state_changes": "state_changes", "patterns": "patterns", "security_implications": "security_implications", "additional_info": "additional_info", "confidence": 0.5}}], "test_code_snapshots": {"contract_name": "code"}}
    
    [반환 값]
    - success: 업데이트 성공 여부
    - message: 상태 메시지
    """
    doc = load_scenario(sid)
    if not doc:
        return {"error": f"시나리오 {sid}가 존재하지 않습니다."}

    # meta 또는 spec 필드가 업데이트 시도 목록에 있는지 확인
    if "meta" in update_dict or "spec" in update_dict:
        disallowed_keys = [k for k in ["meta", "spec"] if k in update_dict]
        return {"error": f"시나리오의 핵심 정의인 '{', '.join(disallowed_keys)}' 필드는 수정할 수 없습니다. 'hints', 'patches', 'runlog', 'extras', 'test_insights', 'test_code_snapshots' 필드만 업데이트 가능합니다."}
    # prompt_ctx가 update_dict에 있고, 허용되지 않는 키로 처리 (명시적 제거)
    if "prompt_ctx" in update_dict: # 추가된 검사
        return {"error": f"'prompt_ctx' 필드는 스키마에서 제거되어 업데이트할 수 없습니다."}

    doc_dict = asdict(doc)
    
    # 허용된 최상위 레벨 키
    allowed_top_level_keys_to_update = {"hints", "patches", "runlog", "extras", "test_insights", "test_code_snapshots"} # prompt_ctx 제거
    
    updated_something = False

    # 재귀적 업데이트 함수
    def _recursive_update(original, updates):
        for key, value in updates.items():
            if isinstance(value, dict) and isinstance(original.get(key), dict):
                original[key] = _recursive_update(original.get(key, {}), value) # 원본에 키가 없을 경우 대비
            else:
                original[key] = value
        return original

    for top_key, top_value in update_dict.items():
        if top_key in allowed_top_level_keys_to_update:
            # doc_dict에 해당 키가 있는지 확인 (ScenarioDoc 구조에 따라 항상 있어야 함)
            if top_key in doc_dict:
                if isinstance(doc_dict[top_key], dict) and isinstance(top_value, dict):
                    # 원본 필드와 업데이트 값이 모두 딕셔너리인 경우, 재귀적으로 업데이트
                    _recursive_update(doc_dict[top_key], top_value)
                else:
                    # 리스트나 다른 타입의 필드는 전체 값으로 교체
                    doc_dict[top_key] = top_value
                updated_something = True
            # else: 허용된 키지만 doc_dict에 없는 경우는 ScenarioDoc의 기본값으로 처리되므로 일반적으로 발생하지 않음
    
    if not updated_something:
        # update_dict가 비어 있거나, 허용되지 않은 키 (meta/spec 제외)만 포함된 경우
        return {"success": True, "message": "업데이트할 유효한 내용이 없거나, 모든 업데이트가 허용되지 않는 필드에 대한 것이었습니다."}

    save_scenario(ScenarioDoc.from_json(json.dumps(doc_dict)))
    return {"success": True, "message": f"시나리오 {sid}의 허용된 필드가 업데이트되었습니다."}

@mcp.tool()
def detect_test_code_diff(sid: str, test_contract_name: str, foundry_root_path: str) -> dict:
    """
    [MCP 시스템 컨텍스트]
    테스트 코드(.t.sol) 변경(diff) 감지 및 기록 툴입니다.
    - MCP는 테스트 코드의 변경(diff) 자체만 patch log에 기록하며, 변경의 의미 해석/정합성 판단/추론은 하지 않습니다.
    - 변경된 diff의 의미 해석, 시나리오와의 정합성 판단, 추가 피드백 등은 반드시 LLM(상위 계층)이 담당해야 합니다.
    - MCP는 단순히 이전 스냅샷과 현재 파일을 비교하여 diff가 있으면 patch log에 남기고, 없으면 아무 기록도 하지 않습니다.
    LLM은 이 툴을 통해 테스트 코드의 변경 사항을 추적하고, 필요한 경우 시나리오 업데이트나 추가 분석을 수행할 수 있습니다.

    [매개변수]
    - sid: 시나리오 ID
    - test_contract_name: 테스트 컨트랙트 이름 (예: MCPTest_D_3_1)
    - foundry_root_path: Foundry 프로젝트 루트 경로
    
    [반환값]
    - message: 처리 결과 메시지
    - diff: 감지된 변경사항 (있는 경우)
    """
    import os, difflib
    doc = load_scenario(sid)
    if not doc:
        return {"error": f"시나리오 {sid}가 존재하지 않습니다."}
    test_file_relative_path = os.path.join("test", "generated", f"{test_contract_name}.t.sol")
    test_file_full_path = os.path.join(foundry_root_path, test_file_relative_path)
    try:
        with open(test_file_full_path, "r", encoding="utf-8") as f:
            current_code = f.read()
    except FileNotFoundError:
        return {"error": f"테스트 파일 {test_file_full_path}를 찾을 수 없습니다."}
    doc.code.setdefault("test_code_snapshots", {})
    last_known_code = doc.code["test_code_snapshots"].get(test_contract_name, "")
    
    if current_code != last_known_code:
        # diff 생성 및 저장
        diff = difflib.unified_diff(
            last_known_code.splitlines(keepends=True),
            current_code.splitlines(keepends=True),
            fromfile=f"previous_{test_contract_name}.t.sol",
            tofile=f"current_{test_contract_name}.t.sol"
        )
        diff_text = "".join(diff)
        
        # 코드 스냅샷 업데이트
        doc.code["test_code_snapshots"][test_contract_name] = current_code
        
        # 패치 로그에 추가
        doc.add_patch(
            author="user", # 또는 system-auto-detect 등 상황에 맞게
            reason=f"{test_contract_name} 변경 감지",
            diff_text=diff_text
        )
        
        # DB 저장
        save_scenario(doc)
        
        return {
            "message": f"{test_contract_name} 변경사항이 기록되었습니다.",
            "diff": diff_text
        }
    else:
        return {"message": "테스트 코드 변경 없음."}

@mcp.tool()
def analyze_test_results(sid: str, run_id: str, insights: Dict[str, Any]) -> dict:
    """
    [MCP 시스템 컨텍스트]
    [순차적 검증 프로세스: 4단계 - 심층 분석 및 인사이트 도출]
    
    스마트 컨트랙트 순차적 검증 프로세스의 네 번째 단계로, 테스트 실행 결과에 대한 
    심층 분석을 수행하고 구조화된 인사이트를 도출합니다.
    
    - 이 도구는 순차적 검증 프로세스에서 다음과 같은 역할을 합니다:
      1. 이전 단계에서 수집한 테스트 결과에 대한 심층 분석을 수행합니다
      2. 순차적 사고 과정을 통해 발견한 인사이트를 구조화된 형태로 저장합니다
      3. 다음 단계인 메타 분석을 위한 기초 데이터를 제공합니다
    
    LLM은 이 단계에서 다음과 같은 순차적 사고 과정을 거쳐야 합니다:
    
    1. 심층 분석 (Deep Analysis):
       - 실행 흐름 추적: 테스트가 어떤 단계를 거쳤는지 분석
       - 상태 변화 감지: 계약 상태가 어떻게 변했는지 파악
       - 조건부 행동 파악: 특정 조건에서의 동작 방식 이해
       - 트리거 포인트 식별: 취약점이 발현되는 조건 파악
    
    2. 가설 형성 (Hypothesis Formation):
       - 동작 가설 수립: 관찰된 동작에 대한 원인과 메커니즘 제시
       - 보안 영향 평가: 취약점의 잠재적 영향 평가
       - 패턴 일반화: 특정 케이스에서 일반적인 취약점 패턴으로 확장
    
    3. 가설 검증 (Hypothesis Verification):
       - 데이터 재검토: 로그를 다시 검토하여 가설 지원 여부 확인
       - 대안 가설 고려: 다른 설명 가능성 검토 및 배제
       - 증거 기반 결론: 증거에 기반한 검증된 결론 도출
    
    4. 인사이트 도출 (Insight Extraction):
       - 핵심 발견 사항 정리: 검증된 핵심 인사이트 요약
       - 구조화된 형식으로 변환: 아래 양식에 맞게 인사이트 구성
       - 신뢰도 평가: 각 인사이트에 대한 신뢰도 수준 평가
    
    [이전 단계]
    - get_single_unit_test_log 도구를 통해 테스트 실행의 상세 로그를 검토했어야 합니다
    
    [다음 단계]
    - get_cumulative_insights 도구를 사용하여 누적된 인사이트에 대한 메타 분석을 수행하세요
    
    [매개변수]
    - sid: 시나리오 ID
    - run_id: 분석 대상 테스트 실행 ID
    - insights: 순차적 사고 과정을 통해 도출한 인사이트 딕셔너리 (아래 필드 포함)
      * precondition: 테스트의 전제 조건 (예: "reverting hook 설정 시")
      * state_changes: 관찰된 상태 변화 (예: "pool.liquidity 값이 0으로 유지됨")
      * patterns: 감지된 패턴 (예: "특정 주소로부터의 호출만 revert됨")
      * security_implications: 보안 영향 (예: "hook이 항상 revert하면 사용자는 swap 불가")
      * additional_info: 추가 분석 정보
      * confidence: 인사이트의 신뢰도 (0-1 범위의 값)
    
    [반환 값]
    - success: 인사이트 저장 성공 여부
    - message: 상태 메시지
    - insights_count: 현재까지 저장된 인사이트 수
    """
    logger.info(f"[analyze_test_results] 호출: sid={sid}, run_id={run_id}")
    
    # insights가 문자열인 경우 딕셔너리로 변환
    if isinstance(insights, str):
        try:
            logger.info("문자열 형태의 insights를 딕셔너리로 변환 시도")
            insights = json.loads(insights)
        except json.JSONDecodeError as e:
            error_msg = f"insights 파라미터가 유효한 JSON 문자열이 아닙니다: {str(e)}"
            logger.error(error_msg)
            return {"error": error_msg}
    
    # 빈 딕셔너리인 경우 기본 필드 추가
    if not insights:
        logger.warning("insights가 비어 있습니다. 기본 값으로 초기화합니다.")
        insights = {
            "precondition": "정보 없음",
            "state_changes": "정보 없음",
            "patterns": "정보 없음",
            "security_implications": "정보 없음",
            "additional_info": "정보 없음",
            "confidence": 0.5
        }
    
    doc = load_scenario(sid)
    if not doc:
        error_msg = f"시나리오 {sid}가 존재하지 않습니다."
        logger.error(error_msg)
        return {"error": error_msg}
    
    # 해당 run_id가 존재하는지 확인
    run_found = False
    for log_entry in doc.runlog:
        if log_entry.get("run_id") == run_id:
            run_found = True
            break
    
    if not run_found:
        error_msg = f"실행 ID {run_id}에 해당하는 로그를 찾을 수 없습니다."
        logger.error(error_msg)
        return {"error": error_msg}
    
    try:
        # ScenarioDoc의 test_insights 필드가 설정되어 있는지 확인
        if not hasattr(doc, 'test_insights'):
            logger.warning(f"시나리오 {sid}에 test_insights 필드가 없습니다. 초기화합니다.")
            doc.test_insights = []
        elif not isinstance(doc.test_insights, list):
            logger.warning(f"시나리오 {sid}의 test_insights가 리스트가 아닙니다. 현재 타입: {type(doc.test_insights)}. 리스트로 초기화합니다.")
            doc.test_insights = []
            
        # 인사이트 저장
        doc.add_test_insight(run_id, insights)
        save_scenario(doc)
        
        # 인사이트 개수 계산 (test_insights가 리스트가 아닐 경우 대비)
        insights_count = len(doc.test_insights) if isinstance(doc.test_insights, list) else 0
        
        logger.info(f"인사이트 저장 완료: sid={sid}, run_id={run_id}, insights_count={insights_count}")
        return {
            "success": True, 
            "message": f"시나리오 {sid}의 실행 {run_id}에 대한 인사이트가 저장되었습니다.",
            "insights_count": insights_count
        }
    except Exception as e:
        error_msg = f"인사이트 저장 중 오류 발생: {str(e)}"
        logger.error(error_msg)
        return {"error": error_msg}

@mcp.tool()
def get_cumulative_insights(sid: str) -> dict:
    """
    [MCP 시스템 컨텍스트]
    [순차적 검증 프로세스: 5단계 - 누적 인사이트 메타 분석]
    
    스마트 컨트랙트 순차적 검증 프로세스의 다섯 번째 단계로, 누적된 모든 인사이트를 종합하여
    메타 수준의 분석을 수행하고 보다 깊은 패턴과 이해를 도출합니다.
    
    - 이 도구는 순차적 검증 프로세스에서 다음과 같은 역할을 합니다:
      1. 시나리오에 대해 지금까지 수행된 모든 테스트 실행의 인사이트를 시간순으로 조회합니다
      2. 개별 테스트에서는 발견하기 어려운 패턴과 추세를 식별할 수 있는 데이터를 제공합니다
      3. 메타 수준의 분석을 통해 높은 신뢰도의 종합적 결론을 도출할 기반을 마련합니다
    
    LLM은 이 단계에서 다음과 같은 메타 분석 프로세스를 수행해야 합니다:
    
    1. 인사이트 수집 및 정리 (Collection & Organization):
       - 시간순 인사이트 추적: 인사이트가 시간에 따라 어떻게 변화했는지 분석
       - 패턴 합성: 개별 인사이트에서 발견된 패턴들을 종합
       - 인사이트 간 관계 매핑: 서로 다른 인사이트 간의 연관성 파악
    
    2. 패턴 인식 (Pattern Recognition):
       - 일관된 패턴 파악: 여러 테스트에서 반복적으로 나타나는 행동 식별
       - 조건부 패턴 감지: 특정 조건에서만 발현되는 패턴 식별
       - 예외 사례 분석: 일반적 패턴과 다른 예외 케이스의 의미 분석
    
    3. 분기 분석 (Branch Analysis):
       - 조건 비교: 서로 다른 조건에서의 시스템 행동 비교
       - 분기점 식별: 행동이 갈라지는 핵심 분기점 파악
       - 결정적 요인 파악: 행동 변화를 일으키는 결정적 요인 식별
    
    4. 가설 통합 (Hypothesis Integration):
       - 가설 조정: 개별 인사이트의 가설들을 통합하고 조정
       - 모순 해결: 상충되는 인사이트 간의 모순 분석 및 해결
       - 통합 모델 구축: 모든 관찰 결과를 설명하는 통합된 모델 구축
    
    5. 메타 인사이트 도출 (Meta-Insight Generation):
       - 종합적 취약점 모델링: 취약점의 전체 메커니즘 종합적 설명
       - 보안 영향 종합 평가: 시스템 전체적 관점에서 보안 영향 평가
       - 근본 원인 분석: 취약점의 근본 원인과 해결 방안 제시
    
    [이전 단계]
    - analyze_test_results 도구를 통해 개별 테스트 실행에 대한 인사이트를 저장했어야 합니다
    - 가능하면 여러 테스트 실행과 다양한 조건에서의 인사이트가 누적되어 있어야 합니다
    
    [다음 단계]
    - 이 단계에서 도출된 메타 인사이트를 바탕으로 최종 결론을 도출하고 보고서를 작성하세요
    - 필요한 경우 update_scenario 도구를 통해 시나리오 자체를 개선할 수 있습니다
    
    [매개변수]
    - sid: 시나리오 ID
    
    [반환 값]
    - success: 조회 성공 여부
    - insights: 시나리오에 저장된 모든 인사이트 목록 (최신순)
    - insights_count: 저장된 인사이트 수
    - 각 인사이트는 run_id, timestamp, precondition, state_changes, patterns, security_implications 등 포함
    """
    logger.info(f"[get_cumulative_insights] 호출: sid={sid}")
    
    doc = load_scenario(sid)
    if not doc:
        error_msg = f"시나리오 {sid}가 존재하지 않습니다."
        logger.error(error_msg)
        return {"error": error_msg}
    
    try:
        # 인사이트 목록 가져오기
        insights = doc.get_cumulative_insights()
        
        # 각 인사이트 항목 검증 및 정리
        validated_insights = []
        for insight in insights:
            # 문자열 형태의 인사이트인 경우 파싱 시도
            if isinstance(insight, str):
                try:
                    insight = json.loads(insight)
                except json.JSONDecodeError:
                    logger.warning(f"잘못된 형식의 인사이트 발견: {insight[:50]}...")
                    # 건너뛰기
                    continue
            
            # 필수 필드 존재 확인 및 기본값 설정
            if not isinstance(insight, dict):
                continue
                
            # 필수 필드 확인
            for field in ["precondition", "state_changes", "patterns", "security_implications"]:
                if field not in insight:
                    insight[field] = "정보 없음"
            
            # 타임스탬프 확인
            if "ts" not in insight:
                insight["ts"] = datetime.datetime.utcnow().isoformat()
                
            validated_insights.append(insight)
        
        logger.info(f"누적 인사이트 조회 완료: sid={sid}, count={len(validated_insights)}")
        return {
            "success": True,
            "insights": validated_insights,
            "insights_count": len(validated_insights)
        }
    except Exception as e:
        error_msg = f"누적 인사이트 조회 중 오류 발생: {str(e)}"
        logger.error(error_msg)
        return {
            "error": error_msg,
            "success": False,
            "insights": [],
            "insights_count": 0
        }

@mcp.tool()
async def get_single_unit_test_log(sid: str, run_id: str) -> dict:
    """
    [MCP 시스템 컨텍스트]
    [순차적 검증 프로세스: 3단계 - 상세 실행 결과 조회 및 초기 관찰]
    
    스마트 컨트랙트 순차적 검증 프로세스의 세 번째 단계로, 특정 테스트 실행의 상세 결과를 조회하고
    초기 관찰을 수행합니다.
    
    - 이 도구는 순차적 검증 프로세스에서 다음과 같은 역할을 합니다:
      1. 실행 ID(run_id)에 해당하는 테스트 실행 로그 전체를 조회합니다
      2. 실행 시간, 상태, 표준 출력, 표준 에러 등 모든 상세 정보를 제공합니다
      3. 순차적 사고의 초기 관찰 단계를 지원하는 상세 데이터를 제공합니다
    
    - 이전 단계]
    - execute_single_unit_test 도구를 통해 테스트를 실행하고 run_id를 얻었어야 합니다
    
    - 다음 단계]
    - analyze_test_results 도구를 사용하여 심층 분석 및 인사이트 도출을 수행하세요
    
    - 매개변수]
    - sid: 시나리오 ID
    - run_id: 분석 대상 테스트 실행 ID
    
    - 반환값]
    - 해당 run_id의 실행 로그 상세 정보 (run_id, ts, status, diff, stdout, stderr 등 포함)
    - 이 정보는 다음 단계인 심층 분석의 입력 데이터로 사용됩니다
    """
    logger.info(f"[get_single_unit_test_log] 호출: sid={sid}, run_id={run_id}")
    doc = load_scenario(sid)
    if not doc:
        return {"error": f"시나리오 {sid}를 찾을 수 없습니다."}
        
    # 먼저 시나리오의 runlog 필드에서 해당 run_id 찾기
    for log_entry in doc.runlog:
        if log_entry.get("run_id") == run_id:
            logger.info(f"시나리오 {sid}에서 실행 ID {run_id}의 로그 찾음")
            return log_entry
    
    # 시나리오에 없으면 runlog 테이블에서 직접 조회
    # db_manager에서 SQLite 연결 관련 기능을 가져와야 하지만, 
    # 현재는 간단하게 직접 연결을 사용
    try:
        from db_manager import _conn
        with _conn() as c:
            row = c.execute("SELECT * FROM runlog WHERE run_id=? AND scenario_id=?", (run_id, sid)).fetchone()
            if row:
                logger.info(f"DB에서 실행 ID {run_id}의 로그 찾음")
                return dict(row)
    except Exception as e:
        logger.error(f"DB 조회 중 오류: {e}")
    
    # 마지막으로 execute_single_unit_test의 반환 결과를 사용
    # 이 부분은 테스트 실행 직후 바로 로그를 조회할 때 유용함
    return {"error": f"실행 ID {run_id}에 해당하는 로그를 찾을 수 없습니다. 로그가 아직 저장되지 않았거나 다른 ID가 사용되었을 수 있습니다."}

################################################################################
# 서버 실행
################################################################################

if __name__ == "__main__":
    logger.info("🔄 dynamic-schema MCP server started")
    local_server = LocalMCPServer()
    mcp.run(transport="stdio")

