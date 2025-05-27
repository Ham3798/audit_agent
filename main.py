################################################################################
# 🎯 **LLM 기반 스마트컨트랙트 PoC 개발 전용 MCP 서버**
#
# 이 MCP 서버는 LLM이 스마트컨트랙트 보안 취약점의 PoC(Proof of Concept) 코드를 
# 체계적으로 개발하고 검증할 수 있도록 설계된 전문 백엔드입니다.
#
# [핵심 PoC 개발 아키텍처: 1 시나리오 = 1 통합 PoC + n개 검증 테스트]
# - LLM이 취약점을 발견하면 → 시나리오로 등록 → 다양한 테스트 케이스 작성 → 통합 PoC 생성
# - 각 유닛테스트는 취약점의 다른 측면을 검증 (기본 공격, 엣지 케이스, 방어 우회 등)
# - 모든 테스트 결과를 종합하여 완성도 높은 최종 PoC 코드 자동 생성
# - 실행 결과와 인사이트를 누적하여 PoC의 신뢰성과 완성도 지속적 향상
#
# [LLM을 위한 PoC 개발 가이드라인]
# 1. **시나리오 중심 접근**: 취약점 발견 → register_scenario로 체계화
# 2. **점진적 테스트 확장**: add_unit_test로 다양한 공격 벡터 검증
# 3. **실행 기반 검증**: execute_unit_test로 실제 동작 확인
# 4. **인사이트 누적**: analyze_test_results로 발견사항 구조화
# 5. **자동 PoC 생성**: generate_poc_from_tests로 최종 통합 코드 생성
# 6. **자율적 개선**: llm_autonomous_verification_cycle로 완성도 향상
#
# [MCP의 역할: LLM의 PoC 개발 파트너]
# - LLM은 창의적 사고와 코드 생성을 담당
# - MCP는 체계적 관리와 실행 환경을 제공
# - 모든 "추론"과 "판단"은 LLM이 수행
# - MCP는 LLM의 결정사항을 정확히 저장/실행/추적만 담당
#
# [주요 PoC 개발 도구 및 사용 시점]
#
# === 🚀 PoC 개발 시작 단계 ===
# 1. register_scenario(scenario_dict)
#    ✅ 사용 시점: 새로운 취약점을 발견했을 때
#    🎯 목적: 취약점을 체계적으로 문서화하고 PoC 개발 기반 마련
#    💡 LLM 가이드: schema_1.0.yaml 구조에 맞게 메타데이터, 스펙, 초기 코드 정보 제공
#
# 2. scenario_context(sid, test_contract_name, foundry_root_path)
#    ✅ 사용 시점: 기존 시나리오의 PoC 개발을 계속할 때
#    🎯 목적: 현재까지의 모든 개발 컨텍스트 로드 (코드, 테스트, 인사이트 등)
#    💡 LLM 가이드: 반환된 정보로 현재 PoC 상태를 파악하고 다음 단계 계획
#
# === 🧪 테스트 케이스 개발 단계 ===
# 3. add_unit_test(sid, test_name, description, test_code, expected_behavior, tags)
#    ✅ 사용 시점: 새로운 공격 벡터나 테스트 시나리오를 추가할 때
#    🎯 목적: 취약점의 다양한 측면을 검증하는 개별 테스트 케이스 생성
#    💡 LLM 가이드: 기본 공격, 엣지 케이스, 방어 우회, 상태 조작 등 다각도 검증
#
# 4. get_unit_tests(sid)
#    ✅ 사용 시점: 현재 등록된 테스트들을 확인하고 싶을 때
#    🎯 목적: 테스트 커버리지 파악 및 누락된 시나리오 식별
#    💡 LLM 가이드: 반환된 목록으로 추가 필요한 테스트 케이스 계획
#
# === ⚡ 실행 및 검증 단계 ===
# 5. execute_unit_test(sid, test_name, foundry_root_path)
#    ✅ 사용 시점: 특정 테스트의 동작을 확인하고 싶을 때
#    🎯 목적: 개별 공격 시나리오의 실제 동작 검증
#    💡 LLM 가이드: 실패 시 코드 수정, 성공 시 다음 테스트로 진행
#
# 6. execute_all_unit_tests(sid, foundry_root_path)
#    ✅ 사용 시점: 모든 테스트의 전체적인 성공률을 확인할 때
#    🎯 목적: PoC의 전반적인 완성도와 안정성 평가
#    💡 LLM 가이드: 성공률이 낮으면 문제 있는 테스트들 개별 분석 필요
#
# === 📊 분석 및 인사이트 단계 ===
# 7. get_test_logs(sid, test_name)
#    ✅ 사용 시점: 테스트 실행 결과의 상세 정보가 필요할 때
#    🎯 목적: 실행 로그 분석을 통한 문제점 진단 및 개선점 도출
#    💡 LLM 가이드: stdout/stderr 분석으로 실패 원인 파악 또는 성공 패턴 이해
#
# 8. analyze_test_results_by_test(sid, test_name, run_id, insights)
#    ✅ 사용 시점: 테스트 결과를 분석하여 의미 있는 발견사항을 기록할 때
#    🎯 목적: 실행 결과에서 도출한 보안 인사이트를 구조화하여 저장
#    💡 LLM 가이드: precondition, state_changes, patterns, security_implications 등 체계적 분석
#
# 9. get_test_insights(sid, test_name)
#    ✅ 사용 시점: 누적된 인사이트를 바탕으로 PoC 개선 방향을 결정할 때
#    🎯 목적: 지금까지 발견한 모든 보안 인사이트 종합 검토
#    💡 LLM 가이드: 패턴 분석으로 추가 공격 벡터 발견 또는 PoC 완성도 평가
#
# === 🎯 최종 PoC 생성 단계 ===
# 10. generate_poc_from_tests(sid)
#     ✅ 사용 시점: 모든 테스트가 완료되어 최종 통합 PoC를 생성할 때
#     🎯 목적: 개별 테스트들을 결합한 완성된 PoC 코드 자동 생성
#     💡 LLM 가이드: 생성된 PoC 검토 후 필요시 추가 테스트나 수정 진행
#
# === 🤖 자율적 개선 단계 ===
# 11. llm_assess_verification_needs(sid)
#     ✅ 사용 시점: 현재 PoC의 완성도를 자체 평가하고 싶을 때
#     🎯 목적: LLM이 스스로 부족한 부분을 진단하고 개선 계획 수립
#     💡 LLM 가이드: 반환된 분석 질문들에 답하며 추가 필요 작업 식별
#
# 12. llm_generate_test_improvement(sid, improvement_plan, foundry_root_path)
#     ✅ 사용 시점: 분석 결과를 바탕으로 실제 코드 개선을 적용할 때
#     🎯 목적: LLM이 설계한 개선사항을 실제 테스트 코드에 반영
#     💡 LLM 가이드: JSON 형태로 새로운 테스트 함수와 개선 이유 제공
#
# 13. llm_autonomous_verification_cycle(sid, foundry_root_path)
#     ✅ 사용 시점: 완전 자율적으로 PoC 완성도를 높이고 싶을 때
#     🎯 목적: LLM이 스스로 분석→개선→실행→평가 사이클 수행
#     💡 LLM 가이드: 제공된 지침에 따라 단계별로 자율적 개선 진행
#
# === 📋 관리 및 유틸리티 도구 ===
# 14. get_scenario(sid) / list_scenarios() / update_scenario(sid, update_dict)
#     ✅ 사용 시점: 시나리오 정보 조회, 목록 확인, 메타데이터 업데이트 시
#     🎯 목적: PoC 개발 과정에서 필요한 기본적인 시나리오 관리
#
# [LLM을 위한 PoC 개발 성공 전략]
# 🎯 **단계적 접근**: 간단한 기본 공격부터 시작하여 점진적으로 복잡한 시나리오 추가
# 🔄 **반복적 개선**: 테스트 실행 → 결과 분석 → 코드 개선 → 재실행 사이클 반복
# 📊 **데이터 기반 판단**: 실행 로그와 인사이트를 바탕으로 객관적 개선 방향 결정
# 🤖 **자율적 완성도 관리**: 정기적으로 자체 평가하여 누락된 부분 보완
# 🎨 **창의적 테스트 설계**: 일반적인 공격뿐만 아니라 독창적인 공격 벡터도 탐색
#
# [새로운 스키마 구조 (schema_1.0.yaml)]
# - code: PoC 컨트랙트 코드 및 대상 컨트랙트 정보
#   * poc_contract: 통합 PoC 컨트랙트 코드 (Solidity)
#   * target_contract_name: 대상 컨트랙트 이름
#   * deployment_script: 배포 스크립트 (선택적)
#
# - unit_tests: n개의 유닛테스트 정의 (배열)
#   * test_name: 테스트 함수 이름 (고유)
#   * description: 테스트 설명
#   * test_code: 테스트 함수 코드 (Solidity)
#   * expected_behavior: 예상 동작
#   * tags: 테스트 태그 (예: ["attack", "reentrancy", "poc"])
#
# - runlog: 실행 로그에 test_name 필드 추가
#   * test_name: 실행된 테스트 이름 (unit_tests의 test_name과 매칭)
#
# - test_insights: 인사이트에 test_name 필드 추가
#   * test_name: 분석된 테스트 이름
#
# [자동 파일 변경 감지 및 PoC 진화 추적]
# - 모든 테스트 실행 시 자동으로 파일 변경 감지
# - 코드 수정 이력을 patches 필드에 자동 기록
# - LLM의 PoC 개발 과정을 완전히 추적하여 개발 히스토리 보존
# - 변경 사항의 의미 해석과 다음 단계 결정은 LLM이 담당
#
# [모듈 구조]
# - main.py: MCP 서버의 PoC 개발 도구와 API 엔드포인트 제공
# - db_manager.py: 시나리오, 테스트, 인사이트 데이터 관리
# - schema_validator.py: PoC 시나리오 스키마 검증 및 힌트 추출
# - file_monitor.py: 테스트 파일 변경 감지 및 PoC 진화 추적
#
# [참고]
# - 각 필드/입력 구조/예시는 schema_1.0.yaml 및 실제 시나리오 예시 참고
# - PoC 개발에 최적화된 아키텍처로 LLM의 창의적 보안 연구 지원
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
from schema_validator import extract_hints
from db_manager import ScenarioDoc, save_scenario, load_scenario, update_scenario_partial, delete_scenario, list_ids, add_runlog_entry, init_db
from file_monitor import FileMonitor  # file_monitor 모듈 가져오기

