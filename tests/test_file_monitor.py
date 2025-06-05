"""
file_monitor.py 테스트 모듈

FileMonitor 클래스의 모든 기능을 테스트합니다.
- 파일 등록 및 모니터링
- 테스트별 파일 관리
- 변경 감지 기능
- 매핑 및 상태 관리
"""

import pytest
import os
import tempfile
import time
from unittest.mock import patch, MagicMock

import sys
sys.path.append('..')
from file_monitor import FileMonitor


class TestFileMonitor:
    """FileMonitor 클래스 테스트"""
    
    def setup_method(self):
        """각 테스트 전 실행되는 설정"""
        self.monitor = FileMonitor()
        
        # 임시 파일들 생성
        self.temp_files = []
        for i in range(3):
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=f'_test_{i}.sol')
            temp_file.write(f"// Test file {i}\ncontract Test{i} {{}}\n".encode())
            temp_file.close()
            self.temp_files.append(temp_file.name)
    
    def teardown_method(self):
        """각 테스트 후 실행되는 정리"""
        # 임시 파일들 삭제
        for temp_file in self.temp_files:
            if os.path.exists(temp_file):
                os.unlink(temp_file)
    
    def test_file_monitor_initialization(self):
        """FileMonitor 초기화 테스트"""
        assert len(self.monitor.active_sids) == 0
        assert len(self.monitor.file_timestamps) == 0
        assert len(self.monitor.sid_to_files) == 0
        assert len(self.monitor.sid_to_test_files) == 0
        assert len(self.monitor.file_to_test_mapping) == 0
    
    def test_register_file_basic(self):
        """기본 파일 등록 테스트"""
        sid = "TEST_001"
        file_path = self.temp_files[0]
        
        self.monitor.register_file(sid, file_path)
        
        # 시나리오가 활성 목록에 추가되었는지 확인
        assert sid in self.monitor.active_sids
        
        # 파일이 시나리오에 매핑되었는지 확인
        assert sid in self.monitor.sid_to_files
        assert file_path in self.monitor.sid_to_files[sid]
        
        # 타임스탬프가 기록되었는지 확인
        assert file_path in self.monitor.file_timestamps
    
    def test_register_file_with_test_name(self):
        """테스트 이름과 함께 파일 등록 테스트"""
        sid = "TEST_002"
        file_path = self.temp_files[0]
        test_name = "test_basic_functionality"
        
        self.monitor.register_file(sid, file_path, test_name)
        
        # 기본 등록 확인
        assert sid in self.monitor.active_sids
        assert file_path in self.monitor.sid_to_files[sid]
        
        # 테스트별 매핑 확인
        assert sid in self.monitor.sid_to_test_files
        assert test_name in self.monitor.sid_to_test_files[sid]
        assert self.monitor.sid_to_test_files[sid][test_name] == file_path
        
        # 파일별 테스트 매핑 확인
        assert file_path in self.monitor.file_to_test_mapping
        assert self.monitor.file_to_test_mapping[file_path] == (sid, test_name)
    
    def test_register_nonexistent_file(self):
        """존재하지 않는 파일 등록 테스트"""
        sid = "TEST_003"
        nonexistent_file = "/path/to/nonexistent/file.sol"
        
        # 경고가 로그되지만 에러는 발생하지 않아야 함
        self.monitor.register_file(sid, nonexistent_file)
        
        # 파일이 존재하지 않으므로 시나리오가 활성화되지 않음
        assert sid not in self.monitor.active_sids
        assert sid not in self.monitor.sid_to_files
        assert nonexistent_file not in self.monitor.file_timestamps
    
    def test_register_test_file(self):
        """테스트 파일 등록 편의 메서드 테스트"""
        sid = "TEST_004"
        test_name = "test_security_check"
        file_path = self.temp_files[1]
        
        self.monitor.register_test_file(sid, test_name, file_path)
        
        # register_file과 동일한 결과인지 확인
        assert sid in self.monitor.sid_to_test_files
        assert test_name in self.monitor.sid_to_test_files[sid]
        assert self.monitor.sid_to_test_files[sid][test_name] == file_path
    
    def test_get_test_file(self):
        """테스트 파일 경로 조회 테스트"""
        sid = "TEST_005"
        test_name = "test_get_file"
        file_path = self.temp_files[2]
        
        # 파일 등록
        self.monitor.register_test_file(sid, test_name, file_path)
        
        # 조회 테스트
        retrieved_path = self.monitor.get_test_file(sid, test_name)
        assert retrieved_path == file_path
        
        # 존재하지 않는 테스트 조회
        non_existent = self.monitor.get_test_file(sid, "non_existent_test")
        assert non_existent is None
        
        # 존재하지 않는 시나리오 조회
        non_existent_sid = self.monitor.get_test_file("NON_EXISTENT_SID", test_name)
        assert non_existent_sid is None
    
    def test_get_test_files_for_scenario(self):
        """시나리오의 모든 테스트 파일 조회 테스트"""
        sid = "TEST_006"
        
        # 여러 테스트 파일 등록
        test_files = {
            "test_one": self.temp_files[0],
            "test_two": self.temp_files[1],
            "test_three": self.temp_files[2]
        }
        
        for test_name, file_path in test_files.items():
            self.monitor.register_test_file(sid, test_name, file_path)
        
        # 모든 테스트 파일 조회
        retrieved_files = self.monitor.get_test_files_for_scenario(sid)
        
        assert len(retrieved_files) == 3
        assert retrieved_files == test_files
        
        # 존재하지 않는 시나리오
        empty_result = self.monitor.get_test_files_for_scenario("NON_EXISTENT")
        assert empty_result == {}
    
    def test_get_test_info_for_file(self):
        """파일 경로로부터 테스트 정보 조회 테스트"""
        sid = "TEST_007"
        test_name = "test_file_info"
        file_path = self.temp_files[0]
        
        # 파일 등록
        self.monitor.register_test_file(sid, test_name, file_path)
        
        # 테스트 정보 조회
        test_info = self.monitor.get_test_info_for_file(file_path)
        assert test_info == (sid, test_name)
        
        # 등록되지 않은 파일
        non_existent_info = self.monitor.get_test_info_for_file("/non/existent/file.sol")
        assert non_existent_info is None
    
    def test_unregister_sid(self):
        """시나리오 모니터링 해제 테스트"""
        sid = "TEST_008"
        
        # 여러 파일 등록
        self.monitor.register_file(sid, self.temp_files[0])
        self.monitor.register_test_file(sid, "test_one", self.temp_files[1])
        self.monitor.register_test_file(sid, "test_two", self.temp_files[2])
        
        # 등록 확인
        assert sid in self.monitor.active_sids
        assert len(self.monitor.sid_to_files[sid]) == 3
        assert len(self.monitor.sid_to_test_files[sid]) == 2
        
        # 시나리오 해제
        self.monitor.unregister_sid(sid)
        
        # 해제 확인
        assert sid not in self.monitor.active_sids
        assert sid not in self.monitor.sid_to_files
        assert sid not in self.monitor.sid_to_test_files
        
        # 파일 관련 정보도 정리되었는지 확인
        for file_path in self.temp_files:
            assert file_path not in self.monitor.file_timestamps
            assert file_path not in self.monitor.file_to_test_mapping
    
    def test_unregister_test(self):
        """특정 테스트 모니터링 해제 테스트"""
        sid = "TEST_009"
        test_name = "test_to_remove"
        file_path = self.temp_files[0]
        
        # 테스트 파일 등록
        self.monitor.register_test_file(sid, test_name, file_path)
        self.monitor.register_test_file(sid, "test_to_keep", self.temp_files[1])
        
        # 등록 확인
        assert len(self.monitor.sid_to_test_files[sid]) == 2
        
        # 특정 테스트 해제
        self.monitor.unregister_test(sid, test_name)
        
        # 해제 확인
        assert test_name not in self.monitor.sid_to_test_files[sid]
        assert len(self.monitor.sid_to_test_files[sid]) == 1
        assert "test_to_keep" in self.monitor.sid_to_test_files[sid]
        
        # 파일 관련 정보 정리 확인
        assert file_path not in self.monitor.file_to_test_mapping
        assert file_path not in self.monitor.file_timestamps
    
    def test_check_for_changes_no_changes(self):
        """변경 사항이 없을 때 테스트"""
        sid = "TEST_010"
        file_path = self.temp_files[0]
        
        # 파일 등록
        self.monitor.register_file(sid, file_path)
        
        # 변경 확인 (변경 없음)
        changes = self.monitor.check_for_changes()
        
        assert changes == {}
    
    def test_check_for_changes_with_modifications(self):
        """파일 수정 시 변경 감지 테스트"""
        sid = "TEST_011"
        file_path = self.temp_files[0]
        
        # 파일 등록
        self.monitor.register_file(sid, file_path)
        
        # 잠시 대기 후 파일 수정 (타임스탬프 차이를 위해)
        time.sleep(0.1)
        with open(file_path, 'a') as f:
            f.write("\n// Modified content\n")
        
        # 변경 확인
        changes = self.monitor.check_for_changes()
        
        assert sid in changes
        assert file_path in changes[sid]
    
    def test_check_test_file_changes(self):
        """특정 테스트 파일 변경 확인 테스트"""
        sid = "TEST_012"
        test_name = "test_change_detection"
        file_path = self.temp_files[0]
        
        # 테스트 파일 등록
        self.monitor.register_test_file(sid, test_name, file_path)
        
        # 변경 없음 확인
        has_changed = self.monitor.check_test_file_changes(sid, test_name)
        assert has_changed is False
        
        # 파일 수정
        time.sleep(0.1)
        with open(file_path, 'a') as f:
            f.write("\n// Test change detection\n")
        
        # 변경 감지 확인
        has_changed = self.monitor.check_test_file_changes(sid, test_name)
        assert has_changed is True
        
        # 존재하지 않는 테스트
        non_existent_change = self.monitor.check_test_file_changes(sid, "non_existent")
        assert non_existent_change is False
    
    def test_apply_changes(self):
        """변경된 파일 처리 테스트"""
        sid = "TEST_013"
        test_name = "test_apply_changes"
        file_path = self.temp_files[0]
        
        # 테스트 파일 등록
        self.monitor.register_test_file(sid, test_name, file_path)
        
        # 가상의 변경 사항
        changes = {
            sid: [file_path]
        }
        
        # 변경 사항 적용 (로깅만 수행)
        self.monitor.apply_changes(changes)
        
        # 에러 없이 실행되었는지 확인 (로깅 기능이므로 특별한 상태 변화 없음)
        assert True
    
    def test_get_monitoring_status(self):
        """모니터링 상태 정보 테스트"""
        # 여러 시나리오와 파일 등록
        scenarios = {
            "SID_001": {
                "test_alpha": self.temp_files[0],
                "test_beta": self.temp_files[1]
            },
            "SID_002": {
                "test_gamma": self.temp_files[2]
            }
        }
        
        for sid, tests in scenarios.items():
            for test_name, file_path in tests.items():
                self.monitor.register_test_file(sid, test_name, file_path)
        
        # 상태 정보 조회
        status = self.monitor.get_monitoring_status()
        
        assert status["active_scenarios"] == 2
        assert status["total_files"] == 3
        assert status["total_test_files"] == 3
        
        # 시나리오별 상세 정보 확인
        assert "SID_001" in status["scenarios"]
        assert "SID_002" in status["scenarios"]
        
        assert status["scenarios"]["SID_001"]["test_files"] == 2
        assert status["scenarios"]["SID_002"]["test_files"] == 1
        
        assert "test_alpha" in status["scenarios"]["SID_001"]["test_names"]
        assert "test_beta" in status["scenarios"]["SID_001"]["test_names"]
        assert "test_gamma" in status["scenarios"]["SID_002"]["test_names"]


