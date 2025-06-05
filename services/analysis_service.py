"""
Analysis and insight service

테스트 결과 분석, 인사이트 도출, 메타 분석 등 분석과 관련된 모든 비즈니스 로직을 담당합니다.
main.py의 분석 관련 MCP 도구들의 백엔드 로직을 제공합니다.
"""

import json
from typing import Any, Dict, List, Optional

from config.logging_config import get_logger
from database.models import ScenarioDoc
from database.manager import save_scenario, load_scenario

logger = get_logger("services.analysis")


class AnalysisService:
    """
    분석 및 인사이트 서비스
    
    테스트 결과 분석, 인사이트 도출, 누적 분석 등의 기능을 제공합니다.
    """
    
    def __init__(self):
        """AnalysisService 초기화"""
        self.logger = logger
    
    def analyze_test_results(self, sid: str, run_id: str, insights: Dict[str, Any], test_name: str = "") -> Dict[str, Any]:
        """
        테스트 결과 분석 및 인사이트 저장 (순차적 검증 프로세스 4단계)
        
        Args:
            sid: 시나리오 ID
            run_id: 분석 대상 테스트 실행 ID
            insights: 순차적 사고 과정을 통해 도출한 인사이트
            test_name: 테스트 이름 (선택적)
            
        Returns:
            Dict[str, Any]: 분석 결과
        """
        self.logger.info(f"테스트 결과 분석: sid={sid}, run_id={run_id}, test_name={test_name}")
        
        doc = load_scenario(sid)
        if not doc:
            return {"error": f"시나리오 {sid}가 존재하지 않습니다."}
        
        try:
            # 필수 인사이트 필드 검증
            required_fields = ["precondition", "state_changes", "patterns", "security_implications"]
            missing_fields = [field for field in required_fields if field not in insights]
            
            if missing_fields:
                return {"error": f"다음 필수 인사이트 필드가 누락되었습니다: {missing_fields}"}
            
            # 신뢰도 기본값 설정
            if "confidence" not in insights:
                insights["confidence"] = 0.5
            
            # 인사이트 저장
            saved_insight = doc.add_insight(
                run_id=run_id,
                insight=insights,
                test_name=test_name
            )
            
            success = save_scenario(doc)
            if success:
                insights_count = len(doc.test_insights)
                self.logger.info(f"인사이트 저장 완료: sid={sid}, run_id={run_id}, 총 인사이트 수={insights_count}")
                
                return {
                    "success": True,
                    "message": f"시나리오 {sid}에 인사이트가 저장되었습니다.",
                    "insights_count": insights_count,
                    "saved_insight": saved_insight
                }
            else:
                return {"error": "인사이트 저장에 실패했습니다."}
                
        except Exception as e:
            error_msg = f"테스트 결과 분석 중 오류: {str(e)}"
            self.logger.error(error_msg)
            return {"error": error_msg}
    
    def analyze_test_results_by_test(self, sid: str, test_name: str, run_id: str, insights: Dict[str, Any]) -> Dict[str, Any]:
        """
        특정 테스트의 결과 분석 및 인사이트 저장
        
        Args:
            sid: 시나리오 ID
            test_name: 테스트 이름
            run_id: 분석 대상 실행 ID
            insights: LLM이 도출한 인사이트
            
        Returns:
            Dict[str, Any]: 분석 결과
        """
        self.logger.info(f"테스트별 결과 분석: sid={sid}, test_name={test_name}, run_id={run_id}")
        
        doc = load_scenario(sid)
        if not doc:
            return {"error": f"시나리오 {sid}가 존재하지 않습니다."}
        
        try:
            # 테스트 존재 확인
            test_info = doc.get_unit_test(test_name)
            if not test_info:
                return {"error": f"테스트 '{test_name}'이 시나리오 {sid}에 존재하지 않습니다."}
            
            # 인사이트 저장
            saved_insight = doc.add_insight(
                run_id=run_id,
                insight=insights,
                test_name=test_name
            )
            
            success = save_scenario(doc)
            if success:
                insights_count = len(doc.test_insights)
                self.logger.info(f"테스트별 인사이트 저장 완료: sid={sid}, test_name={test_name}, 총 인사이트 수={insights_count}")
                
                return {
                    "success": True,
                    "message": f"테스트 '{test_name}'의 인사이트가 저장되었습니다.",
                    "test_name": test_name,
                    "insights_count": insights_count,
                    "saved_insight": saved_insight
                }
            else:
                return {"error": "인사이트 저장에 실패했습니다."}
                
        except Exception as e:
            error_msg = f"테스트별 결과 분석 중 오류: {str(e)}"
            self.logger.error(error_msg)
            return {"error": error_msg}
    
    def get_cumulative_insights(self, sid: str) -> Dict[str, Any]:
        """
        누적 인사이트 메타 분석 (순차적 검증 프로세스 5단계)
        
        Args:
            sid: 시나리오 ID
            
        Returns:
            Dict[str, Any]: 누적된 모든 인사이트와 메타 분석 정보
        """
        self.logger.info(f"누적 인사이트 조회: sid={sid}")
        
        doc = load_scenario(sid)
        if not doc:
            return {"error": f"시나리오 {sid}가 존재하지 않습니다."}
        
        try:
            insights = doc.test_insights
            insights_count = len(insights)
            
            # 시간순으로 정렬된 인사이트 반환
            sorted_insights = sorted(insights, key=lambda x: x.get("timestamp", ""))
            
            self.logger.info(f"누적 인사이트 조회 완료: sid={sid}, 인사이트 수={insights_count}")
            
            return {
                "success": True,
                "insights": sorted_insights,
                "insights_count": insights_count,
                "meta_analysis": self._generate_meta_analysis(sorted_insights)
            }
        except Exception as e:
            error_msg = f"누적 인사이트 조회 중 오류: {str(e)}"
            self.logger.error(error_msg)
            return {"error": error_msg}
    
    def get_test_insights(self, sid: str, test_name: str = "") -> Dict[str, Any]:
        """
        특정 테스트 또는 모든 테스트의 인사이트 조회
        
        Args:
            sid: 시나리오 ID
            test_name: 테스트 이름 (비어있으면 모든 테스트)
            
        Returns:
            Dict[str, Any]: 테스트 인사이트
        """
        self.logger.info(f"테스트 인사이트 조회: sid={sid}, test_name={test_name}")
        
        doc = load_scenario(sid)
        if not doc:
            return {"error": f"시나리오 {sid}가 존재하지 않습니다."}
        
        try:
            if test_name:
                # 특정 테스트의 인사이트만 조회
                test_insights = [
                    insight for insight in doc.test_insights
                    if insight.get("test_name") == test_name
                ]
                
                return {
                    "success": True,
                    "test_name": test_name,
                    "insights": test_insights,
                    "insights_count": len(test_insights)
                }
            else:
                # 모든 테스트의 인사이트 조회
                return {
                    "success": True,
                    "all_insights": doc.test_insights,
                    "insights_count": len(doc.test_insights),
                    "tests_with_insights": list(set(
                        insight.get("test_name", "")
                        for insight in doc.test_insights
                        if insight.get("test_name")
                    ))
                }
        except Exception as e:
            error_msg = f"테스트 인사이트 조회 중 오류: {str(e)}"
            self.logger.error(error_msg)
            return {"error": error_msg}
    
    def _generate_meta_analysis(self, insights: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        인사이트들에 대한 메타 분석 생성
        
        Args:
            insights: 인사이트 목록
            
        Returns:
            Dict[str, Any]: 메타 분석 결과
        """
        if not insights:
            return {"pattern_summary": "인사이트가 없습니다."}
        
        try:
            # 패턴 분석
            patterns = []
            security_implications = []
            confidence_scores = []
            
            for insight in insights:
                insight_data = insight.get("insight", {})
                
                if "patterns" in insight_data:
                    patterns.append(insight_data["patterns"])
                
                if "security_implications" in insight_data:
                    security_implications.append(insight_data["security_implications"])
                
                if "confidence" in insight_data:
                    confidence_scores.append(insight_data["confidence"])
            
            # 평균 신뢰도 계산
            avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0
            
            # 공통 패턴 추출 (단순화된 버전)
            common_patterns = self._extract_common_patterns(patterns)
            
            # 보안 영향 요약
            security_summary = self._summarize_security_implications(security_implications)
            
            return {
                "total_insights": len(insights),
                "average_confidence": round(avg_confidence, 2),
                "common_patterns": common_patterns,
                "security_summary": security_summary,
                "analysis_timestamp": insights[-1].get("timestamp", "") if insights else ""
            }
        except Exception as e:
            self.logger.error(f"메타 분석 생성 중 오류: {str(e)}")
            return {"error": f"메타 분석 생성 실패: {str(e)}"}
    
    def _extract_common_patterns(self, patterns: List[str]) -> List[str]:
        """
        공통 패턴 추출 (단순화된 구현)
        
        Args:
            patterns: 패턴 목록
            
        Returns:
            List[str]: 공통 패턴들
        """
        if not patterns:
            return []
        
        # 패턴에서 키워드 추출 및 빈도 계산
        keyword_count = {}
        for pattern in patterns:
            words = pattern.lower().split()
            for word in words:
                if len(word) > 3:  # 3글자 이상의 단어만
                    keyword_count[word] = keyword_count.get(word, 0) + 1
        
        # 빈도가 높은 키워드들을 공통 패턴으로 간주
        common_keywords = [
            word for word, count in keyword_count.items()
            if count >= 2 or count / len(patterns) >= 0.5
        ]
        
        return common_keywords[:5]  # 상위 5개만 반환
    
    def _summarize_security_implications(self, implications: List[str]) -> str:
        """
        보안 영향 요약 (단순화된 구현)
        
        Args:
            implications: 보안 영향 목록
            
        Returns:
            str: 요약된 보안 영향
        """
        if not implications:
            return "보안 영향 분석 데이터가 없습니다."
        
        # 키워드 기반 분류
        critical_keywords = ["critical", "high", "severe", "exploit", "vulnerability"]
        medium_keywords = ["medium", "moderate", "risk", "potential"]
        low_keywords = ["low", "minor", "info", "informational"]
        
        critical_count = sum(
            1 for impl in implications
            if any(keyword in impl.lower() for keyword in critical_keywords)
        )
        
        medium_count = sum(
            1 for impl in implications
            if any(keyword in impl.lower() for keyword in medium_keywords)
        )
        
        low_count = len(implications) - critical_count - medium_count
        
        return f"총 {len(implications)}개 보안 영향 분석됨 - 높음: {critical_count}, 중간: {medium_count}, 낮음: {low_count}"
    
    def llm_assess_verification_needs(self, sid: str) -> Dict[str, Any]:
        """
        LLM 자율적 검증 - 1단계: 현재 시나리오 상태 분석
        
        Args:
            sid: 시나리오 ID
            
        Returns:
            Dict[str, Any]: 현재 시나리오의 모든 정보 (LLM이 분석할 원시 데이터)
        """
        self.logger.info(f"LLM 자율적 검증 필요성 평가: sid={sid}")
        
        doc = load_scenario(sid)
        if not doc:
            return {"error": f"시나리오 {sid}가 존재하지 않습니다."}
        
        try:
            # 현재 시나리오의 모든 정보를 JSON으로 변환
            scenario_data = json.loads(doc.to_json())
            
            # 테스트 로그 정보
            test_logs = doc.runlog
            
            # 현재 테스트 코드 스냅샷
            current_test_code = doc.test_code_snapshots
            
            # 파일 변경 이력
            file_changes = doc.patches
            
            self.logger.info(f"LLM 검증 데이터 준비 완료: sid={sid}")
            
            return {
                "scenario_data": scenario_data,
                "test_logs": test_logs,
                "current_test_code": current_test_code,
                "file_changes": file_changes,
                "summary": {
                    "total_tests": len(doc.unit_tests),
                    "total_runs": len(doc.runlog),
                    "total_insights": len(doc.test_insights),
                    "has_patches": len(doc.patches) > 0
                }
            }
        except Exception as e:
            error_msg = f"LLM 검증 필요성 평가 중 오류: {str(e)}"
            self.logger.error(error_msg)
            return {"error": error_msg} 