# 로거 설정
logger = logging.getLogger("dyn-schema-mcp")
logger.setLevel(logging.INFO)
logger.handlers.clear()  # 기존 핸들러 제거
file_handler = logging.FileHandler("mcp-server.log")
file_handler.setLevel(logging.INFO)
logger.addHandler(file_handler)

# file_monitor 객체 초기화 - 시나리오 ID와 테스트 컨트랙트 파일 매핑을 위한 도구
file_monitor = FileMonitor()

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
# 3. Foundry 테스트 실행 도구
################################################################################

class FoundryTool:
    """
    Foundry 관련 도구: 유닛테스트 실행, 로그 수집
    
    주요 기능:
    - runUnitTest: Foundry forge test 명령어 실행
    """

    def runUnitTest(self, test_contract_name=None, foundry_root_path=None):
        """
        유닛테스트 실행
        
        Args:
            test_contract_name: 테스트 컨트랙트 이름 (없으면 전체 테스트 실행)
            foundry_root_path: Foundry 프로젝트 루트 디렉토리 경로
            
        Returns:
            tuple: (성공 여부, stdout, stderr)
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
    - test_contract_name: 테스트 컨트랙트 이름
      * 파일 확장자(.t.sol) 포함/제외 모두 가능 (예: "Sync" 또는 "Sync.t.sol")
      * 이 매개변수는 컨텍스트 정보 제공 목적으로 사용되며, 실제 파일 탐색에는 영향을 주지 않습니다
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
async def execute_single_unit_test(sid: str, test_contract_name: str, foundry_root_path: str, test_name: str = "") -> dict:
    """
    [MCP 시스템 컨텍스트]
    [순차적 검증 프로세스: 2단계 - 테스트 실행 및 기초 데이터 수집]
    
    스마트 컨트랙트 순차적 검증 프로세스의 두 번째 단계로, 시나리오에 대한 테스트를 실행하고
    분석을 위한 기초 데이터를 수집합니다.
    
    이 도구는 순차적 검증 프로세스에서 다음과 같은 역할을 합니다:
    1. 지정된 테스트 컨트랙트에 대한 Foundry 유닛 테스트를 실행합니다
    2. 테스트 실행 결과(stdout, stderr, 상태 등)를 수집합니다
    3. 결과를 DB의 runlog에 기록하고 run_id를 생성합니다
    4. 테스트 파일의 변경 여부를 자동으로 감지하고, 변경된 경우 패치 로그를 생성합니다
       - 이전 스냅샷과 현재 파일을 비교하여 diff를 생성
       - 시나리오의 patches 필드에 변경 사항을 자동으로 기록
       - 테스트 코드 스냅샷을 최신 버전으로 업데이트
    
    [중요: 테스트 우선 접근법]
    - 이 함수는 반드시 DB에 등록된 시나리오가 있어야 작동합니다
    - 최초 분석 시에는 먼저 유닛테스트를 실행/분석한 후 register_scenario로 시나리오를 등록해야 합니다
    - 시나리오가 등록되지 않은 상태에서 이 함수 호출 시 에러가 발생합니다
    
    [이전 단계]
    - scenario_context 도구를 통해 시나리오의 전체 컨텍스트를 이해했어야 합니다
    - 또는 최초 검증 시에는 시나리오를 register_scenario로 먼저 등록했어야 합니다
    
    [다음 단계]
    - 여러 번의 테스트 실행 후 get_single_unit_test_log 도구로 각 로그 확인 또는
    - get_unit_test_logs 도구로 모든 누적 로그를 한번에 확인 가능
    - analyze_test_results 도구를 사용하여 누적된 로그에 대한 심층 분석 수행
    
    [중요]
    - 반환되는 run_id 값을 기록해두세요 - 이는 다음 단계들에서 사용됩니다
    - 이 툴은 테스트 실행만 담당하며, 테스트 코드 생성이나 시나리오 자동 수정은 하지 않습니다
    - 테스트 파일의 변경 사항은 자동으로 감지되어 패치 로그에 기록되므로 별도 diff 감지 도구 사용이 불필요합니다
    
    [매개변수]
    - sid: 시나리오 ID (실행 로그 기록용)
    - test_contract_name: 테스트 컨트랙트 이름
      * 파일 확장자(.t.sol) 포함/제외 모두 가능 (예: "Sync" 또는 "Sync.t.sol")
      * 시스템이 자동으로 다음 경로들을 순서대로 탐색합니다:
        1. test/{test_contract_name}.t.sol
        2. test/generated/{test_contract_name}.t.sol  
        3. test/{sid}.t.sol (sid와 contract name이 다를 경우)
      * 파일을 찾지 못해도 테스트 실행은 계속 진행됩니다
    - foundry_root_path: foundry 프로젝트 디렉토리 경로 (예: /foundry_project)
    - test_name: 특정 테스트 함수 이름 (새로 추가, 선택적)
      * 지정하면 해당 테스트만 실행, 비어있으면 전체 테스트 실행
    
    [반환 값]
    - success: 테스트 성공 여부
    - stdout: 테스트 표준 출력
    - stderr: 테스트 표준 에러
    - run_id: 실행 ID (다음 단계에서 사용)
    - test_name: 실행된 테스트 이름 (지정된 경우)
    + execution_context: 실행 컨텍스트 정보 (에러 패턴, 가스 정보, 이벤트, 상태 변화)
    + exploration_status: 탐색 상태 정보 (테스트 수, 커버리지 영역, 패턴)
    
    [LLM을 위한 추가 컨텍스트]
    이 도구는 기본 테스트 결과 외에도 LLM이 다음 액션을 자율적으로 판단할 수 있도록 
    다음과 같은 탐색 컨텍스트를 제공합니다:
    - 실행 결과에서 감지된 패턴들 (에러 유형, 가스 사용, 이벤트 등)
    - 현재까지의 탐색 진행 상황 (테스트 횟수, 접촉한 영역, 나타나는 패턴)
    - 이 정보들을 통해 LLM은 더 깊은 탐색이 필요한지, 다른 접근이 필요한지, 
      또는 분석으로 넘어갈 준비가 되었는지 등을 스스로 판단할 수 있습니다.
    
    [새로 추가된 보안 검증 완성도 평가]
    + security_verification_assessment: 현재까지 검증된 보안 영역과 미검증 영역 분석
    + additional_verification_suggestions: 추가 검증이 필요한 구체적 영역과 테스트 시나리오 제안  
    + current_test_coverage: 현재 테스트의 함수 커버리지와 시나리오 다양성 평가
    + verification_gaps_analysis: 치명적 보안 갭과 즉시 조치가 필요한 영역 식별
    
    이 정보들을 통해 LLM은 테스트가 성공했어도 보안 검증이 충분하지 않을 경우
    능동적으로 추가 테스트 케이스를 생성하고 재실행하는 사이클을 시작할 수 있습니다.
    """
    logger.info(f"[execute_single_unit_test] 호출: sid={sid}, test_contract_name={test_contract_name}, test_name={test_name}")
    doc = load_scenario(sid)
    if not doc:
        error_msg = f"시나리오 {sid}가 DB에 존재하지 않습니다. 먼저 시나리오를 등록하세요."
        logger.error(error_msg)
        return {"error": error_msg}
    
    try:
        # 1. 테스트 파일 경로 생성 및 파일 변경 감지 준비
        # 여러 가능한 테스트 파일 경로를 시도
        possible_paths = [
            # 기본 경로: test/{test_contract_name}.t.sol
            os.path.join(foundry_root_path, "test", f"{test_contract_name}.t.sol"),
            # generated 폴더 경로: test/generated/{test_contract_name}.t.sol  
            os.path.join(foundry_root_path, "test", "generated", f"{test_contract_name}.t.sol"),
            # sid 기반 경로: test/{sid}.t.sol (sid와 contract name이 다를 경우)
            os.path.join(foundry_root_path, "test", f"{sid}.t.sol"),
        ]
        
        # 실제 존재하는 파일 경로 찾기
        test_file_full_path = None
        test_file_relative_path = None
        
        for path in possible_paths:
            if os.path.exists(path):
                test_file_full_path = path
                test_file_relative_path = os.path.relpath(path, foundry_root_path)
                logger.info(f"테스트 파일 발견: {test_file_full_path}")
                break
        
        # 파일이 발견되지 않은 경우 경고 출력
        if not test_file_full_path:
            logger.warning(f"테스트 파일을 찾을 수 없음. 시도한 경로들:")
            for path in possible_paths:
                logger.warning(f"  - {path}")
            logger.warning("테스트 파일 없이 테스트 실행을 계속합니다.")
        
        # 1.1. 테스트 파일이 존재할 경우 변경 감지 수행
        if test_file_full_path and os.path.exists(test_file_full_path):
            # 1.2. 테스트 파일 모니터링 등록 (test_name 포함)
            file_monitor.register_file(sid, test_file_full_path, test_name)
            logger.info(f"테스트 파일 모니터링 등록: {test_file_full_path}, test_name={test_name}")
            
            # 1.3. 테스트 코드 변경 감지
            with open(test_file_full_path, "r", encoding="utf-8") as f:
                current_code = f.read()
                
            # 1.4. 이전 스냅샷과 비교하여 변경 감지
            # 스냅샷 키는 파일의 실제 이름을 사용 (경로에서 파일명만 추출)
            actual_file_name = os.path.basename(test_file_full_path).replace(".t.sol", "")
            last_known_code = doc.test_code_snapshots.get(actual_file_name, "")
            
            if last_known_code != current_code:
                logger.info(f"테스트 코드 변경 감지: {actual_file_name}")
                
                # 1.5. diff 생성
                diff = difflib.unified_diff(
                    last_known_code.splitlines(),
                    current_code.splitlines(),
                    fromfile=f"previous_{actual_file_name}",
                    tofile=f"current_{actual_file_name}",
                    lineterm="\n"
                )
                diff_text = "".join(diff)
                
                if diff_text:
                    # 1.6. 패치 로그 추가
                    doc.add_patch(
                        author="user",
                        reason=f"{actual_file_name} 코드 변경 감지 (execute_single_unit_test)",
                        diff_text=diff_text
                    )
                    logger.info(f"테스트 코드 변경에 대한 패치 로그 생성 완료")
                
                # 1.7. 테스트 코드 스냅샷 업데이트
                doc.test_code_snapshots[actual_file_name] = current_code
        
        # 2. Foundry 테스트 실행
        # test_contract_name에서 .t.sol 확장자 제거 (있는 경우)
        contract_name = test_contract_name.replace('.t.sol','')
        logger.info(f"유닛테스트 실행 준비: {contract_name}")
        
        # 2.1. 테스트 실행
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
        
        # 6. 시나리오 저장 (코드 변경 감지로 인한 업데이트 포함)
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
            "run_id": run_id,
        }
    except Exception as e:
        error_msg = f"테스트 실행 중 오류 발생: {str(e)}"
        logger.error(error_msg)
        return {
            "success": False,
            "message": error_msg,
            "stdout": "",
            "stderr": str(e),
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
    🚀 **PoC 개발 시작점: 새로운 취약점 시나리오 등록**
    
    LLM이 새로운 보안 취약점을 발견했을 때, 이를 체계적인 PoC 개발 프로젝트로 
    전환하기 위한 핵심 도구입니다. 이 단계에서 취약점의 모든 메타데이터와 
    초기 분석 결과를 구조화하여 저장합니다.
    
    🎯 **PoC 개발에서의 역할**:
    - 취약점 발견 → 체계적 PoC 프로젝트 시작
    - 무작정 코딩하지 않고 먼저 취약점의 본질을 문서화
    - 이후 모든 테스트 케이스와 PoC 코드의 기준점 역할
    - 팀 협업이나 감사 보고서 작성 시 참조 자료로 활용
    
    💡 **LLM 사용 가이드**:
    1. **메타데이터 완성**: id, title, category, severity 등 기본 정보
    2. **스펙 정의**: 공격 시나리오, 관련 액터, 자산, 신뢰 경계 등
    3. **초기 코드 구조**: 대상 컨트랙트 정보, 기본 PoC 틀
    4. **태그 활용**: 나중에 유사한 취약점 검색 시 활용
    
    ⚠️ **중요 제약사항**:
    - meta.id는 반드시 고유해야 함 (중복 시 에러)
    - meta.id는 테스트 컨트랙트 파일명과 일치해야 함 (파일 추적용)
    - schema_1.0.yaml 구조를 정확히 따라야 함
    - 빈 필드도 명시적으로 빈 값으로 설정 필요
    
    🔄 **다음 단계 워크플로우**:
    1. add_unit_test로 다양한 공격 시나리오 테스트 추가
    2. execute_unit_test로 각 테스트 검증
    3. analyze_test_results로 결과 분석 및 인사이트 도출
    4. generate_poc_from_tests로 최종 통합 PoC 생성
    
    📋 **입력 예시**:
    ```json
    {
      "meta": {
        "id": "REENTRANCY_ATTACK_001",
        "title": "ERC20 Transfer Reentrancy PoC",
        "category": "Reentrancy",
        "severity": "critical",
        "tags": ["reentrancy", "erc20", "defi"]
      },
      "spec": {
        "description": "ERC20 토큰의 transfer 함수에서 발생하는 reentrancy 취약점",
        "actors": [
          {"id": "attacker", "role": "malicious_user", "trust_level": "untrusted"},
          {"id": "victim", "role": "normal_user", "trust_level": "trusted"}
        ],
        "assets": [
          {"name": "ETH", "type": "native_token", "critical": true},
          {"name": "ERC20_Token", "type": "token", "critical": true}
        ]
      },
      "code": {
        "target_contract_name": "VulnerableToken",
        "poc_contract": "// 통합 PoC 코드가 여기에 생성됨"
      },
      "unit_tests": []
    }
    ```
    
    ✅ **성공 시**: 시나리오 등록 완료, PoC 개발 프로젝트 시작 준비
    ❌ **실패 시**: 중복 ID, 스키마 오류 등의 구체적 에러 메시지 반환
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

    doc_dict = asdict(doc)
    
    # 허용된 최상위 레벨 키
    allowed_top_level_keys_to_update = {"hints", "patches", "runlog", "extras", "test_insights", "test_code_snapshots"}
    
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
def analyze_test_results(sid: str, run_id: str, insights: Dict[str, Any], test_name: str = "") -> dict:
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
       - 핵심 발견 사항 정리: 검증된 핵심 인사이트 요약 (실행과 관련된 결정론적이고 검증 가능한 사실에 기반)
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
    logger.info(f"[analyze_test_results] 호출: sid={sid}, run_id={run_id}, test_name={test_name}")
    
    # 파일 변경 확인
    if sid in file_monitor.active_sids:
        # 해당 시나리오에 관련된 파일들의 변경 확인
        changed_files = file_monitor.check_for_changes()
        if changed_files:
            file_monitor.apply_changes(changed_files)
            logger.info(f"파일 변경 감지 및 반영 완료: sid={sid}")
    
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
            
        # 인사이트 저장 (test_name 포함)
        doc.add_test_insight(run_id, insights, test_name)
        save_scenario(doc)
        
        # 인사이트 개수 계산 (test_insights가 리스트가 아닐 경우 대비)
        insights_count = len(doc.test_insights) if isinstance(doc.test_insights, list) else 0
        
        logger.info(f"인사이트 저장 완료: sid={sid}, run_id={run_id}, test_name={test_name}, insights_count={insights_count}")
        return {
            "success": True, 
            "message": f"시나리오 {sid}의 실행 {run_id}에 대한 인사이트가 저장되었습니다.",
            "test_name": test_name,
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
    
    # 파일 변경 확인
    if sid in file_monitor.active_sids:
        # 해당 시나리오에 관련된 파일들의 변경 확인
        changed_files = file_monitor.check_for_changes()
        if changed_files:
            file_monitor.apply_changes(changed_files)
            logger.info(f"파일 변경 감지 및 반영 완료: sid={sid}")
    
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
    
    # 파일 변경 확인
    if sid in file_monitor.active_sids:
        # 해당 시나리오에 관련된 파일들의 변경 확인
        changed_files = file_monitor.check_for_changes()
        if changed_files:
            file_monitor.apply_changes(changed_files)
            logger.info(f"파일 변경 감지 및 반영 완료: sid={sid}")
    
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
# LLM 기반 자율적 검증 사이클 PoC
################################################################################

@mcp.tool()
async def llm_assess_verification_needs(sid: str) -> dict:
    """
    [LLM 자율적 검증 - 1단계] 
    LLM이 현재 테스트 상황을 분석하고 추가 검증이 필요한 영역을 판단합니다.
    
    이 도구는 시나리오의 현재 상태 정보만 제공하고, 
    실제 분석과 판단은 LLM이 수행해야 합니다.
    
    Returns:
        dict: 현재 시나리오의 모든 정보 (LLM이 분석할 원시 데이터)
        - scenario_data: 시나리오 전체 정보
        - test_logs: 모든 테스트 실행 로그
        - current_test_code: 현재 테스트 코드
        - file_changes: 최근 파일 변경 이력
    """
    logger.info(f"[llm_assess_verification_needs] LLM 분석용 데이터 수집: {sid}")
    
    try:
        # 1. 시나리오 전체 정보 로드
        doc = load_scenario(sid)
        if not doc:
            return {"error": "시나리오를 찾을 수 없습니다"}
        
        scenario_data = json.loads(doc.to_json())
        
        # 2. 현재 테스트 코드 정보
        current_test_code = {}
        for contract_name, code in doc.test_code_snapshots.items():
            current_test_code[contract_name] = {
                "code": code,
                "line_count": len(code.split('\n')),
                "function_count": code.count('function test_'),
                "has_fuzz_tests": 'test_fuzz' in code,
                "has_security_tests": any(word in code.lower() for word in ['security', 'attack', 'exploit', 'revert']),
                "has_gas_tests": 'gas' in code.lower() or 'snapshotGas' in code
            }
        
        # 3. 테스트 실행 통계
        test_stats = {
            "total_runs": len(doc.runlog),
            "successful_runs": len([log for log in doc.runlog if log.get("status") == "SUCCESS"]),
            "failed_runs": len([log for log in doc.runlog if log.get("status") != "SUCCESS"]),
            "recent_logs": doc.runlog[-3:] if doc.runlog else []  # 최근 3개 로그만
        }
        
        # 4. 인사이트 분석 현황
        insights_stats = {
            "total_insights": len(doc.test_insights) if hasattr(doc, 'test_insights') else 0,
            "recent_insights": doc.test_insights[-2:] if hasattr(doc, 'test_insights') and doc.test_insights else []
        }
        
        logger.info(f"LLM 분석용 데이터 준비 완료: {sid}")
        
        return {
            "scenario_basic_info": {
                "id": scenario_data["meta"]["id"],
                "title": scenario_data["meta"]["title"], 
                "category": scenario_data["meta"]["category"],
                "severity": scenario_data["meta"]["severity"]
            },
            "scenario_spec": scenario_data["spec"],
            "current_test_code": current_test_code,
            "test_execution_stats": test_stats,
            "insights_status": insights_stats,
            "file_changes": scenario_data.get("patches", [])[-3:],  # 최근 3개 변경사항
            
            # LLM이 판단해야 할 질문들을 명시적으로 제시
            "llm_analysis_questions": [
                "현재 테스트가 시나리오의 보안 취약점을 충분히 검증하고 있는가?",
                "어떤 종류의 공격 벡터나 엣지 케이스가 누락되어 있는가?",
                "현재 테스트 코드의 품질과 커버리지는 어떤 수준인가?",
                "추가로 필요한 테스트 케이스는 구체적으로 무엇인가?",
                "시나리오의 특성을 고려할 때 우선적으로 검증해야 할 영역은?",
                "현재까지의 테스트 실행 결과에서 발견할 수 있는 패턴이나 문제점은?"
            ]
        }
        
    except Exception as e:
        logger.error(f"LLM 분석용 데이터 수집 오류: {e}")
        return {"error": f"데이터 수집 중 오류: {str(e)}"}

@mcp.tool()
async def llm_generate_test_improvement(sid: str, improvement_plan: str, foundry_root_path: str) -> dict:
    """
    [LLM 자율적 검증 - 2단계]
    LLM이 분석한 결과를 바탕으로 테스트 개선사항을 실제 코드에 적용합니다.
    
    Args:
        sid: 시나리오 ID
        improvement_plan: LLM이 생성한 개선 계획 (새로운 테스트 함수 코드 포함)
        foundry_root_path: Foundry 프로젝트 경로
        
    Note:
        improvement_plan은 LLM이 다음 형태로 제공해야 합니다:
        {
            "analysis_summary": "분석 요약",
            "new_test_functions": "추가할 새로운 테스트 함수들의 Solidity 코드",
            "modification_reason": "수정 이유",
            "expected_improvement": "기대되는 개선사항"
        }
    """
    logger.info(f"[llm_generate_test_improvement] LLM 개선사항 적용: {sid}")
    
    try:
        doc = load_scenario(sid)
        if not doc:
            return {"error": "시나리오를 찾을 수 없습니다"}
        
        # improvement_plan을 JSON으로 파싱 (문자열인 경우)
        if isinstance(improvement_plan, str):
            try:
                improvement_data = json.loads(improvement_plan)
            except json.JSONDecodeError:
                # JSON이 아닌 일반 텍스트로 전달된 경우, 그대로 사용
                improvement_data = {
                    "analysis_summary": "LLM 분석 결과",
                    "new_test_functions": improvement_plan,
                    "modification_reason": "LLM이 판단한 개선 필요성",
                    "expected_improvement": "테스트 커버리지 및 보안 검증 강화"
                }
        else:
            improvement_data = improvement_plan
        
        new_test_code = improvement_data.get("new_test_functions", "")
        if not new_test_code:
            return {"error": "새로운 테스트 코드가 제공되지 않았습니다"}
        
        # 기존 테스트 코드 가져오기 (첫 번째 스냅샷 사용)
        if not doc.test_code_snapshots:
            return {"error": "기존 테스트 코드 스냅샷이 없습니다"}
        
        contract_name = list(doc.test_code_snapshots.keys())[0]
        existing_code = doc.test_code_snapshots[contract_name]
        
        # 기존 코드에 새 테스트 추가
        lines = existing_code.split('\n')
        
        # 마지막 } 앞에 새 테스트 삽입
        insert_pos = -1
        for i in range(len(lines) - 1, -1, -1):
            if lines[i].strip() == '}' and i > 0:
                insert_pos = i
                break
        
        if insert_pos > 0:
            # 새 테스트 코드 삽입
            lines.insert(insert_pos, "\n    // === LLM이 생성한 추가 테스트 케이스 ===")
            lines.insert(insert_pos + 1, new_test_code)
            lines.insert(insert_pos + 2, "    // === 추가 테스트 케이스 끝 ===\n")
            
            new_code = '\n'.join(lines)
            
            # 파일에 저장
            test_file_paths = [
                os.path.join(foundry_root_path, "test", f"{sid}.t.sol"),
                os.path.join(foundry_root_path, "test", f"{contract_name}.t.sol")
            ]
            
            saved_to = None
            for test_file_path in test_file_paths:
                if os.path.exists(os.path.dirname(test_file_path)):
                    with open(test_file_path, 'w', encoding='utf-8') as f:
                        f.write(new_code)
                    saved_to = test_file_path
                    break
            
            if saved_to:
                # 스냅샷 업데이트
                doc.test_code_snapshots[contract_name] = new_code
                
                # 패치 로그 추가
                doc.add_patch(
                    author="LLM",
                    reason=f"LLM 자율적 검증: {improvement_data.get('modification_reason', '테스트 개선')}",
                    diff_text=f"LLM이 생성한 추가 테스트:\n{new_test_code}"
                )
                
                save_scenario(doc)
                
                logger.info(f"LLM 개선사항 적용 완료: {saved_to}")
                
                return {
                    "success": True,
                    "analysis_summary": improvement_data.get("analysis_summary", ""),
                    "modification_reason": improvement_data.get("modification_reason", ""),
                    "expected_improvement": improvement_data.get("expected_improvement", ""),
                    "new_code_added": new_test_code,
                    "file_updated": saved_to,
                    "added_functions": new_test_code.count('function test_')
                }
            else:
                return {"error": "테스트 파일을 저장할 위치를 찾을 수 없습니다"}
        else:
            return {"error": "코드 삽입 위치를 찾을 수 없습니다"}
            
    except Exception as e:
        logger.error(f"LLM 개선사항 적용 오류: {e}")
        return {"error": f"적용 중 오류: {str(e)}"}

@mcp.tool()  
async def llm_autonomous_verification_cycle(sid: str, foundry_root_path: str) -> dict:
    """
    🤖 **PoC 자율적 완성도 향상: LLM 주도 개선 사이클**
    
    LLM이 현재 PoC의 상태를 스스로 분석하고, 부족한 부분을 식별하여 
    자동으로 개선하는 완전 자율적 PoC 개발 사이클을 시작하는 도구입니다.
    단순한 도구 호출을 넘어서 LLM의 창의적 사고를 활용한 지능적 PoC 완성도 관리를 제공합니다.
    
    🎯 **PoC 개발에서의 혁신적 역할**:
    - 인간의 개입 없이 LLM이 스스로 PoC 품질을 평가하고 개선
    - 놓치기 쉬운 공격 벡터나 엣지 케이스를 자동으로 발견
    - 반복적인 분석→개선→테스트 사이클을 통한 PoC 완성도 극대화
    - 창의적이고 독창적인 공격 시나리오 자동 생성 및 검증
    
    🧠 **LLM 자율적 사고 프로세스**:
    1. **현재 상황 종합 분석**:
       - 기존 테스트들의 커버리지와 성공률 평가
       - 시나리오 특성에 맞는 공격 벡터 완성도 검토
       - 보안 검증의 깊이와 폭 자체 진단
    
    2. **창의적 개선 계획 수립**:
       - 일반적인 테스트를 넘어선 독창적 공격 방법 고안
       - 실제 해커가 사용할 법한 고급 기법 시뮬레이션
       - 방어 메커니즘을 우회하는 새로운 접근법 설계
    
    3. **자동 코드 생성 및 적용**:
       - 설계한 개선사항을 실제 Solidity 코드로 구현
       - 기존 테스트와의 조화를 고려한 통합적 접근
       - 가독성과 실행 효율성을 모두 고려한 코드 품질 관리
    
    4. **실행 및 결과 평가**:
       - 새로 생성한 테스트의 실제 동작 검증
       - 예상과 다른 결과에 대한 원인 분석 및 재개선
       - 전체 PoC 완성도에 대한 객관적 평가
    
    5. **지속적 개선 판단**:
       - 추가 개선이 필요한지 스스로 판단
       - 완성도가 충분하다면 최종 PoC 생성 단계로 진행
       - 필요시 다음 사이클 계획 수립
    
    💡 **LLM을 위한 자율적 개선 전략**:
    - **다각도 접근**: 기술적, 경제적, 사회적 관점에서 취약점 분석
    - **시나리오 확장**: 단순 공격에서 복합 공격으로 점진적 발전
    - **실용성 고려**: 실제 공격 상황에서 사용 가능한 현실적 PoC 개발
    - **방어 관점**: 공격자와 방어자 양쪽 시각에서 균형잡힌 분석
    
    🔄 **자율적 사이클 워크플로우**:
    ```
    현재 상태 분석 → 개선 계획 수립 → 코드 생성 → 테스트 실행 → 결과 평가
           ↑                                                           ↓
    완성도 판단 ← 추가 개선 필요 시 ← 다음 사이클 계획 ← 성과 측정 ←
    ```
    
    🎨 **창의적 PoC 개발 영역**:
    - **새로운 공격 벡터**: 기존에 시도하지 않은 독창적 접근법
    - **복합 취약점**: 여러 취약점을 조합한 고급 공격 시나리오
    - **가스 최적화**: 실제 공격에서 경제적으로 실행 가능한 효율적 방법
    - **타이밍 공격**: 블록체인 특성을 활용한 시간 기반 공격
    - **MEV 활용**: 최대 추출 가치를 고려한 정교한 공격 설계
    
    Args:
        sid: 시나리오 ID (자율적 개선 대상)
        foundry_root_path: Foundry 프로젝트 루트 디렉토리 경로
    
    Returns:
        dict: 자율적 사이클 시작 정보 및 LLM 가이드
        - cycle_started: 사이클 시작 여부
        - initial_analysis_data: 현재 상황 분석 데이터
        - llm_instructions: LLM을 위한 상세 실행 지침
        - success: 사이클 준비 성공 여부
    
    📋 **사용 예시**:
    ```python
    # PoC 자율적 개선 사이클 시작
    cycle_result = await llm_autonomous_verification_cycle(
        sid="REENTRANCY_ATTACK_001",
        foundry_root_path="/path/to/foundry/project"
    )
    
    if cycle_result["success"]:
        print("🤖 자율적 개선 사이클 시작!")
        print("LLM 지침:")
        print(cycle_result["llm_instructions"])
        
        # LLM이 제공된 지침에 따라 자율적으로 개선 진행
        # 1. 현재 상황 분석
        # 2. 개선 계획 수립  
        # 3. llm_generate_test_improvement 호출
        # 4. execute_unit_test로 검증
        # 5. 결과 평가 및 다음 단계 결정
        
    else:
        print("❌ 자율적 사이클 시작 실패")
        print(cycle_result.get("error", "알 수 없는 오류"))
    ```
    
    🌟 **기대 효과**:
    - **완성도 극대화**: 인간이 놓칠 수 있는 부분까지 자동 보완
    - **창의성 확보**: LLM의 창의적 사고로 독창적 공격 시나리오 개발
    - **효율성 향상**: 반복적 개선 작업의 자동화로 개발 시간 단축
    - **품질 보장**: 체계적 자체 검증으로 PoC 신뢰성 확보
    
    ⚠️ **주의사항**:
    - LLM의 자율적 판단에 의존하므로 최종 검토는 필수
    - 복잡한 개선사항은 여러 사이클에 걸쳐 점진적으로 적용
    - 생성된 코드는 반드시 별도 환경에서 안전성 검증 필요
    
    ✅ **성공 시**: LLM 주도 자율적 PoC 개선 프로세스 시작
    ❌ **실패 시**: 시나리오 상태 문제 또는 환경 설정 오류
    """
    logger.info(f"[llm_autonomous_verification_cycle] LLM 자율적 검증 사이클 시작: {sid}")
    
    cycle_result = {
        "cycle_started": True,
        "initial_analysis_data": {},
        "llm_instructions": "",
        "success": True
    }
    
    try:
        # 1. LLM 분석을 위한 현재 상황 데이터 수집
        analysis_data = await llm_assess_verification_needs(sid)
        cycle_result["initial_analysis_data"] = analysis_data
        
        if "error" in analysis_data:
            return {"error": analysis_data["error"], "success": False}
        
        # 2. LLM에게 제공할 자율적 검증 지침
        llm_instructions = f"""
