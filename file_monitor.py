"""
파일 모니터링 모듈 (v1.3.0)

이 모듈은 시나리오 관련 파일의 변경 사항을 감지하고 처리하는 기능을 제공합니다.

[핵심 아키텍처 변화: 1 시나리오 = 1 PoC + n개 유닛테스트]
- 기존: 1 시나리오 = 1 테스트 파일 모니터링
- 신규: 1 시나리오 = n개의 유닛테스트 파일 개별 모니터링
- 테스트별 파일 매핑 및 변경 추적 지원
- 각 유닛테스트 파일을 독립적으로 모니터링하고 변경 감지

[새로운 모니터링 기능]
1. 테스트별 파일 관리:
   - register_test_file(): 특정 테스트의 파일 등록
   - get_test_file(): 특정 테스트의 파일 경로 조회
   - get_test_files_for_scenario(): 시나리오의 모든 테스트 파일 조회
   - get_test_info_for_file(): 파일 경로로부터 테스트 정보 조회
   - unregister_test(): 특정 테스트 모니터링 해제

2. 확장된 변경 감지:
   - check_test_file_changes(): 특정 테스트 파일의 변경 여부 확인
   - 테스트별 변경 로깅 및 추적
   - 파일별 테스트 이름 매핑 지원

3. 새로운 데이터 구조:
   - sid_to_test_files: 시나리오별 테스트 파일 매핑 {sid: {test_name: file_path}}
   - file_to_test_mapping: 파일별 테스트 정보 매핑 {file_path: (sid, test_name)}

[주요 클래스 및 메서드]
- FileMonitor: 메인 모니터링 클래스
  - register_file(): 파일 등록 (테스트 이름 지원)
  - register_test_file(): 테스트 파일 등록 편의 메서드
  - check_for_changes(): 전체 파일 변경 확인
  - check_test_file_changes(): 특정 테스트 파일 변경 확인
  - apply_changes(): 변경된 파일 처리
  - get_monitoring_status(): 모니터링 상태 정보

[모니터링 범위]
- 시나리오별 관련 파일들
- 테스트별 개별 파일들
- 파일 수정 시간 추적
- 변경 감지 및 자동 처리

[기존 호환성]
- 기존 파일 모니터링 기능과 완전 호환
- 새로운 테스트별 모니터링 기능 추가
- 기존 시나리오의 파일 모니터링 유지
"""
import os
import logging
from typing import Dict, List, Set, Optional, Any

# 로거 설정
logger = logging.getLogger("file-monitor")
logger.setLevel(logging.INFO)
handler = logging.FileHandler("file-monitor.log")
handler.setLevel(logging.INFO)
logger.addHandler(handler)