class TestFileMonitorEdgeCases:
    """FileMonitor 엣지 케이스 테스트"""
    
    def setup_method(self):
        """각 테스트 전 실행되는 설정"""
        self.monitor = FileMonitor()
    
    def test_register_same_file_multiple_times(self):
        """같은 파일을 여러 번 등록하는 테스트"""
        sid = "EDGE_001"
        
        # 임시 파일 생성
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.sol')
        temp_file.write(b"contract Test {}")
        temp_file.close()
        
        try:
            # 같은 파일을 여러 번 등록
            self.monitor.register_file(sid, temp_file.name)
            self.monitor.register_file(sid, temp_file.name)
            self.monitor.register_file(sid, temp_file.name)
            
            # 중복 등록되지 않았는지 확인
            assert len(self.monitor.sid_to_files[sid]) == 1
            assert temp_file.name in self.monitor.sid_to_files[sid]
        finally:
            os.unlink(temp_file.name)
    
    def test_register_file_different_scenarios(self):
        """같은 파일을 다른 시나리오에 등록하는 테스트"""
        # 임시 파일 생성
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.sol')
        temp_file.write(b"contract Shared {}")
        temp_file.close()
        
        try:
            # 다른 시나리오에 같은 파일 등록
            self.monitor.register_file("SID_A", temp_file.name)
            self.monitor.register_file("SID_B", temp_file.name)
            
            # 두 시나리오 모두에 등록되었는지 확인
            assert temp_file.name in self.monitor.sid_to_files["SID_A"]
            assert temp_file.name in self.monitor.sid_to_files["SID_B"]
            
            # 타임스탬프는 하나만 있어야 함
            assert temp_file.name in self.monitor.file_timestamps
        finally:
            os.unlink(temp_file.name)
    
    def test_unregister_nonexistent_scenario(self):
        """존재하지 않는 시나리오 해제 테스트"""
        # 에러 없이 처리되어야 함
        self.monitor.unregister_sid("NON_EXISTENT_SID")
        assert "NON_EXISTENT_SID" not in self.monitor.active_sids
    
    def test_unregister_nonexistent_test(self):
        """존재하지 않는 테스트 해제 테스트"""
        sid = "EDGE_002"
        
        # 시나리오는 있지만 테스트는 없는 경우
        self.monitor.active_sids.add(sid)
        self.monitor.sid_to_test_files[sid] = {}
        
        # 에러 없이 처리되어야 함
        self.monitor.unregister_test(sid, "non_existent_test")
        
        # 시나리오는 그대로 유지
        assert sid in self.monitor.active_sids
    
    def test_check_changes_deleted_file(self):
        """모니터링 중인 파일이 삭제된 경우 테스트"""
        sid = "EDGE_003"
        
        # 임시 파일 생성 및 등록
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.sol')
        temp_file.write(b"contract ToDelete {}")
        temp_file.close()
        
        self.monitor.register_file(sid, temp_file.name)
        
        # 파일 삭제
        os.unlink(temp_file.name)
        
        # 변경 확인 (경고 로그만 출력되고 에러는 발생하지 않아야 함)
        changes = self.monitor.check_for_changes()
        
        # 삭제된 파일은 변경 목록에 포함되지 않아야 함
        assert sid not in changes or temp_file.name not in changes.get(sid, [])