🎯 **자율적 검증 사이클 미션**

당신은 스마트컨트랙트 보안 검증 전문가로서, 다음 시나리오에 대한 완전 자율적 검증을 수행해야 합니다.

**현재 시나리오**: {analysis_data['scenario_basic_info']['title']}
**카테고리**: {analysis_data['scenario_basic_info']['category']} 
**심각도**: {analysis_data['scenario_basic_info']['severity']}

**현재 상황 분석**:
- 테스트 실행 횟수: {analysis_data['test_execution_stats']['total_runs']}
- 성공률: {analysis_data['test_execution_stats']['successful_runs']}/{analysis_data['test_execution_stats']['total_runs']}
- 현재 테스트 함수 수: {sum(info['function_count'] for info in analysis_data['current_test_code'].values())}
- 인사이트 수: {analysis_data['insights_status']['total_insights']}

**자율적 판단 및 실행 단계**:

1️⃣ **현재 테스트 분석**: 위 데이터를 바탕으로 현재 테스트의 완성도와 부족한 점을 분석하세요.

2️⃣ **추가 검증 영역 식별**: 시나리오 특성을 고려하여 누락된 보안 검증 영역을 식별하세요.

3️⃣ **새 테스트 케이스 설계**: 구체적인 Solidity 테스트 함수를 설계하세요.

