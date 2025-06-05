"""
Scenario-related MCP tools

시나리오 관리와 관련된 MCP 도구들을 제공합니다.
main.py에서 분리된 MCP 도구들이며, 서비스 레이어를 호출하여 실제 작업을 수행합니다.
"""

from typing import Any, Dict, List
from mcp.server.fastmcp import FastMCP

from config.logging_config import get_logger
from services import ScenarioService

logger = get_logger("mcp_tools.scenario")


class ScenarioMCPTools:
    """
    시나리오 관련 MCP 도구 컬렉션
    
    주요 기능:
    - 시나리오 CRUD 관리
    - YAML import/export
    - 순차적 검증 프로세스 1단계 지원
    """
    
    def __init__(self):
        self.scenario_service = ScenarioService()
        self.logger = logger
    
    def register_tools(self, mcp_instance):
        """MCP 도구들을 등록합니다."""
        
        @mcp_instance.tool()
        async def get_scenario(sid: str) -> Dict[str, Any]:
            """
            [MCP 시스템 컨텍스트]
            DB에서 특정 시나리오의 전체 정보를 JSON 형태로 반환합니다.
            시나리오 기반 검증 및 분석에 사용되며, LLM은 이 정보를 바탕으로 시나리오를 이해하거나
            테스트 결과를 해석하고 새로운 인사이트를 도출할 수 있습니다.
            """
            self.logger.info(f"[get_scenario] 호출: {sid}")
            return self.scenario_service.get_scenario(sid)
        
        @mcp_instance.tool()
        async def list_scenarios(random_string: str = "dummy") -> List[str]:
            """
            [MCP 시스템 컨텍스트]
            DB에 저장된 모든 시나리오의 ID 목록을 반환합니다.
            사용자가 검증 대상을 선택하거나 전체 시나리오 현황을 파악하는 데 도움을 줍니다.
            """
            self.logger.info(f"[list_scenarios] 호출")
            return self.scenario_service.list_scenarios()
        
        @mcp_instance.tool()
        def export_scenario_to_yaml(sid: str, path: str) -> str:
            """
            [MCP 시스템 컨텍스트]
            DB에 저장된 특정 시나리오를 YAML 파일 형태로 내보냅니다.
            시나리오의 외부 공유나 백업 목적으로 사용되며, 감사 중에는 DB를 기준으로 작업해야 합니다.
            """
            self.logger.info(f"[export_scenario_to_yaml] 호출: sid={sid}, path={path}")
            return self.scenario_service.export_scenario_to_yaml(sid, path)
        
        @mcp_instance.tool()
        async def bootstrap_from_yaml_files(folder: str = "scenarios"):
            """
            [MCP 시스템 컨텍스트]
            지정된 폴더 내의 YAML 파일들을 읽어와 각 시나리오 정보를 DB에 일괄적으로 저장합니다.
            시스템 초기 설정이나 대량의 시나리오 마이그레이션에 사용되며, 
            이후에는 DB를 통해 시나리오를 관리합니다.
            """
            self.logger.info(f"[bootstrap_from_yaml_files] 호출: folder={folder}")
            return self.scenario_service.bootstrap_from_yaml_files(folder)
        
        @mcp_instance.tool()
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
            self.logger.info(f"[scenario_context] 호출: sid={sid}, test_contract_name={test_contract_name}, foundry_root_path={foundry_root_path}")
            return self.scenario_service.scenario_context(sid, test_contract_name, foundry_root_path)
        
        @mcp_instance.tool()
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
            - schema_1.4.yaml 구조를 정확히 따라야 함 (확장된 필드 지원)
            - 빈 필드도 명시적으로 빈 값으로 설정 필요
            
            🔄 **다음 단계 워크플로우**:
            1. add_unit_test로 다양한 공격 시나리오 테스트 추가
            2. execute_unit_test로 각 테스트 검증
            3. analyze_test_results로 결과 분석 및 인사이트 도출
            4. generate_poc_from_tests로 최종 통합 PoC 생성
            
            📋 **입력 예시 (확장된 스키마 지원)**:
            ```json
            {
              "meta": {
                "id": "CETHER_REENTRANCY_001",
                "title": "Fuse CEther doTransferOut 재진입 공격",
                "category": "Reentrancy",
                "severity": "critical",
                "tags": ["reentrancy", "cether", "fuse", "defi", "lending"]
              },
              "spec": {
                "description": "CEther 컨트랙트의 doTransferOut 함수에서 발생할 수 있는 재진입 공격",
                "actors": [
                  {"id": "attacker", "role": "malicious_user", "trust_level": "untrusted"},
                  {"id": "victim", "role": "normal_user", "trust_level": "trusted"}
                ],
                "assets": [
                  {"name": "ETH", "type": "native_token", "critical": true},
                  {"name": "cETH", "type": "ctoken", "critical": true}
                ],
                "attack_vectors": [
                  "redeem 함수 호출 시 doTransferOut에서 재진입",
                  "borrow 함수 호출 시 doTransferOut에서 재진입"
                ],
                "trust_boundaries": [
                  "CEther 컨트랙트와 외부 사용자 간의 경계"
                ]
              },
              "code": {
                "target_contract_name": "CEther",
                "vulnerable_functions": ["redeem", "redeemUnderlying", "borrow"],
                "vulnerability_pattern": "doTransferOut 함수에서 call.value() 사용 시 재진입 가능"
              },
              "hints": {
                "vulnerability_details": {
                  "root_cause": "CEther.doTransferOut에서 (bool success, ) = to.call.value(amount)(\"\") 사용",
                  "attack_flow": "1. 공격자가 redeem/borrow 호출 -> 2. doTransferOut에서 ETH 전송 -> 3. 공격자 receive 함수에서 재진입",
                  "impact": "풀의 ETH 고갈, 사용자 자금 손실"
                }
              }
            }
            ```
            
            ✅ **성공 시**: 시나리오 등록 완료, PoC 개발 프로젝트 시작 준비
            ❌ **실패 시**: 중복 ID, 스키마 오류 등의 구체적 에러 메시지 반환
            """
            self.logger.info(f"[register_scenario] 호출")
            return self.scenario_service.register_scenario(scenario)
        
        @mcp_instance.tool()
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
            self.logger.info(f"[update_scenario] 호출: sid={sid}")
            return self.scenario_service.update_scenario(sid, update_dict) 