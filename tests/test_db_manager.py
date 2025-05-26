"""
db_manager.py 테스트 모듈

ScenarioDoc 클래스와 데이터베이스 관련 기능들을 테스트합니다.
- ScenarioDoc 클래스의 모든 메서드
- 유닛테스트 관리 기능
- 데이터베이스 CRUD 작업
- 실행 로그 및 인사이트 관리
"""

import pytest
import os
import tempfile
import json
import datetime
from unittest.mock import patch, MagicMock

# 테스트용 임시 DB 설정
import sys
sys.path.append('..')
from db_manager import (
    ScenarioDoc, save_scenario, load_scenario, update_scenario_partial,
    delete_scenario, list_ids, add_runlog_entry, init_db
)


class TestScenarioDoc:
    """ScenarioDoc 클래스 테스트"""
    
    def setup_method(self):
        """각 테스트 전 실행되는 설정"""
        self.sample_scenario = {
            "meta": {
                "id": "TEST_001",
                "title": "테스트 시나리오",
                "category": "Test",
                "severity": "medium",
                "tags": ["test", "unit"],
                "author": "tester",
                "created": "2025-01-23T10:00:00Z"
            },
            "spec": {
                "description": "테스트용 시나리오입니다",
                "actors": [{"id": "user", "role": "EOA", "trust_level": "untrusted"}],
                "assets": [{"name": "TestAsset", "type": "address"}],
                "components": [{"name": "TestContract", "type": "contract"}],
                "trust_boundaries": [],
                "data_flows": [],
                "behaviors": [],
                "precondition": "테스트 전제조건",
                "action": "테스트 액션",
                "expected": "예상 결과"
            },
            "code": {
                "poc_contract": "contract TestPoC {}",
                "target_contract_name": "TestContract",
                "deployment_script": ""
            },
            "unit_tests": [
                {
                    "test_name": "test_basic_functionality",
                    "description": "기본 기능 테스트",
                    "test_code": "function test_basic_functionality() public {}",
                    "expected_behavior": "성공적으로 실행",
                    "tags": ["basic"]
                }
            ],
            "hints": {},
            "patches": [],
            "runlog": [],
            "extras": {},
            "test_insights": [],
            "test_code_snapshots": {}
        }
    
    def test_scenario_doc_creation(self):
        """ScenarioDoc 생성 테스트"""
        doc = ScenarioDoc.from_json(json.dumps(self.sample_scenario))
        
        assert doc.id == "TEST_001"
        assert doc.meta["title"] == "테스트 시나리오"
        assert len(doc.unit_tests) == 1
        assert doc.unit_tests[0]["test_name"] == "test_basic_functionality"
    
    def test_scenario_doc_to_json(self):
        """ScenarioDoc JSON 변환 테스트"""
        doc = ScenarioDoc.from_json(json.dumps(self.sample_scenario))
        json_str = doc.to_json()
        
        # JSON 파싱이 성공하는지 확인
        parsed = json.loads(json_str)
        assert parsed["meta"]["id"] == "TEST_001"
    
    def test_add_run_log(self):
        """실행 로그 추가 테스트"""
        doc = ScenarioDoc.from_json(json.dumps(self.sample_scenario))
        
        run_id = doc.add_run_log(
            run_id="run_001",
            status="SUCCESS",
            diff="test diff",
            stdout="test output",
            stderr="",
            test_name="test_basic_functionality"
        )
        
        assert run_id == "run_001"
        assert len(doc.runlog) == 1
        assert doc.runlog[0]["run_id"] == "run_001"
        assert doc.runlog[0]["test_name"] == "test_basic_functionality"
        assert doc.runlog[0]["status"] == "SUCCESS"
    
    def test_add_patch(self):
        """패치 추가 테스트"""
        doc = ScenarioDoc.from_json(json.dumps(self.sample_scenario))
        
        patch_entry = doc.add_patch(
            author="tester",
            reason="테스트 수정",
            diff_text="+ new line\n- old line"
        )
        
        assert len(doc.patches) == 1
        assert doc.patches[0]["author"] == "tester"
        assert doc.patches[0]["reason"] == "테스트 수정"
        assert "ts" in doc.patches[0]
    
    def test_add_test_insight(self):
        """테스트 인사이트 추가 테스트"""
        doc = ScenarioDoc.from_json(json.dumps(self.sample_scenario))
        
        insight = {
            "precondition": "테스트 전제조건",
            "state_changes": "상태 변화 없음",
            "patterns": "정상 패턴",
            "security_implications": "보안 영향 없음",
            "additional_info": "추가 정보",
            "confidence": 0.9
        }
        
        result = doc.add_test_insight("run_001", insight, "test_basic_functionality")
        
        assert len(doc.test_insights) == 1
        assert doc.test_insights[0]["run_id"] == "run_001"
        assert doc.test_insights[0]["test_name"] == "test_basic_functionality"
        assert doc.test_insights[0]["confidence"] == 0.9
    
    def test_add_test_insight_string_input(self):
        """문자열 형태 인사이트 추가 테스트"""
        doc = ScenarioDoc.from_json(json.dumps(self.sample_scenario))
        
        insight_str = json.dumps({
            "precondition": "문자열 테스트",
            "state_changes": "변화 없음",
            "patterns": "패턴",
            "security_implications": "영향 없음",
            "additional_info": "정보",
            "confidence": 0.8
        })
        
        result = doc.add_test_insight("run_002", insight_str, "test_string")
        
        assert len(doc.test_insights) == 1
        assert doc.test_insights[0]["precondition"] == "문자열 테스트"
    
    def test_get_cumulative_insights(self):
        """누적 인사이트 조회 테스트"""
        doc = ScenarioDoc.from_json(json.dumps(self.sample_scenario))
        
        # 여러 인사이트 추가
        for i in range(3):
            insight = {
                "precondition": f"조건 {i}",
                "state_changes": f"변화 {i}",
                "patterns": f"패턴 {i}",
                "security_implications": f"영향 {i}",
                "additional_info": f"정보 {i}",
                "confidence": 0.5 + i * 0.1
            }
            doc.add_test_insight(f"run_{i}", insight, f"test_{i}")
        
        insights = doc.get_cumulative_insights()
        
        assert len(insights) == 3
        # 최신순 정렬 확인 (타임스탬프 기준)
        assert insights[0]["precondition"] == "조건 2"
    
    def test_add_unit_test(self):
        """유닛테스트 추가 테스트"""
        doc = ScenarioDoc.from_json(json.dumps(self.sample_scenario))
        
        new_test = doc.add_unit_test(
            test_name="test_new_feature",
            description="새로운 기능 테스트",
            test_code="function test_new_feature() public { assert(true); }",
            expected_behavior="성공",
            tags=["new", "feature"]
        )
        
        assert len(doc.unit_tests) == 2
        assert new_test["test_name"] == "test_new_feature"
        assert new_test["tags"] == ["new", "feature"]
    
    def test_add_unit_test_duplicate_name(self):
        """중복 테스트 이름 처리 테스트"""
        doc = ScenarioDoc.from_json(json.dumps(self.sample_scenario))
        
        # 기존과 같은 이름으로 테스트 추가
        updated_test = doc.add_unit_test(
            test_name="test_basic_functionality",
            description="업데이트된 설명",
            test_code="function test_basic_functionality() public { revert(); }",
            expected_behavior="실패",
            tags=["updated"]
        )
        
        # 테스트 개수는 그대로, 내용만 업데이트
        assert len(doc.unit_tests) == 1
        assert doc.unit_tests[0]["description"] == "업데이트된 설명"
        assert doc.unit_tests[0]["tags"] == ["updated"]
    
    def test_get_unit_test(self):
        """특정 유닛테스트 조회 테스트"""
        doc = ScenarioDoc.from_json(json.dumps(self.sample_scenario))
        
        test = doc.get_unit_test("test_basic_functionality")
        assert test is not None
        assert test["test_name"] == "test_basic_functionality"
        
        # 존재하지 않는 테스트
        non_existent = doc.get_unit_test("non_existent_test")
        assert non_existent is None
    
    def test_remove_unit_test(self):
        """유닛테스트 제거 테스트"""
        doc = ScenarioDoc.from_json(json.dumps(self.sample_scenario))
        
        # 테스트 추가
        doc.add_unit_test("test_to_remove", "제거될 테스트", "code", "behavior")
        assert len(doc.unit_tests) == 2
        
        # 테스트 제거
        result = doc.remove_unit_test("test_to_remove")
        assert result is True
        assert len(doc.unit_tests) == 1
        
        # 존재하지 않는 테스트 제거 시도
        result = doc.remove_unit_test("non_existent")
        assert result is False
    
    def test_get_runlog_by_test(self):
        """테스트별 실행 로그 조회 테스트"""
        doc = ScenarioDoc.from_json(json.dumps(self.sample_scenario))
        
        # 여러 테스트의 로그 추가
        doc.add_run_log("run_1", "SUCCESS", "diff1", test_name="test_a")
        doc.add_run_log("run_2", "FAILURE", "diff2", test_name="test_b")
        doc.add_run_log("run_3", "SUCCESS", "diff3", test_name="test_a")
        
        # test_a의 로그만 조회
        test_a_logs = doc.get_runlog_by_test("test_a")
        assert len(test_a_logs) == 2
        assert all(log["test_name"] == "test_a" for log in test_a_logs)
    
    def test_get_insights_by_test(self):
        """테스트별 인사이트 조회 테스트"""
        doc = ScenarioDoc.from_json(json.dumps(self.sample_scenario))
        
        # 여러 테스트의 인사이트 추가 (각각 독립적인 객체로 생성)
        insight1 = {"precondition": "조건1", "state_changes": "", "patterns": "",
                   "security_implications": "", "additional_info": "", "confidence": 0.8}
        insight2 = {"precondition": "조건2", "state_changes": "", "patterns": "",
                   "security_implications": "", "additional_info": "", "confidence": 0.9}
        insight3 = {"precondition": "조건3", "state_changes": "", "patterns": "",
                   "security_implications": "", "additional_info": "", "confidence": 0.7}
        
        doc.add_test_insight("run_1", insight1, "test_a")
        doc.add_test_insight("run_2", insight2, "test_b")
        doc.add_test_insight("run_3", insight3, "test_a")  # test_a에 대한 두 번째 인사이트
        
        # test_a의 인사이트만 조회
        test_a_insights = doc.get_insights_by_test("test_a")
        assert len(test_a_insights) == 2  # run_1과 run_3
        
        # test_b의 인사이트만 조회
        test_b_insights = doc.get_insights_by_test("test_b")
        assert len(test_b_insights) == 1  # run_2만
        
        # 존재하지 않는 테스트
        test_c_insights = doc.get_insights_by_test("test_c")
        assert len(test_c_insights) == 0
    
    def test_get_test_summary(self):
        """테스트 현황 요약 테스트"""
        doc = ScenarioDoc.from_json(json.dumps(self.sample_scenario))
        
        # 테스트 및 로그 추가
        doc.add_unit_test("test_second", "두 번째 테스트", "code", "behavior")
        doc.add_run_log("run_1", "SUCCESS", "diff1", test_name="test_basic_functionality")
        doc.add_run_log("run_2", "FAILURE", "diff2", test_name="test_second")
        
        summary = doc.get_test_summary()
        
        assert summary["total_tests"] == 2
        assert summary["total_runs"] == 2
        assert summary["successful_runs"] == 1
        assert summary["success_rate"] == 0.5
        assert "test_stats" in summary
        assert "test_basic_functionality" in summary["test_stats"]


