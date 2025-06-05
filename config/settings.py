"""
Global settings for audit_agent project

이 모듈은 프로젝트 전반에서 사용되는 설정값들을 중앙에서 관리합니다.
환경변수, 기본값, 경로 설정 등을 포함합니다.
"""

import os
from typing import Optional
from dataclasses import dataclass


@dataclass
class Settings:
    """audit_agent 프로젝트의 전역 설정 클래스"""
    
    # 데이터베이스 설정
    database_path: str = os.getenv("SCENARIO_DB", "scenario_dyn.db")
    
    # 스키마 설정
    default_schema_path: str = "schemas/schema_1.0.yaml"
    
    # 로깅 설정
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    log_file_path: str = "audit_agent.log"
    db_log_file_path: str = "db-manager.log"
    mcp_log_file_path: str = "mcp-server.log"
    
    # Foundry 설정
    foundry_command: str = "forge"
    default_gas_limit: int = 30000000
    
    # 파일 처리 설정
    max_log_size: int = 4000  # 로그 텍스트 최대 크기 (문자 수)
    scenarios_folder: str = "scenarios"
    
    # 테스트 설정
    test_timeout: int = 300  # 테스트 타임아웃 (초)
    max_parallel_tests: int = 5
    
    # MCP 서버 설정
    server_name: str = "audit-agent"
    server_version: str = "2.0.0"
    
    @classmethod
    def get_instance(cls) -> 'Settings':
        """싱글톤 패턴으로 Settings 인스턴스 반환"""
        if not hasattr(cls, '_instance'):
            cls._instance = cls()
        return cls._instance
    
    def get_absolute_path(self, relative_path: str) -> str:
        """상대 경로를 절대 경로로 변환"""
        if os.path.isabs(relative_path):
            return relative_path
        return os.path.abspath(relative_path)
    
    def validate_settings(self) -> None:
        """설정값들의 유효성을 검증"""
        if not os.path.exists(os.path.dirname(self.database_path)):
            os.makedirs(os.path.dirname(self.database_path), exist_ok=True)
            
        if not os.path.exists(self.scenarios_folder):
            os.makedirs(self.scenarios_folder, exist_ok=True)


# 전역 설정 인스턴스
settings = Settings.get_instance() 