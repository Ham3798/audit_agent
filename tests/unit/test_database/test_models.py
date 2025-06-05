"""
Unit tests for database models

ScenarioDoc 클래스의 기능을 테스트합니다.
"""

import pytest
import json
import datetime
from unittest.mock import patch

from database.models import ScenarioDoc


class TestScenarioDoc:
    """ScenarioDoc 클래스 테스트"""
    
    def test_initialization(self):
        """기본 초기화 테스트"""
        doc = ScenarioDoc()
        
        assert doc.meta == {}
        assert doc.spec == {}
        assert doc.code == {}
        assert doc.unit_tests == []
        assert doc.hints == {}
        assert doc.patches == []
        assert doc.runlog == []
        assert doc.extras == {}
        assert doc.test_insights == []
        assert doc.test_code_snapshots == {}
    
    def test_id_property(self):
        """ID 프로퍼티 테스트"""
        doc = ScenarioDoc()
        
        # ID가 없는 경우
        assert doc.id == ""
        
        # ID가 있는 경우
        doc.meta = {"id": "TEST_001"}
        assert doc.id == "TEST_001"
    
    def test_to_json(self):
        """JSON 변환 테스트"""
        doc = ScenarioDoc()
        doc.meta = {"id": "TEST_001", "title": "테스트 시나리오"}
        doc.spec = {"description": "테스트 설명"}
        
        json_str = doc.to_json()
        parsed = json.loads(json_str)
        
        assert parsed["meta"]["id"] == "TEST_001"
        assert parsed["meta"]["title"] == "테스트 시나리오"
        assert parsed["spec"]["description"] == "테스트 설명"
    
    def test_from_json(self):
        """JSON에서 객체 생성 테스트"""
        json_data = {
            "meta": {"id": "TEST_001", "title": "테스트"},
            "spec": {"description": "테스트 설명"},
            "code": {"target_contract": "TestContract"},
            "unit_tests": [{"test_name": "test1", "description": "테스트1"}],
            "unknown_field": "이 필드는 extras에 들어가야 함"
        }
        
        doc = ScenarioDoc.from_json(json.dumps(json_data))
        
        assert doc.meta["id"] == "TEST_001"
        assert doc.spec["description"] == "테스트 설명" 
        assert doc.code["target_contract"] == "TestContract"
        assert len(doc.unit_tests) == 1
        assert doc.unit_tests[0]["test_name"] == "test1"
        assert doc.extras["unknown_field"] == "이 필드는 extras에 들어가야 함"
    
    def test_add_run_log(self):
        """실행 로그 추가 테스트"""
        doc = ScenarioDoc()
        
        run_id = doc.add_run_log(
            run_id="run_123",
            status="SUCCESS",
            diff="+ new code",
            stdout="Test passed",
            stderr="",
            test_name="test_basic"
        )
        
        assert run_id == "run_123"
        assert len(doc.runlog) == 1
        
        log_entry = doc.runlog[0]
        assert log_entry["run_id"] == "run_123"
        assert log_entry["status"] == "SUCCESS"
        assert log_entry["diff"] == "+ new code"
        assert log_entry["stdout"] == "Test passed"
        assert log_entry["test_name"] == "test_basic"
        assert "ts" in log_entry
    
    def test_add_patch(self):
        """패치 추가 테스트"""
        doc = ScenarioDoc()
        
        patch_entry = doc.add_patch(
            author="developer",
            reason="버그 수정",
            diff_text="- old line\n+ new line"
        )
        
        assert len(doc.patches) == 1
        assert patch_entry["author"] == "developer"
        assert patch_entry["reason"] == "버그 수정"
        assert patch_entry["diff"] == "- old line\n+ new line"
        assert "ts" in patch_entry
    
    def test_add_test_insight(self):
        """테스트 인사이트 추가 테스트"""
        doc = ScenarioDoc()
        
        insight = {
            "precondition": "테스트 전제조건",
            "state_changes": "상태 변화",
            "patterns": "발견된 패턴",
            "security_implications": "보안 영향",
            "confidence": 0.8
        }
        
        result = doc.add_test_insight("run_123", insight, "test_basic")
        
        assert len(doc.test_insights) == 1
        saved_insight = doc.test_insights[0]
        assert saved_insight["run_id"] == "run_123"
        assert saved_insight["test_name"] == "test_basic"
        assert saved_insight["precondition"] == "테스트 전제조건"
        assert saved_insight["confidence"] == 0.8
        assert "ts" in saved_insight
    
    def test_add_test_insight_string_input(self):
        """문자열 인사이트 처리 테스트"""
        doc = ScenarioDoc()
        
        # 유효한 JSON 문자열
        json_insight = '{"precondition": "조건", "confidence": 0.9}'
        result = doc.add_test_insight("run_123", json_insight, "test1")
        
        assert len(doc.test_insights) == 1
        assert doc.test_insights[0]["precondition"] == "조건"
        assert doc.test_insights[0]["confidence"] == 0.9
        
        # 잘못된 JSON 문자열
        invalid_insight = "잘못된 JSON"
        doc.add_test_insight("run_124", invalid_insight, "test2")
        
        assert len(doc.test_insights) == 2
        assert doc.test_insights[1]["precondition"] == "정보 없음"
        assert doc.test_insights[1]["confidence"] == 0.5
    
    def test_get_cumulative_insights(self):
        """누적 인사이트 조회 테스트"""
        doc = ScenarioDoc()
        
        # 여러 인사이트 추가
        doc.add_test_insight("run_1", {"precondition": "조건1", "confidence": 0.8}, "test1")
        doc.add_test_insight("run_2", {"precondition": "조건2", "confidence": 0.9}, "test2")
        
        insights = doc.get_cumulative_insights()
        
        assert len(insights) == 2
        # 최신순으로 정렬되어야 함
        assert insights[0]["run_id"] == "run_2"  
        assert insights[1]["run_id"] == "run_1"
    
    def test_add_unit_test(self):
        """유닛테스트 추가 테스트"""
        doc = ScenarioDoc()
        
        test = doc.add_unit_test(
            test_name="test_basic_attack",
            description="기본 공격 테스트",
            test_code="function test_basic_attack() public { ... }",
            expected_behavior="공격 성공",
            tags=["attack", "basic"]
        )
        
        assert len(doc.unit_tests) == 1
        assert test["test_name"] == "test_basic_attack"
        assert test["description"] == "기본 공격 테스트"
        assert test["tags"] == ["attack", "basic"]
    
    def test_add_unit_test_duplicate(self):
        """중복 유닛테스트 처리 테스트"""
        doc = ScenarioDoc()
        
        # 첫 번째 테스트 추가
        doc.add_unit_test("test1", "설명1", "코드1")
        
        # 같은 이름으로 두 번째 테스트 추가 (업데이트되어야 함)
        doc.add_unit_test("test1", "설명2", "코드2")
        
        assert len(doc.unit_tests) == 1
        assert doc.unit_tests[0]["description"] == "설명2"
        assert doc.unit_tests[0]["test_code"] == "코드2"
    
    def test_add_unit_test_reference(self):
        """유닛테스트 참조 추가 테스트"""
        doc = ScenarioDoc()
        
        test = doc.add_unit_test_reference(
            test_name="test_existing",
            description="기존 테스트 참조",
            test_file_path="test/ExistingTest.t.sol",
            expected_behavior="성공",
            tags=["existing"]
        )
        
        assert len(doc.unit_tests) == 1
        assert test["test_file_path"] == "test/ExistingTest.t.sol"
        assert "test_code" not in test  # 참조 방식이므로 코드는 없어야 함
    
    def test_get_unit_test(self):
        """유닛테스트 조회 테스트"""
        doc = ScenarioDoc()
        doc.add_unit_test("test1", "설명", "코드")
        
        test = doc.get_unit_test("test1")
        assert test is not None
        assert test["test_name"] == "test1"
        
        test = doc.get_unit_test("nonexistent")
        assert test is None
    
    def test_remove_unit_test(self):
        """유닛테스트 제거 테스트"""
        doc = ScenarioDoc()
        doc.add_unit_test("test1", "설명", "코드")
        
        assert len(doc.unit_tests) == 1
        
        result = doc.remove_unit_test("test1")
        assert result is True
        assert len(doc.unit_tests) == 0
        
        result = doc.remove_unit_test("nonexistent")
        assert result is False
    
    def test_get_test_summary(self):
        """테스트 요약 정보 테스트"""
        doc = ScenarioDoc()
        
        # 테스트와 로그 추가
        doc.add_unit_test("test1", "설명1", "코드1")
        doc.add_unit_test("test2", "설명2", "코드2")
        
        doc.add_run_log("run1", "SUCCESS", "", "", "", "test1")
        doc.add_run_log("run2", "FAILURE", "", "", "", "test1")
        doc.add_run_log("run3", "SUCCESS", "", "", "", "test2")
        
        doc.add_test_insight("run1", {"precondition": "조건"}, "test1")
        
        summary = doc.get_test_summary()
        
        assert summary["total_tests"] == 2
        assert summary["total_runs"] == 3
        assert summary["successful_runs"] == 2
        assert summary["success_rate"] == 2/3
        assert summary["total_insights"] == 1
        
        # 테스트별 통계 확인
        test1_stats = summary["test_stats"]["test1"]
        assert test1_stats["total_runs"] == 2
        assert test1_stats["successful_runs"] == 1
        assert test1_stats["insights_count"] == 1 