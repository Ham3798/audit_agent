"""
Audit Agent MCP Server - MVP Version

스마트컨트랙트 보안 취약점 PoC 개발을 위한 MCP 서버
"""

import os
from mcp.server.fastmcp import FastMCP

# 설정 및 데이터베이스
from config.logging_config import get_logger
from database.manager import init_db

# MCP 도구들
from mcp_tools import ScenarioMCPTools, TestMCPTools, AnalysisMCPTools, PocMCPTools

# 로거 설정
logger = get_logger("main")

# MCP 서버 초기화
mcp = FastMCP("audit-agent-mcp")

def register_all_mcp_tools():
    """모든 MCP 도구들을 등록합니다."""
    # 기존 도구들
    scenario_tools = ScenarioMCPTools()
    test_tools = TestMCPTools()
    analysis_tools = AnalysisMCPTools()
    poc_tools = PocMCPTools()
    
    scenario_tools.register_tools(mcp)
    test_tools.register_tools(mcp)
    analysis_tools.register_tools(mcp)
    poc_tools.register_tools(mcp)
    
    logger.info("모든 MCP 도구들이 등록되었습니다.")

def run_server():
    """MCP 서버를 실행합니다."""
    logger.info("✅ Audit Agent MCP 서버 시작")
    mcp.run()

if __name__ == "__main__":
    # 개선된 init_db() 함수가 모든 초기화를 담당
    init_db()
    register_all_mcp_tools()
    run_server()