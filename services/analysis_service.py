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
        
        # 1. 시나리오 존재 확인
        doc = load_scenario(sid)
        if not doc:
            return {"error": f"시나리오 {sid}가 존재하지 않습니다."}
        
        # 2. 입력값 기본 검증
        if not isinstance(insights, dict):
            return {
                "error": "insights는 딕셔너리 형태여야 합니다.",
                "received_type": type(insights).__name__
            }
        
        if not run_id or not run_id.strip():
            return {"error": "run_id가 비어있습니다."}
        
        try:
            # 3. 필수 인사이트 필드 검증 (강화된 검증)
            required_fields = {
                "precondition": "테스트의 전제 조건",
                "state_changes": "관찰된 상태 변화",
                "patterns": "감지된 패턴",
                "security_implications": "보안 영향"
            }
            
            # 3a. 필수 필드 존재 여부 확인
            missing_fields = []
            empty_fields = []
            
            for field, description in required_fields.items():
                if field not in insights:
                    missing_fields.append(f"{field} ({description})")
                elif not insights[field] or (isinstance(insights[field], str) and not insights[field].strip()):
                    empty_fields.append(f"{field} ({description})")
            
            if missing_fields:
                return {
                    "error": f"다음 필수 인사이트 필드가 누락되었습니다: {missing_fields}",
                    "required_fields": required_fields,
                    "received_fields": list(insights.keys())
                }
            
            if empty_fields:
                return {
                    "error": f"다음 필수 인사이트 필드가 비어있습니다: {empty_fields}",
                    "hint": "각 필드에는 의미있는 내용이 포함되어야 합니다."
                }
            
            # 3b. 각 필드의 내용 품질 검증
            field_validation_errors = []
            
            # precondition 검증
            if len(str(insights["precondition"]).strip()) < 10:
                field_validation_errors.append("precondition: 최소 10자 이상의 구체적인 설명이 필요합니다.")
            
            # state_changes 검증
            if len(str(insights["state_changes"]).strip()) < 10:
                field_validation_errors.append("state_changes: 최소 10자 이상의 구체적인 상태 변화 설명이 필요합니다.")
            
            # patterns 검증
            if len(str(insights["patterns"]).strip()) < 10:
                field_validation_errors.append("patterns: 최소 10자 이상의 패턴 설명이 필요합니다.")
            
            # security_implications 검증
            if len(str(insights["security_implications"]).strip()) < 15:
                field_validation_errors.append("security_implications: 최소 15자 이상의 상세한 보안 영향 분석이 필요합니다.")
            
            if field_validation_errors:
                return {
                    "error": "인사이트 필드 내용 품질 검증 실패",
                    "validation_errors": field_validation_errors,
                    "hint": "각 필드에는 충분히 상세하고 의미있는 분석 내용이 포함되어야 합니다."
                }
            
            # 4. confidence 필드 검증 및 기본값 설정
            if "confidence" not in insights:
                insights["confidence"] = 0.5
                self.logger.info("confidence 필드가 없어 기본값 0.5로 설정")
            else:
                confidence = insights["confidence"]
                
                # confidence 타입 검증
                if not isinstance(confidence, (int, float)):
                    try:
                        confidence = float(confidence)
                        insights["confidence"] = confidence
                    except (ValueError, TypeError):
                        return {
                            "error": f"confidence 값은 숫자여야 합니다. 받은 값: {confidence} (타입: {type(confidence).__name__})",
                            "valid_range": "0.0 ~ 1.0"
                        }
                
                # confidence 범위 검증
                if not (0.0 <= confidence <= 1.0):
                    return {
                        "error": f"confidence 값은 0.0과 1.0 사이여야 합니다. 받은 값: {confidence}",
                        "valid_range": "0.0 (낮은 신뢰도) ~ 1.0 (높은 신뢰도)",
                        "hint": "0.0: 매우 불확실, 0.5: 보통, 1.0: 매우 확실"
                    }
            
            # 5. 추가 정보 필드 검증 (선택적)
            if "additional_info" in insights:
                if isinstance(insights["additional_info"], str) and len(insights["additional_info"].strip()) == 0:
                    insights["additional_info"] = "추가 정보 없음"
            else:
                insights["additional_info"] = "추가 정보 없음"
            
            # 6. 타임스탬프 추가
            from datetime import datetime
            insights["analysis_timestamp"] = datetime.now().isoformat()
            
            # 7. 인사이트 저장
            saved_insight = doc.add_insight(
                run_id=run_id,
                insight=insights,
                test_name=test_name
            )
            
            success = save_scenario(doc)
            if success:
                insights_count = len(doc.test_insights)
                self.logger.info(f"인사이트 저장 완료: sid={sid}, run_id={run_id}, 총 인사이트 수={insights_count}")
                
                # 8. 저장된 인사이트 품질 평가
                quality_score = self._evaluate_insight_quality(insights)
                
                return {
                    "success": True,
                    "message": f"시나리오 {sid}에 인사이트가 저장되었습니다.",
                    "insights_count": insights_count,
                    "saved_insight": saved_insight,
                    "insight_quality_score": quality_score,
                    "validation_summary": {
                        "all_required_fields_present": True,
                        "confidence_valid": True,
                        "content_quality": "validated"
                    }
                }
            else:
                return {"error": "인사이트 저장에 실패했습니다."}
                
        except Exception as e:
            error_msg = f"테스트 결과 분석 중 오류: {str(e)}"
            self.logger.error(error_msg)
            return {"error": error_msg}
    
    def _evaluate_insight_quality(self, insights: Dict[str, Any]) -> Dict[str, Any]:
        """
        저장된 인사이트의 품질을 평가합니다.
        
        Args:
            insights: 인사이트 딕셔너리
            
        Returns:
            Dict[str, Any]: 품질 평가 결과
        """
        try:
            quality_score = 0.0
            max_score = 5.0
            
            # 1. 내용 길이 평가 (1점)
            total_length = sum(len(str(insights.get(field, ""))) for field in 
                             ["precondition", "state_changes", "patterns", "security_implications"])
            if total_length > 200:
                quality_score += 1.0
            elif total_length > 100:
                quality_score += 0.5
            
            # 2. 구체성 평가 (1점) - 숫자, 주소, 구체적 용어 포함
            content = " ".join(str(insights.get(field, "")) for field in insights.keys())
            specificity_indicators = ["0x", "wei", "gas", "block", "transaction", "address", "uint", "bytes"]
            specificity_count = sum(1 for indicator in specificity_indicators if indicator.lower() in content.lower())
            if specificity_count >= 3:
                quality_score += 1.0
            elif specificity_count >= 1:
                quality_score += 0.5
            
            # 3. 보안 관련성 평가 (1점)
            security_keywords = ["vulnerability", "attack", "exploit", "risk", "security", "malicious", "unauthorized"]
            security_count = sum(1 for keyword in security_keywords if keyword.lower() in content.lower())
            if security_count >= 2:
                quality_score += 1.0
            elif security_count >= 1:
                quality_score += 0.5
            
            # 4. 신뢰도 적정성 평가 (1점)
            confidence = insights.get("confidence", 0.5)
            if 0.3 <= confidence <= 0.9:  # 적정 범위
                quality_score += 1.0
            elif confidence == 0.0 or confidence == 1.0:  # 극값은 0.5점
                quality_score += 0.5
            
            # 5. 패턴 분석 깊이 평가 (1점)
            patterns_text = str(insights.get("patterns", ""))
            if "because" in patterns_text.lower() or "due to" in patterns_text.lower() or "결과" in patterns_text:
                quality_score += 1.0  # 인과관계 분석 포함
            elif len(patterns_text) > 50:
                quality_score += 0.5  # 충분한 길이
            
            normalized_score = quality_score / max_score
            
            return {
                "score": round(normalized_score, 2),
                "grade": self._get_quality_grade(normalized_score),
                "strengths": self._identify_insight_strengths(insights, quality_score),
                "improvement_suggestions": self._suggest_insight_improvements(insights, quality_score)
            }
        except Exception as e:
            self.logger.warning(f"인사이트 품질 평가 중 오류: {str(e)}")
            return {"score": 0.5, "grade": "평가 불가", "error": str(e)}
    
    def _get_quality_grade(self, score: float) -> str:
        """품질 점수를 등급으로 변환"""
        if score >= 0.9:
            return "A (매우 우수)"
        elif score >= 0.7:
            return "B (우수)"
        elif score >= 0.5:
            return "C (보통)"
        elif score >= 0.3:
            return "D (미흡)"
        else:
            return "F (부족)"
    
    def _identify_insight_strengths(self, insights: Dict[str, Any], quality_score: float) -> List[str]:
        """인사이트의 강점 식별"""
        strengths = []
        
        if quality_score >= 4.0:
            strengths.append("상세하고 구체적인 분석")
        if insights.get("confidence", 0) > 0.7:
            strengths.append("높은 신뢰도")
        if len(str(insights.get("security_implications", ""))) > 50:
            strengths.append("충분한 보안 영향 분석")
        if "0x" in str(insights) or "gas" in str(insights).lower():
            strengths.append("기술적 세부사항 포함")
        
        return strengths if strengths else ["기본 요구사항 충족"]
    
    def _suggest_insight_improvements(self, insights: Dict[str, Any], quality_score: float) -> List[str]:
        """인사이트 개선 제안"""
        suggestions = []
        
        if quality_score < 2.0:
            suggestions.append("더 상세하고 구체적인 분석 필요")
        if len(str(insights.get("security_implications", ""))) < 30:
            suggestions.append("보안 영향에 대한 더 깊이 있는 분석 필요")
        if insights.get("confidence", 0.5) == 0.5:
            suggestions.append("분석 결과에 대한 신뢰도 평가 개선 필요")
        if "0x" not in str(insights) and "gas" not in str(insights).lower():
            suggestions.append("기술적 세부사항(주소, 가스, 블록 정보 등) 추가 필요")
        
        return suggestions if suggestions else ["현재 품질 수준 유지"]
    
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