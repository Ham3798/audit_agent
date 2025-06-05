"""
Analysis-related MCP tools

인사이트 분석, 메타 분석, 결과 해석과 관련된 MCP 도구들을 제공합니다.
main.py에서 분리된 MCP 도구들이며, 서비스 레이어를 호출하여 실제 작업을 수행합니다.
"""

from typing import Any, Dict
from mcp.server.fastmcp import FastMCP

from config.logging_config import get_logger
from services import AnalysisService

logger = get_logger("mcp_tools.analysis")


class AnalysisMCPTools:
    """
    분석 관련 MCP 도구 컬렉션
    
    주요 기능:
    - 테스트 결과 심층 분석
    - 인사이트 도출 및 관리
    - 순차적 검증 프로세스 4-5단계 지원
    """
    
    def __init__(self):
        self.analysis_service = AnalysisService()
        self.logger = logger
    
    def register_tools(self, mcp_instance):
        """MCP 도구들을 등록합니다."""
        
        @mcp_instance.tool()
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
            self.logger.info(f"[analyze_test_results] 호출: sid={sid}, run_id={run_id}, test_name={test_name}")
            return self.analysis_service.analyze_test_results(sid, run_id, insights, test_name)
        
        @mcp_instance.tool()
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
            self.logger.info(f"[get_cumulative_insights] 호출: sid={sid}")
            return self.analysis_service.get_cumulative_insights(sid)
        
        @mcp_instance.tool()
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
            self.logger.info(f"[get_test_insights] 호출: sid={sid}, test_name={test_name}")
            return self.analysis_service.get_test_insights(sid, test_name)
        
        @mcp_instance.tool()
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
            self.logger.info(f"[analyze_test_results_by_test] 호출: sid={sid}, test_name={test_name}, run_id={run_id}")
            return self.analysis_service.analyze_test_results_by_test(sid, test_name, run_id, insights) 