4️⃣ **테스트 코드 생성**: `llm_generate_test_improvement` 도구를 사용하여 새로운 테스트를 추가하세요.

5️⃣ **테스트 실행**: `execute_single_unit_test` 도구로 개선된 테스트를 실행하세요.

6️⃣ **결과 분석**: 실행 결과를 분석하고 추가 개선이 필요한지 판단하세요.

7️⃣ **사이클 반복**: 필요시 2-6단계를 반복하여 검증 완성도를 높이세요.

**주의사항**:
- 시나리오의 특성({analysis_data['scenario_basic_info']['category']})을 반드시 고려하세요
- 단순한 반복이 아닌 창의적이고 효과적인 테스트를 설계하세요  
- 각 단계에서 스스로 판단하고 결정하세요

**지금 바로 1단계부터 시작하세요!** 🚀
"""
        
        cycle_result["llm_instructions"] = llm_instructions
        
        logger.info(f"LLM 자율적 검증 사이클 데이터 준비 완료: {sid}")
        
        return cycle_result
        
    except Exception as e:
        logger.error(f"LLM 자율적 검증 사이클 오류: {e}")
        return {
            "success": False,
            "error": str(e),
            "cycle_result": cycle_result
        }

@mcp.tool()
async def get_test_insights(sid: str, test_name: str = "") -> dict:
    """
    [MCP 시스템 컨텍스트]
    특정 테스트 또는 모든 테스트의 인사이트를 조회합니다.
    
    Args:
        sid: 시나리오 ID
        test_name: 테스트 이름 (비어있으면 모든 테스트)
    
    Returns:
        dict: 테스트 인사이트
    """
    logger.info(f"[get_test_insights] 호출: sid={sid}, test_name={test_name}")
    
    doc = load_scenario(sid)
    if not doc:
        return {"error": f"시나리오 {sid}가 존재하지 않습니다."}
    
    try:
        if test_name:
            # 특정 테스트의 인사이트만 조회
            insights = doc.get_insights_by_test(test_name)
            return {
                "success": True,
                "test_name": test_name,
                "insights": insights,
                "insights_count": len(insights)
            }
        else:
            # 모든 테스트의 인사이트 조회
            all_insights = doc.get_cumulative_insights()
            return {
                "success": True,
                "all_insights": all_insights,
                "insights_count": len(all_insights)
            }
    except Exception as e:
        error_msg = f"테스트 인사이트 조회 중 오류: {str(e)}"
        logger.error(error_msg)
        return {"error": error_msg}

@mcp.tool()
async def analyze_test_results_by_test(sid: str, test_name: str, run_id: str, insights: Dict[str, Any]) -> dict:
    """
    [MCP 시스템 컨텍스트]
    특정 테스트의 실행 결과를 분석하고 인사이트를 저장합니다.
    
    Args:
        sid: 시나리오 ID
        test_name: 테스트 이름
        run_id: 분석 대상 실행 ID
        insights: LLM이 도출한 인사이트
    
    Returns:
        dict: 분석 결과
    """
    logger.info(f"[analyze_test_results_by_test] 호출: sid={sid}, test_name={test_name}, run_id={run_id}")
    
    doc = load_scenario(sid)
    if not doc:
        return {"error": f"시나리오 {sid}가 존재하지 않습니다."}
    
    # 테스트 존재 확인
    test_info = doc.get_unit_test(test_name)
    if not test_info:
        return {"error": f"테스트 '{test_name}'이 시나리오 {sid}에 존재하지 않습니다."}
    
    try:
        # 인사이트 저장 (test_name 포함)
        doc.add_test_insight(run_id, insights, test_name)
        save_scenario(doc)
        
        insights_count = len(doc.get_insights_by_test(test_name))
        
        logger.info(f"테스트별 인사이트 저장 완료: sid={sid}, test_name={test_name}, run_id={run_id}")
        return {
            "success": True,
            "message": f"테스트 '{test_name}'의 인사이트가 저장되었습니다.",
            "test_insights_count": insights_count
        }
    except Exception as e:
        error_msg = f"테스트별 인사이트 저장 중 오류: {str(e)}"
        logger.error(error_msg)
        return {"error": error_msg}

@mcp.tool()
async def generate_poc_code(sid: str, foundry_root_path: str, poc_type: str = "contract") -> dict:
    """
    🎯 **독립적 PoC 코드 생성: 테스트와 분리된 실제 공격 코드**
    
    시나리오와 등록된 테스트들의 인사이트를 바탕으로 **테스트와 완전히 분리된** 
    독립적인 PoC 코드를 생성하는 도구입니다. 기존 src/ 컨트랙트를 참조하여 
    실제 공격에 사용할 수 있는 완성된 PoC를 만들어냅니다.
    
    🎯 **PoC 개발에서의 역할**:
    - 테스트 코드와 완전히 분리된 독립적인 공격 컨트랙트 생성
    - 기존 src/ 폴더의 컨트랙트 구조를 참조하여 현실적인 PoC 작성
    - 실제 배포 및 실행 가능한 형태의 공격 코드 제공
    - script/ 폴더의 배포 스크립트 또는 독립 컨트랙트로 생성 가능
    
    💡 **LLM 활용 가이드**:
    1. **기존 코드베이스 분석**: src/ 폴더의 취약한 컨트랙트 구조 파악
    2. **테스트 인사이트 활용**: 등록된 테스트들에서 발견된 취약점 패턴 적용
    3. **독립적 구현**: 테스트 프레임워크에 의존하지 않는 순수 Solidity 코드
    4. **실행 가능성 확보**: 실제 네트워크에서 배포/실행 가능한 형태로 작성
    
    🔧 **생성되는 PoC 유형**:
    - **contract**: 독립적인 공격 컨트랙트 (.sol 파일)
    - **script**: Foundry 배포 스크립트 (script/ 폴더용)
    - **exploit**: 완전한 exploit 시나리오 (컨트랙트 + 실행 로직)
    
    📁 **코드베이스 참조 구조**:
    - src/ 폴더: 취약한 대상 컨트랙트들
    - test/ 폴더: 등록된 테스트들의 공격 패턴
    - script/ 폴더: 배포 및 실행 스크립트들
    
    🔄 **생성 후 권장 워크플로우**:
    1. **코드 검토**: 생성된 PoC의 로직과 구조 확인
    2. **의존성 확인**: import 구문과 컨트랙트 참조 검증
    3. **컴파일 테스트**: forge build로 컴파일 가능성 확인
    4. **배포 테스트**: 테스트넷에서 실제 배포 및 실행 검증
    5. **문서화**: PoC 사용법과 공격 시나리오 문서 작성
    
    Args:
        sid: 시나리오 ID
        foundry_root_path: Foundry 프로젝트 루트 경로
        poc_type: PoC 유형 ("contract", "script", "exploit")
    
    Returns:
        dict: PoC 생성 결과
        - success: 생성 성공 여부
        - message: 생성 결과 메시지
        - poc_code: 생성된 PoC 코드 (Solidity)
        - file_path: 저장된 파일 경로
        - poc_type: 생성된 PoC 유형
        - dependencies: 필요한 의존성 목록
    
    📋 **사용 예시**:
    ```python
    # 독립적인 공격 컨트랙트 생성
    poc_result = await generate_poc_code(
        sid="REENTRANCY_ATTACK_001",
        foundry_root_path="/path/to/foundry/project",
        poc_type="contract"
    )
    
    if poc_result["success"]:
        print("🎉 독립적 PoC 코드 생성 완료!")
        print(f"파일 경로: {poc_result['file_path']}")
        print(f"PoC 유형: {poc_result['poc_type']}")
        
        # 생성된 PoC 코드 확인
        print("생성된 PoC 코드:")
        print(poc_result["poc_code"])
        
        # 컴파일 테스트
        # forge build
        
    else:
        print("❌ PoC 생성 실패")
        print(poc_result.get("message", "알 수 없는 오류"))
    ```
    
    ⚠️ **주의사항**:
    - 기존 src/ 컨트랙트 구조를 정확히 참조해야 함
    - 생성된 PoC는 반드시 컴파일 및 배포 테스트 필요
    - 실제 메인넷 사용 시 법적/윤리적 책임 고려 필요
    
    ✅ **성공 시**: 독립적 PoC 코드 제공, 컴파일 및 배포 테스트 단계로 진행
    ❌ **실패 시**: 코드베이스 분석 실패, 생성 오류 등의 구체적 원인 제시
    """
    logger.info(f"[generate_poc_code] 호출: sid={sid}, poc_type={poc_type}")
    
    doc = load_scenario(sid)
    if not doc:
        return {"error": f"시나리오 {sid}가 존재하지 않습니다."}
    
    try:
        # 1. 기존 src/ 폴더 분석
        src_path = os.path.join(foundry_root_path, "src")
        if not os.path.exists(src_path):
            return {"error": f"src 폴더가 존재하지 않습니다: {src_path}"}
        
        # src 폴더의 컨트랙트 파일들 스캔
        contract_files = []
        for file in os.listdir(src_path):
            if file.endswith('.sol'):
                contract_files.append(file)
        
        if not contract_files:
            return {"error": f"src 폴더에 Solidity 파일이 없습니다: {src_path}"}
        
        # 2. 등록된 테스트들의 인사이트 수집
        test_insights = []
        if hasattr(doc, 'test_insights') and doc.test_insights:
            test_insights = doc.test_insights[-3:]  # 최근 3개 인사이트만
        
        # 3. 시나리오 메타 정보
        scenario_info = {
            "id": doc.meta.get("id", sid),
            "title": doc.meta.get("title", ""),
            "category": doc.meta.get("category", ""),
            "severity": doc.meta.get("severity", "")
        }
        
        # 4. PoC 코드 생성
        poc_code = generate_poc_template(
            scenario_info=scenario_info,
            contract_files=contract_files,
            test_insights=test_insights,
            poc_type=poc_type,
            foundry_root_path=foundry_root_path
        )
        
        # 5. 파일 저장
        if poc_type == "script":
            output_dir = os.path.join(foundry_root_path, "script")
            file_name = f"{sid}_Exploit.s.sol"
        else:
            output_dir = os.path.join(foundry_root_path, "src")
            file_name = f"{sid}_PoC.sol"
        
        os.makedirs(output_dir, exist_ok=True)
        file_path = os.path.join(output_dir, file_name)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(poc_code)
        
        # 6. 시나리오 업데이트
        if not hasattr(doc, 'code') or not isinstance(doc.code, dict):
            doc.code = {}
        
        doc.code["poc_contract"] = poc_code
        doc.code["poc_file_path"] = file_path
        doc.code["poc_type"] = poc_type
        doc.code["target_contract_name"] = scenario_info["id"]
        
        save_scenario(doc)
        
        logger.info(f"독립적 PoC 코드 생성 완료: sid={sid}, file={file_path}")
        return {
            "success": True,
            "message": f"독립적 PoC 코드가 생성되었습니다: {file_path}",
            "poc_code": poc_code,
            "file_path": file_path,
            "poc_type": poc_type,
            "dependencies": contract_files
        }
    except Exception as e:
        error_msg = f"PoC 코드 생성 중 오류: {str(e)}"
        logger.error(error_msg)
        return {"error": error_msg}

def generate_poc_template(scenario_info: dict, contract_files: list, test_insights: list, poc_type: str, foundry_root_path: str) -> str:
    """PoC 코드 템플릿 생성"""
    
    # 기본 헤더
    header = f"""// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