class TestDatabaseOperations:
    """데이터베이스 CRUD 작업 테스트"""
    
    def setup_method(self):
        """각 테스트 전 실행되는 설정"""
        # 임시 DB 파일 생성
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        
        # 환경 변수 설정
        os.environ['SCENARIO_DB'] = self.temp_db.name
        
        # DB 초기화
        init_db()
        
        self.sample_doc = ScenarioDoc(
            meta={"id": "DB_TEST_001", "title": "DB 테스트"},
            spec={"description": "DB 테스트용"},
            code={"poc_contract": "contract Test {}"},
            unit_tests=[],
            hints={},
            patches=[],
            runlog=[],
            extras={},
            test_insights=[],
            test_code_snapshots={}
        )
    
    def teardown_method(self):
        """각 테스트 후 실행되는 정리"""
        # 임시 DB 파일 삭제
        if os.path.exists(self.temp_db.name):
            os.unlink(self.temp_db.name)
    
    def test_save_and_load_scenario(self):
        """시나리오 저장 및 로드 테스트"""
        # 저장
        result = save_scenario(self.sample_doc)
        assert result is True
        
        # 로드
        loaded_doc = load_scenario("DB_TEST_001")
        assert loaded_doc is not None
        assert loaded_doc.id == "DB_TEST_001"
        assert loaded_doc.meta["title"] == "DB 테스트"
    
    def test_load_nonexistent_scenario(self):
        """존재하지 않는 시나리오 로드 테스트"""
        result = load_scenario("NONEXISTENT")
        assert result is None
    
    def test_update_scenario_partial(self):
        """시나리오 부분 업데이트 테스트"""
        # 먼저 저장
        save_scenario(self.sample_doc)
        
        # 부분 업데이트
        update_dict = {
            "hints": {"runtime": {"last_run": "test"}},
            "extras": {"new_field": "new_value"}
        }
        
        result = update_scenario_partial("DB_TEST_001", update_dict)
        assert result is True
        
        # 업데이트 확인
        updated_doc = load_scenario("DB_TEST_001")
        assert updated_doc.hints["runtime"]["last_run"] == "test"
        assert updated_doc.extras["new_field"] == "new_value"
    
    def test_update_nonexistent_scenario(self):
        """존재하지 않는 시나리오 업데이트 테스트"""
        with pytest.raises(ValueError):
            update_scenario_partial("NONEXISTENT", {"hints": {}})
    
    def test_delete_scenario(self):
        """시나리오 삭제 테스트"""
        # 먼저 저장
        save_scenario(self.sample_doc)
        
        # 삭제
        result = delete_scenario("DB_TEST_001")
        assert result is True
        
        # 삭제 확인
        loaded_doc = load_scenario("DB_TEST_001")
        assert loaded_doc is None
    
    def test_list_ids(self):
        """시나리오 ID 목록 조회 테스트"""
        # 여러 시나리오 저장
        for i in range(3):
            doc = ScenarioDoc(
                meta={"id": f"LIST_TEST_{i}", "title": f"테스트 {i}"},
                spec={"description": "테스트"},
                code={}, unit_tests=[], hints={}, patches=[], 
                runlog=[], extras={}, test_insights=[], test_code_snapshots={}
            )
            save_scenario(doc)
        
        # ID 목록 조회
        ids = list_ids()
        assert len(ids) == 3
        assert "LIST_TEST_0" in ids
        assert "LIST_TEST_1" in ids
        assert "LIST_TEST_2" in ids
    
    def test_add_runlog_entry(self):
        """실행 로그 엔트리 추가 테스트"""
        # 먼저 시나리오 저장
        save_scenario(self.sample_doc)
        
        # 실행 로그 추가
        run_id = add_runlog_entry(
            sid="DB_TEST_001",
            status="SUCCESS",
            diff="test diff",
            stdout="test output",
            stderr="",
            test_name="test_function"
        )
        
        assert run_id is not None
        
        # 시나리오에서 로그 확인
        updated_doc = load_scenario("DB_TEST_001")
        assert len(updated_doc.runlog) == 1
        assert updated_doc.runlog[0]["run_id"] == run_id
        assert updated_doc.runlog[0]["test_name"] == "test_function"