class FileMonitor:
    """
    파일 변경 감지 및 처리 클래스
    
    시나리오와 관련된 파일들의 변경 사항을 감지하고 필요한 처리를 수행합니다.
    n개의 유닛테스트 파일을 지원하며, 테스트별로 파일 변경을 추적합니다.
    """
    
    def __init__(self):
        """FileMonitor 초기화"""
        # 모니터링할 시나리오 ID 목록
        self.active_sids: Set[str] = set()
        
        # 파일 경로별 마지막 수정 시간
        self.file_timestamps: Dict[str, float] = {}
        
        # 시나리오별 관련 파일 매핑
        self.sid_to_files: Dict[str, List[str]] = {}
        
        # 시나리오별 테스트 파일 매핑 (새로 추가)
        # 구조: {sid: {test_name: file_path}}
        self.sid_to_test_files: Dict[str, Dict[str, str]] = {}
        
        # 파일별 테스트 이름 매핑 (새로 추가)
        # 구조: {file_path: (sid, test_name)}
        self.file_to_test_mapping: Dict[str, tuple] = {}
        
        logger.info("FileMonitor 초기화 완료 (n개 유닛테스트 지원)")
    
    def register_file(self, sid: str, file_path: str, test_name: str = "") -> None:
        """
        시나리오와 관련된 파일 등록 (테스트 이름 지원)
        
        Args:
            sid: 시나리오 ID
            file_path: 모니터링할 파일 경로
            test_name: 테스트 이름 (유닛테스트 파일인 경우)
        """
        if not os.path.exists(file_path):
            logger.warning(f"파일이 존재하지 않음: {file_path}")
            return
        
        # 시나리오 ID를 활성 목록에 추가
        self.active_sids.add(sid)
        
        # 시나리오별 파일 목록에 추가
        if sid not in self.sid_to_files:
            self.sid_to_files[sid] = []
        
        if file_path not in self.sid_to_files[sid]:
            self.sid_to_files[sid].append(file_path)
        
        # 테스트 파일인 경우 추가 매핑 정보 저장
        if test_name:
            if sid not in self.sid_to_test_files:
                self.sid_to_test_files[sid] = {}
            
            self.sid_to_test_files[sid][test_name] = file_path
            self.file_to_test_mapping[file_path] = (sid, test_name)
            
            logger.info(f"테스트 파일 등록: sid={sid}, test_name={test_name}, file={file_path}")
        else:
            logger.info(f"일반 파일 등록: sid={sid}, file={file_path}")
        
        # 초기 타임스탬프 기록
        self.file_timestamps[file_path] = os.path.getmtime(file_path)
    
    def register_test_file(self, sid: str, test_name: str, file_path: str) -> None:
        """
        특정 테스트의 파일을 등록하는 편의 메서드
        
        Args:
            sid: 시나리오 ID
            test_name: 테스트 이름
            file_path: 테스트 파일 경로
        """
        self.register_file(sid, file_path, test_name)
    
    def get_test_file(self, sid: str, test_name: str) -> Optional[str]:
        """
        특정 테스트의 파일 경로 조회
        
        Args:
            sid: 시나리오 ID
            test_name: 테스트 이름
            
        Returns:
            Optional[str]: 파일 경로 (없으면 None)
        """
        if sid in self.sid_to_test_files:
            return self.sid_to_test_files[sid].get(test_name)
        return None
    
    def get_test_files_for_scenario(self, sid: str) -> Dict[str, str]:
        """
        시나리오의 모든 테스트 파일 조회
        
        Args:
            sid: 시나리오 ID
            
        Returns:
            Dict[str, str]: {test_name: file_path} 매핑
        """
        return self.sid_to_test_files.get(sid, {})
    
    def get_test_info_for_file(self, file_path: str) -> Optional[tuple]:
        """
        파일 경로로부터 테스트 정보 조회
        
        Args:
            file_path: 파일 경로
            
        Returns:
            Optional[tuple]: (sid, test_name) 또는 None
        """
        return self.file_to_test_mapping.get(file_path)
    
    def unregister_sid(self, sid: str) -> None:
        """
        시나리오 모니터링 해제
        
        Args:
            sid: 시나리오 ID
        """
        if sid in self.active_sids:
            self.active_sids.remove(sid)
        
        # 해당 시나리오 관련 파일 목록 제거
        if sid in self.sid_to_files:
            # 파일 타임스탬프 정보도 정리
            for file_path in self.sid_to_files[sid]:
                if file_path in self.file_timestamps:
                    del self.file_timestamps[file_path]
                
                # 테스트 파일 매핑 정보도 정리
                if file_path in self.file_to_test_mapping:
                    del self.file_to_test_mapping[file_path]
            
            del self.sid_to_files[sid]
        
        # 테스트 파일 매핑 정보 정리
        if sid in self.sid_to_test_files:
            del self.sid_to_test_files[sid]
        
        logger.info(f"시나리오 모니터링 해제: sid={sid}")
    
    def unregister_test(self, sid: str, test_name: str) -> None:
        """
        특정 테스트 모니터링 해제
        
        Args:
            sid: 시나리오 ID
            test_name: 테스트 이름
        """
        if sid in self.sid_to_test_files and test_name in self.sid_to_test_files[sid]:
            file_path = self.sid_to_test_files[sid][test_name]
            
            # 테스트 파일 매핑에서 제거
            del self.sid_to_test_files[sid][test_name]
            
            # 파일 매핑에서 제거
            if file_path in self.file_to_test_mapping:
                del self.file_to_test_mapping[file_path]
            
            # 시나리오 파일 목록에서 제거
            if sid in self.sid_to_files and file_path in self.sid_to_files[sid]:
                self.sid_to_files[sid].remove(file_path)
            
            # 타임스탬프 정보 제거
            if file_path in self.file_timestamps:
                del self.file_timestamps[file_path]
            
            logger.info(f"테스트 모니터링 해제: sid={sid}, test_name={test_name}")
    
    def check_for_changes(self) -> Dict[str, List[str]]:
        """
        파일 변경 사항 확인
        
        Returns:
            Dict[str, List[str]]: 시나리오별 변경된 파일 목록
        """
        changed_files = {}
        
        for sid in self.active_sids:
            if sid not in self.sid_to_files:
                continue
            
            sid_changed_files = []
            
            for file_path in self.sid_to_files[sid]:
                if not os.path.exists(file_path):
                    logger.warning(f"모니터링 중인 파일이 삭제됨: {file_path}")
                    continue
                
                current_mtime = os.path.getmtime(file_path)
                last_mtime = self.file_timestamps.get(file_path, 0)
                
                if current_mtime > last_mtime:
                    sid_changed_files.append(file_path)
                    self.file_timestamps[file_path] = current_mtime
                    
                    # 테스트 파일인 경우 추가 로깅
                    test_info = self.get_test_info_for_file(file_path)
                    if test_info:
                        _, test_name = test_info
                        logger.info(f"테스트 파일 변경 감지: sid={sid}, test_name={test_name}, file={file_path}")
                    else:
                        logger.info(f"파일 변경 감지: sid={sid}, file={file_path}")
            
            if sid_changed_files:
                changed_files[sid] = sid_changed_files
        
        return changed_files
    
    def check_test_file_changes(self, sid: str, test_name: str) -> bool:
        """
        특정 테스트 파일의 변경 여부 확인
        
        Args:
            sid: 시나리오 ID
            test_name: 테스트 이름
            
        Returns:
            bool: 변경되었으면 True
        """
        file_path = self.get_test_file(sid, test_name)
        if not file_path or not os.path.exists(file_path):
            return False
        
        current_mtime = os.path.getmtime(file_path)
        last_mtime = self.file_timestamps.get(file_path, 0)
        
        if current_mtime > last_mtime:
            self.file_timestamps[file_path] = current_mtime
            logger.info(f"테스트 파일 변경 확인: sid={sid}, test_name={test_name}")
            return True
        
        return False
    
    def apply_changes(self, changed_files: Dict[str, List[str]]) -> None:
        """
        변경된 파일 처리
        
        Args:
            changed_files: 시나리오별 변경된 파일 목록
        """
        for sid, files in changed_files.items():
            logger.info(f"시나리오 {sid}의 {len(files)}개 파일 변경 처리")
            
            for file_path in files:
                test_info = self.get_test_info_for_file(file_path)
                if test_info:
                    _, test_name = test_info
                    logger.info(f"테스트 파일 변경 처리: test_name={test_name}, file={file_path}")
                else:
                    logger.info(f"일반 파일 변경 처리: file={file_path}")
    
    def get_monitoring_status(self) -> Dict[str, Any]:
        """
        모니터링 상태 정보 반환
        
        Returns:
            Dict[str, Any]: 모니터링 상태 정보
        """
        total_files = sum(len(files) for files in self.sid_to_files.values())
        total_test_files = sum(len(tests) for tests in self.sid_to_test_files.values())
        
        return {
            "active_scenarios": len(self.active_sids),
            "total_files": total_files,
            "total_test_files": total_test_files,
            "scenarios": {
                sid: {
                    "files": len(self.sid_to_files.get(sid, [])),
                    "test_files": len(self.sid_to_test_files.get(sid, {})),
                    "test_names": list(self.sid_to_test_files.get(sid, {}).keys())
                }
                for sid in self.active_sids
            }
        }