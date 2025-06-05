"""
Database models for audit_agent project

이 모듈은 audit_agent에서 사용되는 데이터 모델들을 정의합니다.
주요 모델인 ScenarioDoc 클래스가 포함되어 있습니다.
"""

import json
import datetime
from dataclasses import dataclass, asdict, field, fields
from typing import Any, Dict, List, Optional

from config.logging_config import get_logger

logger = get_logger("database")


@dataclass 
class ScenarioDoc:
    """
    시나리오 전체 데이터를 관리하는 메인 모델 클래스
    
    YAML 스키마를 JSON으로 파싱한 후 보관하며, 최소 PK(id)만 강제합니다.
    1 시나리오 = 1 PoC + n개 유닛테스트 구조를 지원합니다.
    
    Attributes:
        meta: 시나리오 메타데이터 (ID, 제목, 카테고리, 심각도 등)
        spec: 위협 모델링 기반 시나리오 스펙 (actors, assets, behaviors 등)
        code: PoC 컨트랙트 코드 및 대상 컨트랙트 정보
        unit_tests: n개의 유닛테스트 정의
        hints: 컴파일러/런타임 힌트
        patches: 코드 변경 이력
        runlog: 테스트 실행 로그
        extras: 미래 확장을 위한 추가 섹션
        test_insights: LLM이 추출한 테스트 분석 인사이트
        test_code_snapshots: 테스트 코드 스냅샷 (기존 호환성)
    """
    
    meta: Dict[str, Any] = field(default_factory=dict)
    spec: Dict[str, Any] = field(default_factory=dict)
    code: Dict[str, Any] = field(default_factory=dict)
    unit_tests: List[Dict[str, Any]] = field(default_factory=list)
    hints: Dict[str, Any] = field(default_factory=dict)
    patches: List[Dict[str, Any]] = field(default_factory=list)
    runlog: List[Dict[str, Any]] = field(default_factory=list)
    extras: Dict[str, Any] = field(default_factory=dict)
    test_insights: List[Dict[str, Any]] = field(default_factory=list)
    test_code_snapshots: Dict[str, str] = field(default_factory=dict)

    @property
    def id(self) -> str:
        """시나리오 ID 반환"""
        return self.meta.get("id", "")

    def to_json(self) -> str:
        """ScenarioDoc을 JSON 문자열로 변환"""
        return json.dumps(asdict(self), ensure_ascii=False, indent=2)

    @staticmethod
    def from_json(js: str) -> "ScenarioDoc":
        """
        JSON 문자열에서 ScenarioDoc 생성
        
        스키마에 정의되지 않은 추가 필드들은 extras에 저장됩니다.
        """
        data = json.loads(js)
        field_names = {f.name for f in fields(ScenarioDoc)}
        
        # 기본값 설정 및 extras 처리
        processed_data = {}
        current_extras = data.get("extras", {})

        for fname_in_class in field_names:
            if fname_in_class == "extras":
                continue
            if fname_in_class in data:
                processed_data[fname_in_class] = data[fname_in_class]
            else:
                # 리스트 타입 필드들은 빈 리스트로 초기화
                if fname_in_class in ["patches", "runlog", "test_insights", "unit_tests"]:
                    processed_data[fname_in_class] = []
                else:
                    processed_data[fname_in_class] = {}

        # 스키마에 정의되지 않은 최상위 키들을 extras에 추가
        for key_in_data, value_in_data in data.items():
            if key_in_data not in field_names:
                current_extras[key_in_data] = value_in_data
        
        processed_data["extras"] = current_extras
        
        return ScenarioDoc(**processed_data)

    def add_run_log(self, run_id: str, status: str, diff: str, stdout: str = "", stderr: str = "", test_name: str = ""):
        """
        시나리오에 실행 로그 추가
        
        Args:
            run_id: 실행 ID
            status: 실행 상태 (SUCCESS, FAILURE 등)
            diff: 코드 변경 diff
            stdout: 표준 출력
            stderr: 표준 에러
            test_name: 실행된 테스트 이름
        """
        from config.settings import settings
        
        log_entry = {
            "run_id": run_id,
            "ts": datetime.datetime.utcnow().isoformat(),
            "test_name": test_name,
            "status": status,
            "diff": diff,
            "stdout": stdout[:settings.max_log_size] if stdout else "",
            "stderr": stderr[:settings.max_log_size] if stderr else ""
        }
        self.runlog.append(log_entry)
        logger.info(f"실행 로그 추가: {run_id} (테스트: {test_name}, 상태: {status})")
        return run_id

    def add_patch(self, author: str, reason: str, diff_text: str):
        """
        시나리오에 코드 변경 패치 추가
        
        Args:
            author: 변경 작성자
            reason: 변경 이유
            diff_text: 변경 내용 (diff 형식)
        """
        patch_entry = {
            "ts": datetime.datetime.utcnow().isoformat(),
            "author": author,
            "reason": reason,
            "diff": diff_text
        }
        self.patches.append(patch_entry)
        logger.info(f"패치 추가: {author} - {reason}")
        return patch_entry

    def add_test_insight(self, run_id: str, insight: Dict[str, Any], test_name: str = ""):
        """
        LLM이 순차적 사고 과정을 통해 테스트 실행 결과에서 추출한 인사이트를 저장
        
        Args:
            run_id: 테스트 실행 ID
            insight: 인사이트 정보 딕셔너리
            test_name: 분석된 테스트 이름
        """
        # insight가 문자열인 경우 딕셔너리로 변환
        if isinstance(insight, str):
            try:
                insight = json.loads(insight)
            except json.JSONDecodeError:
                logger.error(f"유효하지 않은 JSON 인사이트: {insight[:50]}...")
                insight = {
                    "precondition": "정보 없음",
                    "state_changes": "정보 없음", 
                    "patterns": "정보 없음",
                    "security_implications": "정보 없음",
                    "additional_info": f"원본 데이터: {insight[:100]}...",
                    "confidence": 0.5
                }
        
        # 메타데이터 추가
        insight["ts"] = datetime.datetime.utcnow().isoformat()
        insight["run_id"] = run_id
        insight["test_name"] = test_name
        
        # test_insights 초기화 확인
        if not hasattr(self, 'test_insights') or not isinstance(self.test_insights, list):
            logger.warning("test_insights 필드 초기화")
            self.test_insights = []
        
        # 동일 run_id 인사이트 업데이트 또는 추가
        updated = False
        for i, existing in enumerate(self.test_insights):
            if existing.get("run_id") == run_id:
                self.test_insights[i] = insight
                updated = True
                logger.info(f"인사이트 업데이트: {run_id}")
                break
        
        if not updated:
            self.test_insights.append(insight)
            logger.info(f"새 인사이트 추가: {run_id} (테스트: {test_name})")
        
        return insight

    def get_cumulative_insights(self) -> List[Dict[str, Any]]:
        """
        시나리오의 모든 인사이트를 시간순으로 반환
        
        Returns:
            시간순으로 정렬된 인사이트 리스트 (최신순)
        """
        if not hasattr(self, 'test_insights') or not isinstance(self.test_insights, list):
            logger.warning("test_insights 필드가 없거나 올바르지 않습니다.")
            return []
        
        processed_insights = []
        for insight in self.test_insights:
            if isinstance(insight, str):
                try:
                    parsed_insight = json.loads(insight)
                    processed_insights.append(parsed_insight)
                except json.JSONDecodeError:
                    logger.warning(f"잘못된 형식의 인사이트: {insight[:50]}...")
                    # 기본 구조로 변환
                    processed_insights.append({
                        "ts": datetime.datetime.utcnow().isoformat(),
                        "run_id": "unknown",
                        "test_name": "unknown",
                        "precondition": "정보 없음",
                        "state_changes": "정보 없음",
                        "patterns": "정보 없음", 
                        "security_implications": "정보 없음",
                        "additional_info": f"원본: {insight[:100]}...",
                        "confidence": 0.5
                    })
            else:
                processed_insights.append(insight)
        
        # 타임스탬프 기준 정렬 (최신순)
        def get_timestamp(item):
            if not isinstance(item, dict):
                return ""
            ts = item.get("ts", "")
            if isinstance(ts, (datetime.datetime, datetime.date)):
                return ts.isoformat()
            return ts
        
        return sorted(processed_insights, key=get_timestamp, reverse=True)

    # === 유닛테스트 관리 기능 ===
    
    def add_unit_test(self, test_name: str, description: str, test_code: str, expected_behavior: str = "", tags: List[str] = None):
        """
        시나리오에 새로운 유닛테스트 추가
        
        Args:
            test_name: 테스트 함수 이름 (고유해야 함)
            description: 테스트 설명
            test_code: 테스트 함수 코드 (Solidity)
            expected_behavior: 예상 동작
            tags: 테스트 태그 리스트
        """
        if tags is None:
            tags = []
        
        # 중복 테스트 이름 확인
        for existing_test in self.unit_tests:
            if existing_test.get("test_name") == test_name:
                logger.warning(f"테스트 이름 '{test_name}' 중복, 업데이트합니다.")
                existing_test.update({
                    "description": description,
                    "test_code": test_code,
                    "expected_behavior": expected_behavior,
                    "tags": tags
                })
                return existing_test
        
        # 새 테스트 추가
        new_test = {
            "test_name": test_name,
            "description": description,
            "test_code": test_code,
            "expected_behavior": expected_behavior,
            "tags": tags
        }
        self.unit_tests.append(new_test)
        logger.info(f"새 유닛테스트 추가: {test_name}")
        return new_test
    
    def add_unit_test_reference(self, test_name: str, description: str, test_file_path: str, expected_behavior: str = "", tags: List[str] = None):
        """
        시나리오에 기존 유닛테스트 파일 참조 추가
        
        Args:
            test_name: 테스트 함수 이름
            description: 테스트 설명
            test_file_path: 기존 테스트 파일 경로
            expected_behavior: 예상 동작
            tags: 테스트 태그 리스트
        """
        if tags is None:
            tags = []
        
        # 중복 테스트 이름 확인
        for existing_test in self.unit_tests:
            if existing_test.get("test_name") == test_name:
                logger.warning(f"테스트 이름 '{test_name}' 중복, 참조로 업데이트합니다.")
                # test_code 필드 제거 (참조 방식으로 변경)
                if "test_code" in existing_test:
                    del existing_test["test_code"]
                existing_test.update({
                    "description": description,
                    "test_file_path": test_file_path,
                    "expected_behavior": expected_behavior,
                    "tags": tags
                })
                return existing_test
        
        # 새 테스트 참조 추가
        new_test = {
            "test_name": test_name,
            "description": description,
            "test_file_path": test_file_path,
            "expected_behavior": expected_behavior,
            "tags": tags
        }
        self.unit_tests.append(new_test)
        logger.info(f"새 유닛테스트 참조 추가: {test_name} -> {test_file_path}")
        return new_test
    
    def get_unit_test(self, test_name: str) -> Optional[Dict[str, Any]]:
        """특정 이름의 유닛테스트 조회"""
        for test in self.unit_tests:
            if test.get("test_name") == test_name:
                return test
        return None
    
    def remove_unit_test(self, test_name: str) -> bool:
        """특정 이름의 유닛테스트 제거"""
        for i, test in enumerate(self.unit_tests):
            if test.get("test_name") == test_name:
                del self.unit_tests[i]
                logger.info(f"유닛테스트 제거: {test_name}")
                return True
        return False
    
    def get_runlog_by_test(self, test_name: str) -> List[Dict[str, Any]]:
        """특정 테스트의 모든 실행 로그 조회"""
        return [log for log in self.runlog if log.get("test_name") == test_name]
    
    def get_insights_by_test(self, test_name: str) -> List[Dict[str, Any]]:
        """특정 테스트의 모든 인사이트 조회"""
        return [insight for insight in self.test_insights if insight.get("test_name") == test_name]
    
    def get_test_summary(self) -> Dict[str, Any]:
        """시나리오의 테스트 현황 요약"""
        total_tests = len(self.unit_tests)
        total_runs = len(self.runlog)
        successful_runs = len([log for log in self.runlog if log.get("status") == "SUCCESS"])
        total_insights = len(self.test_insights)
        
        # 테스트별 통계
        test_stats = {}
        for test in self.unit_tests:
            test_name = test.get("test_name", "")
            test_runs = self.get_runlog_by_test(test_name)
            test_insights = self.get_insights_by_test(test_name)
            
            test_stats[test_name] = {
                "total_runs": len(test_runs),
                "successful_runs": len([log for log in test_runs if log.get("status") == "SUCCESS"]),
                "insights_count": len(test_insights),
                "last_run": test_runs[-1] if test_runs else None
            }
        
        return {
            "total_tests": total_tests,
            "total_runs": total_runs,
            "successful_runs": successful_runs,
            "success_rate": successful_runs / total_runs if total_runs > 0 else 0,
            "total_insights": total_insights,
            "test_stats": test_stats
        }

    def update_hints_from_run(self, run_id: str, status: str, stdout: str, stderr: str):
        """
        실행 결과를 바탕으로 hints 업데이트
        
        Args:
            run_id: 실행 ID
            status: 실행 상태
            stdout: 표준 출력
            stderr: 표준 에러
        """
        self.hints.setdefault("runtime", {})["last_run_id"] = run_id
        self.hints["runtime"]["last_run_status"] = status
        
        # 추후 validation 모듈로 이동 예정
        # schema_validator의 extract_hints 사용
        try:
            from validation.hint_extractor import extract_hints
            scenario_data = json.loads(self.to_json())
            updated_scenario = extract_hints(scenario_data, stdout, stderr)
            self.hints = updated_scenario.get("hints", self.hints)
        except ImportError:
            # 리팩토링 중에는 기존 방식 사용
            logger.warning("validation.hint_extractor 모듈을 찾을 수 없습니다. 기본 힌트 업데이트를 수행합니다.")
        
        return self.hints 