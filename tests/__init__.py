"""
audit_agent 테스트 패키지

이 패키지는 audit_agent 프로젝트의 모든 모듈에 대한 포괄적인 테스트를 제공합니다.

테스트 모듈:
- test_db_manager.py: 데이터베이스 관리 기능 테스트
- test_file_monitor.py: 파일 모니터링 기능 테스트  
- test_schema_validator.py: 스키마 검증 기능 테스트
- test_main_mcp_tools.py: MCP 도구들 테스트

실행 방법:
    # 모든 테스트 실행
    pytest tests/
    
    # 특정 모듈 테스트
    pytest tests/test_db_manager.py
    
    # 상세 출력으로 실행
    pytest tests/ -v
    
    # 커버리지와 함께 실행
    pytest tests/ --cov=.
""" 