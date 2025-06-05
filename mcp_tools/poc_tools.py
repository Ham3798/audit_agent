"""
PoC-related MCP tools

PoC 코드 생성, LLM 자율적 개선과 관련된 MCP 도구들을 제공합니다.
main.py에서 분리된 MCP 도구들이며, 서비스 레이어를 호출하여 실제 작업을 수행합니다.
"""

from typing import Any, Dict
from mcp.server.fastmcp import FastMCP

from config.logging_config import get_logger
from services import PocService

logger = get_logger("mcp_tools.poc")


class PocMCPTools:
    """
    PoC 관련 MCP 도구 컬렉션
    
    주요 기능:
    - PoC 코드 생성
    - LLM 자율적 검증 및 개선
    - 테스트 개선 사이클
    """
    
    def __init__(self):
        self.poc_service = PocService()
        self.logger = logger
    
    def register_tools(self, mcp_instance):
        """MCP 도구들을 등록합니다."""
        
        @mcp_instance.tool()
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
            self.logger.info(f"[generate_poc_code] 호출: sid={sid}, foundry_root_path={foundry_root_path}, poc_type={poc_type}")
            return self.poc_service.generate_poc_code(sid, foundry_root_path, poc_type)
        
        @mcp_instance.tool()
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
            self.logger.info(f"[llm_assess_verification_needs] 호출: sid={sid}")
            return self.poc_service.llm_assess_verification_needs(sid)
        
        @mcp_instance.tool()
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
            self.logger.info(f"[llm_generate_test_improvement] 호출: sid={sid}, foundry_root_path={foundry_root_path}")
            return self.poc_service.llm_generate_test_improvement(sid, improvement_plan, foundry_root_path)
        
        @mcp_instance.tool()
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
            self.logger.info(f"[llm_autonomous_verification_cycle] 호출: sid={sid}, foundry_root_path={foundry_root_path}")
            return self.poc_service.llm_autonomous_verification_cycle(sid, foundry_root_path)