class TestFileMonitorIntegration:
    """FileMonitor 통합 테스트"""
    
    def setup_method(self):
        """각 테스트 전 실행되는 설정"""
        self.monitor = FileMonitor()
        
        # 여러 임시 파일 생성
        self.test_files = {}
        for i in range(5):
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=f'_integration_{i}.sol')
            temp_file.write(f"// Integration test file {i}\ncontract Integration{i} {{}}\n".encode())
            temp_file.close()
            self.test_files[f"file_{i}"] = temp_file.name
    
    def teardown_method(self):
        """각 테스트 후 실행되는 정리"""
        # 임시 파일들 삭제
        for file_path in self.test_files.values():
            if os.path.exists(file_path):
                os.unlink(file_path)
    
    def test_complete_workflow(self):
        """완전한 워크플로우 테스트"""
        # 1. 여러 시나리오와 테스트 등록
        scenarios = {
            "INTEGRATION_001": {
                "test_basic": self.test_files["file_0"],
                "test_advanced": self.test_files["file_1"]
            },
            "INTEGRATION_002": {
                "test_security": self.test_files["file_2"],
                "test_performance": self.test_files["file_3"]
            }
        }
        
        for sid, tests in scenarios.items():
            for test_name, file_path in tests.items():
                self.monitor.register_test_file(sid, test_name, file_path)
        
        # 2. 상태 확인
        status = self.monitor.get_monitoring_status()
        assert status["active_scenarios"] == 2
        assert status["total_test_files"] == 4
        
        # 3. 파일 수정
        time.sleep(0.1)
        with open(self.test_files["file_0"], 'a') as f:
            f.write("\n// Modified for integration test\n")
        
        # 4. 변경 감지
        changes = self.monitor.check_for_changes()
        assert "INTEGRATION_001" in changes
        assert self.test_files["file_0"] in changes["INTEGRATION_001"]
        
        # 5. 특정 테스트 변경 확인 (이미 check_for_changes에서 타임스탬프가 업데이트되었으므로 False)
        has_changed = self.monitor.check_test_file_changes("INTEGRATION_001", "test_basic")
        assert has_changed is False  # 이미 변경이 감지되어 타임스탬프가 업데이트됨
        
        # 6. 변경 사항 적용
        self.monitor.apply_changes(changes)
        
        # 7. 특정 테스트 해제
        self.monitor.unregister_test("INTEGRATION_001", "test_basic")
        
        # 8. 상태 재확인
        updated_status = self.monitor.get_monitoring_status()
        assert updated_status["total_test_files"] == 3
        assert "test_basic" not in updated_status["scenarios"]["INTEGRATION_001"]["test_names"]
        
        # 9. 전체 시나리오 해제
        self.monitor.unregister_sid("INTEGRATION_002")
        
        # 10. 최종 상태 확인
        final_status = self.monitor.get_monitoring_status()
        assert final_status["active_scenarios"] == 1
        assert "INTEGRATION_002" not in final_status["scenarios"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 