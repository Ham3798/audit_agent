"""
Test-related MCP tools

테스트 실행, 로그 조회, 유닛테스트 관리와 관련된 MCP 도구들을 제공합니다.
main.py에서 분리된 MCP 도구들이며, 서비스 레이어를 호출하여 실제 작업을 수행합니다.
"""

from typing import Any, Dict, List
from mcp.server.fastmcp import FastMCP

from config.logging_config import get_logger
from services import TestService
from file_monitor import FileMonitor

logger = get_logger("mcp_tools.test")


class TestMCPTools:
    """
    테스트 관련 MCP 도구 컬렉션
    
    주요 기능:
    - 테스트 실행 및 관리
    - 테스트 로그 조회
    - 순차적 검증 프로세스 2-3단계 지원
    """
    
    def __init__(self):
        self.file_monitor = FileMonitor()
        self.test_service = TestService(self.file_monitor)
        self.logger = logger
    
    def register_tools(self, mcp_instance):
        """MCP 도구들을 등록합니다."""
        
        @mcp_instance.tool()
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
            self.logger.info(f"[execute_single_unit_test] 호출: sid={sid}, test_contract_name={test_contract_name}, foundry_root_path={foundry_root_path}, test_name={test_name}")
            return self.test_service.execute_single_unit_test(sid, test_contract_name, foundry_root_path, test_name)
        
        @mcp_instance.tool()
        async def get_unit_test_logs(sid: str) -> list:
            """
            [MCP 시스템 컨텍스트]
            특정 시나리오 ID(sid)에 대한 모든 유닛테스트 실행 결과(runlog) 기록들을 시간순으로 조회합니다.
            LLM은 이 로그들을 바탕으로 테스트 히스토리를 파악하거나, 특정 실행 결과를 분석할 수 있습니다.
            
            [반환값]
            - 시나리오의 `runlog` 필드에 저장된 모든 실행 로그 목록 (각 로그는 run_id, 상태, stdout, stderr 등 포함)
            """
            self.logger.info(f"[get_unit_test_logs] 호출: sid={sid}")
            return self.test_service.get_unit_test_logs(sid)
        
        @mcp_instance.tool()
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
            self.logger.info(f"[get_single_unit_test_log] 호출: sid={sid}, run_id={run_id}")
            return self.test_service.get_single_unit_test_log(sid, run_id)
        
        @mcp_instance.tool()
        async def add_unit_test(sid: str, test_name: str, description: str, test_file_path: str, expected_behavior: str = "", tags: List[str] = None, workspace_root: str = None) -> dict:
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
            self.logger.info(f"[add_unit_test] 호출: sid={sid}, test_name={test_name}, workspace_root={workspace_root}")
            return self.test_service.add_unit_test(sid, test_name, description, test_file_path, expected_behavior, tags, workspace_root)
        
        @mcp_instance.tool()
        async def get_unit_tests(sid: str) -> dict:
            """
            [MCP 시스템 컨텍스트]
            시나리오의 모든 유닛테스트 목록을 조회합니다.
            
            Args:
                sid: 시나리오 ID
            
            Returns:
                dict: 유닛테스트 목록 및 요약 정보
            """
            self.logger.info(f"[get_unit_tests] 호출: sid={sid}")
            return self.test_service.get_unit_tests(sid)
        
        @mcp_instance.tool()
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
            self.logger.info(f"[execute_unit_test] 호출: sid={sid}, test_name={test_name}, foundry_root_path={foundry_root_path}")
            return self.test_service.execute_unit_test(sid, test_name, foundry_root_path)
        
        @mcp_instance.tool()
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
            self.logger.info(f"[execute_all_unit_tests] 호출: sid={sid}, foundry_root_path={foundry_root_path}")
            return self.test_service.execute_all_unit_tests(sid, foundry_root_path)
        
        @mcp_instance.tool()
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
            self.logger.info(f"[get_test_logs] 호출: sid={sid}, test_name={test_name}")
            return self.test_service.get_test_logs(sid, test_name) 