class TestErrorHandling:
    """에러 처리 테스트"""
    
    def test_scenario_doc_invalid_json(self):
        """잘못된 JSON으로 ScenarioDoc 생성 테스트"""
        with pytest.raises(json.JSONDecodeError):
            ScenarioDoc.from_json("invalid json")
    
    def test_scenario_doc_missing_id(self):
        """ID가 없는 시나리오 저장 테스트"""
        doc = ScenarioDoc(
            meta={},  # id 없음
            spec={}, code={}, unit_tests=[], hints={}, patches=[],
            runlog=[], extras={}, test_insights=[], test_code_snapshots={}
        )
        
        with pytest.raises(ValueError):
            save_scenario(doc)
    
    def test_add_test_insight_invalid_json(self):
        """잘못된 JSON 인사이트 추가 테스트"""
        doc = ScenarioDoc(
            meta={"id": "ERROR_TEST"},
            spec={}, code={}, unit_tests=[], hints={}, patches=[],
            runlog=[], extras={}, test_insights=[], test_code_snapshots={}
        )
        
        # 잘못된 JSON 문자열
        result = doc.add_test_insight("run_001", "invalid json string", "test")
        
        # 기본값으로 처리되어야 함
        assert len(doc.test_insights) == 1
        assert doc.test_insights[0]["precondition"] == "정보 없음"


if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 