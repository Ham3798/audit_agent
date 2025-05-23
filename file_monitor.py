"""
파일 모니터링 모듈

이 모듈은 시나리오 관련 파일의 변경 사항을 감지하고 처리하는 기능을 제공합니다.
"""
import os
import logging
from typing import Dict, List, Set

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
    """
    
    def __init__(self):
        """FileMonitor 초기화"""
        # 모니터링할 시나리오 ID 목록
        self.active_sids: Set[str] = set()
        
        # 파일 경로별 마지막 수정 시간
        self.file_timestamps: Dict[str, float] = {}
        
        # 시나리오별 관련 파일 매핑
        self.sid_to_files: Dict[str, List[str]] = {}
        
        logger.info("FileMonitor 초기화 완료")
    
    def register_file(self, sid: str, file_path: str) -> None:
        """
        시나리오와 관련된 파일 등록
        
        Args:
            sid: 시나리오 ID
            file_path: 모니터링할 파일 경로
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
        
        # 초기 타임스탬프 기록
        self.file_timestamps[file_path] = os.path.getmtime(file_path)
        
        logger.info(f"파일 등록: sid={sid}, file={file_path}")
    
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
            
            del self.sid_to_files[sid]
        
        logger.info(f"시나리오 모니터링 해제: sid={sid}")
    
    def check_for_changes(self) -> Dict[str, List[str]]:
        """
        파일 변경 사항 확인 (간단한 구현)
        
        Returns:
            Dict[str, List[str]]: 시나리오별 변경된 파일 목록
        """
        # 실제 MCP tools에서는 이 메서드가 크게 사용되지 않으므로 
        # 간단한 구현만 유지
        logger.info("파일 변경 확인 (미사용 기능)")
        return {}
    
    def apply_changes(self, changed_files: Dict[str, List[str]]) -> None:
        """
        변경된 파일 처리 (간단한 구현)
        
        Args:
            changed_files: 시나리오별 변경된 파일 목록
        """
        # 실제 MCP tools에서는 이 메서드가 크게 사용되지 않으므로 
        # 간단한 구현만 유지
        logger.info("파일 변경 처리 (미사용 기능)")