/**
 * @title {scenario_info['title']} PoC
 * @dev 시나리오 ID: {scenario_info['id']}
 * @dev 카테고리: {scenario_info['category']}
 * @dev 심각도: {scenario_info['severity']}
 * @dev 생성일: {datetime.datetime.utcnow().isoformat()}
 * 
 * 이 PoC는 테스트와 분리된 독립적인 공격 코드입니다.
 * 실제 취약점 검증 및 보안 연구 목적으로만 사용하세요.
 */
"""
    
    # Import 구문 생성
    imports = []
    for contract_file in contract_files:
        contract_name = contract_file.replace('.sol', '')
        imports.append(f'import "../src/{contract_file}";')
    
    if poc_type == "script":
        imports.append('import "forge-std/Script.sol";')
        imports.append('import "forge-std/console.sol";')
    
    import_section = "\n".join(imports)
    
    # 인사이트 기반 주석 생성
    insights_comments = []
    if test_insights:
        insights_comments.append("/**")
        insights_comments.append(" * 테스트에서 발견된 주요 인사이트:")
        for i, insight in enumerate(test_insights):
            if isinstance(insight, dict):
                patterns = insight.get('patterns', '정보 없음')
                security_implications = insight.get('security_implications', '정보 없음')
                insights_comments.append(f" * {i+1}. 패턴: {patterns}")
                insights_comments.append(f" *    보안 영향: {security_implications}")
        insights_comments.append(" */")
    
    insights_section = "\n".join(insights_comments) if insights_comments else ""
    
    # PoC 유형별 코드 생성
    if poc_type == "script":
        main_code = f"""
