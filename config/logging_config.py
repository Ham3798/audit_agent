"""
Logging configuration for audit_agent project

이 모듈은 프로젝트 전반의 로깅 설정을 중앙에서 관리합니다.
각 모듈별로 적절한 로거를 설정하고 일관된 로그 형식을 제공합니다.
"""

import logging
import logging.handlers
import os
from typing import Optional
from .settings import settings


def setup_logging(
    logger_name: str = None,
    log_file: str = None,
    level: str = None,
    console_output: bool = True
) -> logging.Logger:
    """
    로거를 설정하고 반환합니다.
    
    Args:
        logger_name: 로거 이름 (None이면 루트 로거)
        log_file: 로그 파일 경로 (None이면 파일 로깅 없음)
        level: 로그 레벨 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        console_output: 콘솔 출력 여부
        
    Returns:
        설정된 로거 인스턴스
    """
    # 로거 생성
    logger = logging.getLogger(logger_name or "audit_agent")
    
    # 기존 핸들러 제거 (중복 방지)
    logger.handlers.clear()
    
    # 로그 레벨 설정
    log_level = getattr(logging, (level or settings.log_level).upper(), logging.INFO)
    logger.setLevel(log_level)
    
    # 로그 포맷 설정
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # 콘솔 핸들러 추가
    if console_output:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(log_level)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
    
    # 파일 핸들러 추가
    if log_file:
        # 로그 파일 디렉토리 생성
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)
        
        # 회전하는 파일 핸들러 (10MB, 최대 5개 파일)
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setLevel(log_level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    # 전파 방지 (중복 로깅 방지)
    logger.propagate = False
    
    return logger


def get_logger(module_name: str) -> logging.Logger:
    """
    모듈별 로거를 가져옵니다.
    
    Args:
        module_name: 모듈 이름 (예: "database", "validation", "mcp_tools")
        
    Returns:
        해당 모듈의 로거
    """
    logger_configs = {
        "database": {
            "log_file": settings.db_log_file_path,
            "level": settings.log_level
        },
        "mcp_server": {
            "log_file": settings.mcp_log_file_path,
            "level": settings.log_level
        },
        "validation": {
            "log_file": "logs/validation.log",
            "level": settings.log_level
        },
        "services": {
            "log_file": "logs/services.log",
            "level": settings.log_level
        },
        "utils": {
            "log_file": "logs/utils.log",
            "level": settings.log_level
        }
    }
    
    config = logger_configs.get(module_name, {
        "log_file": f"logs/{module_name}.log",
        "level": settings.log_level
    })
    
    return setup_logging(
        logger_name=f"audit_agent.{module_name}",
        **config
    )


def setup_project_logging():
    """
    프로젝트 전체의 로깅을 초기화합니다.
    이 함수는 애플리케이션 시작 시 한 번만 호출되어야 합니다.
    """
    # 로그 디렉토리 생성
    os.makedirs("logs", exist_ok=True)
    
    # 루트 로거 설정
    root_logger = setup_logging(
        logger_name="audit_agent",
        log_file=settings.log_file_path,
        level=settings.log_level,
        console_output=True
    )
    
    # 각 모듈별 로거 초기화
    modules = ["database", "validation", "services", "utils", "mcp_server"]
    for module in modules:
        get_logger(module)
    
    root_logger.info("프로젝트 로깅 시스템이 초기화되었습니다.")
    return root_logger 