contract {scenario_info['id']}ExploitScript is Script {{
    function run() external {{
        vm.startBroadcast();
        
        // TODO: 실제 공격 로직 구현
        // 1. 대상 컨트랙트 주소 설정
        // 2. 공격 컨트랙트 배포
        // 3. 공격 실행
        // 4. 결과 확인
        
        console.log("PoC 실행 완료");
        
        vm.stopBroadcast();
    }}
}}"""
    else:
        main_code = f"""
contract {scenario_info['id']}PoC {{
    // TODO: 필요한 상태 변수 선언
    
    constructor() {{
        // TODO: 초기화 로직
    }}
    
    function exploit() external {{
        // TODO: 실제 공격 로직 구현
        // 기존 src/ 컨트랙트들을 참조하여 구현하세요
    }}
    
    function verify() external view returns (bool) {{
        // TODO: 공격 성공 여부 확인 로직
        return true;
    }}
}}"""
    
    # 전체 코드 조합
    full_code = f"""{header}

{import_section}

{insights_section}

{main_code}
"""
    
    return full_code

################################################################################
# 새로 추가: n개 유닛테스트 관리 도구들
################################################################################

@mcp.tool()
async def add_unit_test(sid: str, test_name: str, description: str, test_file_path: str, expected_behavior: str = "", tags: List[str] = None) -> dict:
    """
    🧪 **PoC 테스트 케이스 등록: 기존 유닛테스트 연결**
    
    등록된 시나리오에 **이미 존재하는** 유닛테스트를 연결하여 PoC 검증 체계를 구축하는 도구입니다.
    이 도구는 새로운 테스트 코드를 생성하지 않고, 기존 코드베이스의 테스트를 시나리오에 등록합니다.
    
    🎯 **PoC 개발에서의 역할**:
    - 기존 테스트 파일에서 관련 테스트 함수를 시나리오에 연결
    - 실제 존재하는 테스트 코드를 기반으로 한 신뢰성 있는 검증
    - 코드베이스와 일관성을 유지하며 PoC 검증 체계 구축
    - 테스트와 PoC 코드를 분리하여 명확한 역할 구분
    
    💡 **LLM 사용 가이드**:
    1. **기존 테스트 파일 확인**: test/ 폴더의 실제 테스트 파일 경로 지정
    2. **테스트 함수 식별**: 파일 내의 특정 test_ 함수명 지정
    3. **테스트 목적 명시**: 해당 테스트가 검증하는 취약점 측면 설명
    4. **태그 분류**: 테스트의 성격과 중요도에 따른 태그 부여
    
    🏷️ **효과적인 태그 활용**:
    - "existing_test": 기존 코드베이스의 테스트
    - "vulnerability_test": 취약점 검증 테스트
    - "edge_case": 경계값이나 특수 상황 테스트
    - "security_critical": 보안상 중요한 테스트
    - "poc_validation": PoC 검증용 테스트
    
    📁 **파일 경로 예시**:
    - "test/VulnerableContract.t.sol" (상대 경로)
    - "/absolute/path/to/test/SecurityTest.t.sol" (절대 경로)
    - "test/generated/ExploitTest.t.sol" (생성된 테스트)
    
    🔄 **다음 단계 워크플로우**:
    1. execute_unit_test로 등록된 테스트 실행
    2. get_test_logs로 실행 결과 상세 분석
    3. analyze_test_results_by_test로 인사이트 도출
    4. 필요시 추가 기존 테스트 등록
    5. 별도로 generate_poc_code로 독립적인 PoC 코드 생성
    
    Args:
        sid: 시나리오 ID (기존에 등록된 시나리오여야 함)
        test_name: 테스트 함수 이름 (예: "test_reentrancy_attack")
        description: 테스트의 목적과 검증 내용 설명
        test_file_path: 기존 테스트 파일의 경로 (상대 또는 절대 경로)
        expected_behavior: 예상되는 실행 결과 (성공/실패/특정 상태 변화 등)
        tags: 테스트 분류를 위한 태그 목록
    
    Returns:
        dict: 테스트 등록 결과 및 현재 테스트 목록 정보
        
    📋 **사용 예시**:
    ```python
    await add_unit_test(
        sid="REENTRANCY_ATTACK_001",
        test_name="test_reentrancy_exploit",
        description="기존 테스트 파일의 reentrancy 공격 검증 테스트",
        test_file_path="test/ReentrancyTest.t.sol",
        expected_behavior="공격자가 초기 잔액보다 많은 토큰을 획득함",
        tags=["existing_test", "vulnerability_test", "poc_validation"]
    )
    ```
    
    ✅ **성공 시**: 기존 테스트 등록 완료, 테스트 실행 준비
    ❌ **실패 시**: 파일 없음, 중복 테스트명 등의 에러 메시지
    """
    logger.info(f"[add_unit_test] 호출: sid={sid}, test_name={test_name}, test_file_path={test_file_path}")
    
    doc = load_scenario(sid)
    if not doc:
        return {"error": f"시나리오 {sid}가 존재하지 않습니다."}
    
    # 테스트 파일 존재 확인
    if not os.path.exists(test_file_path):
        return {"error": f"테스트 파일이 존재하지 않습니다: {test_file_path}"}
    
    try:
        if tags is None:
            tags = []
        
        # 기존 테스트 파일에서 코드 읽기
        with open(test_file_path, 'r', encoding='utf-8') as f:
            file_content = f.read()
        
        # 특정 테스트 함수가 파일에 존재하는지 확인
        if f"function {test_name}" not in file_content:
            return {"error": f"테스트 함수 '{test_name}'이 파일 {test_file_path}에서 찾을 수 없습니다."}
        
        # 테스트 정보를 시나리오에 등록 (파일 경로 포함)
        new_test = doc.add_unit_test_reference(test_name, description, test_file_path, expected_behavior, tags)
        save_scenario(doc)
        
        logger.info(f"기존 유닛테스트 등록 완료: sid={sid}, test_name={test_name}, file={test_file_path}")
        return {
            "success": True,
            "message": f"기존 유닛테스트 '{test_name}'이 시나리오 {sid}에 등록되었습니다.",
            "test_info": new_test,
            "file_path": test_file_path
        }
    except Exception as e:
        error_msg = f"유닛테스트 등록 중 오류: {str(e)}"
        logger.error(error_msg)
        return {"error": error_msg}

@mcp.tool()
async def get_unit_tests(sid: str) -> dict:
    """
    [MCP 시스템 컨텍스트]
    시나리오의 모든 유닛테스트 목록을 조회합니다.
    
    Args:
        sid: 시나리오 ID
    
    Returns:
        dict: 유닛테스트 목록 및 요약 정보
    """
    logger.info(f"[get_unit_tests] 호출: sid={sid}")
    
    doc = load_scenario(sid)
    if not doc:
        return {"error": f"시나리오 {sid}가 존재하지 않습니다."}
    
    try:
        test_summary = doc.get_test_summary()
        
        return {
            "success": True,
            "unit_tests": doc.unit_tests,
            "summary": test_summary
        }
    except Exception as e:
        error_msg = f"유닛테스트 조회 중 오류: {str(e)}"
        logger.error(error_msg)
        return {"error": error_msg}

@mcp.tool()
async def execute_unit_test(sid: str, test_name: str, foundry_root_path: str) -> dict:
    """
    ⚡ **PoC 테스트 실행: 개별 공격 시나리오 검증**
    
    추가된 유닛테스트를 실제로 실행하여 공격 시나리오가 예상대로 작동하는지 검증하는 도구입니다.
    각 테스트의 성공/실패를 통해 PoC의 유효성을 확인하고, 실행 과정에서 발생하는 
    모든 정보를 수집하여 PoC 개선에 활용합니다.
    
    🎯 **PoC 개발에서의 역할**:
    - 이론적 공격 시나리오를 실제 블록체인 환경에서 검증
    - 테스트 실패 시 코드 수정 방향 제시
    - 테스트 성공 시 공격 패턴과 결과 데이터 수집
    - 가스 사용량, 상태 변화, 이벤트 로그 등 실행 컨텍스트 분석
    
    💡 **LLM 실행 결과 활용 가이드**:
    1. **성공 시**: 
       - stdout에서 console.log 출력 확인
       - 가스 사용량과 상태 변화 패턴 분석
       - 다음 테스트 케이스 설계에 활용
    2. **실패 시**:
       - stderr에서 구체적 에러 원인 파악
       - 컴파일 에러 vs 런타임 에러 구분
       - 테스트 코드 수정 또는 환경 설정 조정
    3. **부분 성공 시**:
       - 예상과 다른 결과의 원인 분석
       - 추가 검증 로직 필요성 판단
    
    🔍 **수집되는 실행 정보**:
    - 테스트 성공/실패 상태
    - 표준 출력 (console.log, 가스 정보 등)
    - 에러 메시지 (컴파일/런타임 에러)
    - 실행 ID (추후 상세 분석용)
    - 실행 시간 및 환경 정보
    
    🔄 **실행 후 권장 워크플로우**:
    1. **성공한 경우**:
       - get_test_logs로 상세 실행 로그 분석
       - analyze_test_results_by_test로 인사이트 도출
       - 다음 테스트 케이스 추가 또는 PoC 통합 진행
    2. **실패한 경우**:
       - 에러 메시지 분석하여 문제점 파악
       - 테스트 코드 수정 또는 환경 설정 조정
       - 수정 후 재실행하여 검증
    
    🚨 **일반적인 실패 원인과 해결책**:
    - **컴파일 에러**: import 누락, 문법 오류 → 테스트 코드 수정
    - **런타임 에러**: 잘못된 주소, 권한 부족 → 테스트 환경 설정 확인
    - **Assertion 실패**: 예상과 다른 결과 → 공격 로직 또는 검증 로직 재검토
    - **가스 부족**: 복잡한 공격 → 가스 한도 조정 또는 최적화
    
    Args:
        sid: 시나리오 ID
        test_name: 실행할 테스트 함수 이름
        foundry_root_path: Foundry 프로젝트 루트 디렉토리 경로
    
    Returns:
        dict: 테스트 실행 결과 및 상세 정보
        - success: 테스트 성공 여부
        - test_name: 실행된 테스트 이름
        - stdout: 표준 출력 (console.log, 가스 정보 등)
        - stderr: 에러 메시지
        - run_id: 실행 ID (상세 분석용)
        - status: 실행 상태 ("SUCCESS" 또는 "TEST_FAILURE")
    
    📋 **사용 예시**:
    ```python
    result = await execute_unit_test(
        sid="REENTRANCY_ATTACK_001",
        test_name="test_basic_reentrancy",
        foundry_root_path="/path/to/foundry/project"
    )
    
    if result["success"]:
        print("✅ 공격 성공! PoC 유효성 확인됨")
        print(f"실행 로그: {result['stdout']}")
        # 다음 단계: 인사이트 분석
    else:
        print("❌ 공격 실패, 코드 수정 필요")
        print(f"에러: {result['stderr']}")
        # 다음 단계: 에러 분석 및 코드 수정
    ```
    
    ✅ **성공 시**: 공격 시나리오 검증 완료, 인사이트 분석 단계로 진행
    ❌ **실패 시**: 구체적 에러 정보 제공, 코드 수정 후 재실행 필요
    """
    logger.info(f"[execute_unit_test] 호출: sid={sid}, test_name={test_name}")
    
    doc = load_scenario(sid)
    if not doc:
        return {"error": f"시나리오 {sid}가 존재하지 않습니다."}
    
    # 테스트 존재 확인
    test_info = doc.get_unit_test(test_name)
    if not test_info:
        return {"error": f"테스트 '{test_name}'이 시나리오 {sid}에 존재하지 않습니다."}
    
    try:
        # Foundry 테스트 실행 (특정 테스트 함수만)
        forge_tool = FoundryTool()
        success, stdout, stderr = forge_tool.runUnitTest(
            test_contract_name=None,  # 전체 컨트랙트에서 특정 함수만 실행
            foundry_root_path=foundry_root_path
        )
        
        # 실행 결과 저장
        status = "SUCCESS" if success else "TEST_FAILURE"
        diff_for_runlog = f"[{sid}] execute_unit_test: {test_name}"
        run_id = str(uuid.uuid4())
        
        # 시나리오 객체에 로그 추가 (test_name 포함)
        doc.add_run_log(
            run_id=run_id,
            status=status,
            diff=diff_for_runlog,
            stdout=stdout,
            stderr=stderr,
            test_name=test_name
        )
        
        # 힌트 업데이트
        doc.update_hints_from_run(run_id, status, stdout, stderr)
        
        # 시나리오 저장
        save_scenario(doc)
        
        # 글로벌 runlog 테이블에도 저장
        add_runlog_entry(sid, status, diff_for_runlog, stdout, stderr, test_name)
        
        logger.info(f"유닛테스트 실행 완료: sid={sid}, test_name={test_name}, run_id={run_id}")
        
        return {
            "success": success,
            "test_name": test_name,
            "stdout": stdout,
            "stderr": stderr,
            "run_id": run_id,
            "status": status
        }
    except Exception as e:
        error_msg = f"유닛테스트 실행 중 오류: {str(e)}"
        logger.error(error_msg)
        return {"error": error_msg}

@mcp.tool()
async def execute_all_unit_tests(sid: str, foundry_root_path: str) -> dict:
    """
    [MCP 시스템 컨텍스트]
    시나리오의 모든 유닛테스트를 순차적으로 실행합니다.
    
    Args:
        sid: 시나리오 ID
        foundry_root_path: Foundry 프로젝트 경로
    
    Returns:
        dict: 모든 테스트 실행 결과 요약
    """
    logger.info(f"[execute_all_unit_tests] 호출: sid={sid}")
    
    doc = load_scenario(sid)
    if not doc:
        return {"error": f"시나리오 {sid}가 존재하지 않습니다."}
    
    if not doc.unit_tests:
        return {"error": f"시나리오 {sid}에 유닛테스트가 없습니다."}
    
    results = []
    total_tests = len(doc.unit_tests)
    successful_tests = 0
    
    try:
        for test in doc.unit_tests:
            test_name = test.get("test_name", "")
            if not test_name:
                continue
            
            logger.info(f"테스트 실행 중: {test_name}")
            
            # 개별 테스트 실행
            result = await execute_unit_test(sid, test_name, foundry_root_path)
            results.append({
                "test_name": test_name,
                "result": result
            })
            
            if result.get("success", False):
                successful_tests += 1
        
        # 전체 실행 결과 요약
        summary = {
            "total_tests": total_tests,
            "successful_tests": successful_tests,
            "failed_tests": total_tests - successful_tests,
            "success_rate": successful_tests / total_tests if total_tests > 0 else 0
        }
        
        logger.info(f"모든 유닛테스트 실행 완료: sid={sid}, 성공률={summary['success_rate']:.2%}")
        
        return {
            "success": True,
            "summary": summary,
            "test_results": results
        }
    except Exception as e:
        error_msg = f"유닛테스트 일괄 실행 중 오류: {str(e)}"
        logger.error(error_msg)
        return {"error": error_msg}

@mcp.tool()
async def get_test_logs(sid: str, test_name: str = "") -> dict:
    """
    [MCP 시스템 컨텍스트]
    특정 테스트 또는 모든 테스트의 실행 로그를 조회합니다.
    
    Args:
        sid: 시나리오 ID
        test_name: 테스트 이름 (비어있으면 모든 테스트)
    
    Returns:
        dict: 테스트 실행 로그
    """
    logger.info(f"[get_test_logs] 호출: sid={sid}, test_name={test_name}")
    
    doc = load_scenario(sid)
    if not doc:
        return {"error": f"시나리오 {sid}가 존재하지 않습니다."}
    
    try:
        if test_name:
            # 특정 테스트의 로그만 조회
            logs = doc.get_runlog_by_test(test_name)
            return {
                "success": True,
                "test_name": test_name,
                "logs": logs,
                "log_count": len(logs)
            }
        else:
            # 모든 테스트의 로그 조회
            return {
                "success": True,
                "all_logs": doc.runlog,
                "log_count": len(doc.runlog)
            }
    except Exception as e:
        error_msg = f"테스트 로그 조회 중 오류: {str(e)}"
        logger.error(error_msg)
        return {"error": error_msg}

################################################################################
# 서버 실행  
################################################################################

if __name__ == "__main__":
    # DB 초기화
    init_db()
    
    logger.info("🔄 dynamic-schema MCP server v1.4.0 started")
    logger.info(f"📊 등록된 도구 수: {len(mcp._tool_manager._tools) if hasattr(mcp, '_tool_manager') and hasattr(mcp._tool_manager, '_tools') else '알 수 없음'}")
    
    # MCP 서버 실행 (stdio 모드)
    mcp.run(transport="stdio")