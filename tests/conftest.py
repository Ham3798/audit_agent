"""
pytest 설정 파일

테스트 실행을 위한 공통 설정과 픽스처를 정의합니다.
"""

import pytest
import os
import tempfile
import shutil
from unittest.mock import patch
import sys

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 테스트용 임시 디렉토리 설정
@pytest.fixture(scope="session")
def temp_test_dir():
    """테스트용 임시 디렉토리 생성"""
    temp_dir = tempfile.mkdtemp(prefix="audit_agent_test_")
    yield temp_dir
    # 테스트 완료 후 정리
    shutil.rmtree(temp_dir, ignore_errors=True)

@pytest.fixture(scope="function")
def temp_db_file():
    """테스트용 임시 데이터베이스 파일"""
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
    temp_file.close()
    yield temp_file.name
    # 테스트 완료 후 파일 삭제
    if os.path.exists(temp_file.name):
        os.unlink(temp_file.name)

@pytest.fixture(scope="function")
def mock_foundry_project(temp_test_dir):
    """테스트용 Foundry 프로젝트 구조 생성"""
    foundry_dir = os.path.join(temp_test_dir, "foundry_project")
    os.makedirs(foundry_dir, exist_ok=True)
    
    # 기본 디렉토리 구조 생성
    test_dir = os.path.join(foundry_dir, "test")
    src_dir = os.path.join(foundry_dir, "src")
    os.makedirs(test_dir, exist_ok=True)
    os.makedirs(src_dir, exist_ok=True)
    
    # 기본 파일들 생성
    foundry_toml = os.path.join(foundry_dir, "foundry.toml")
    with open(foundry_toml, 'w') as f:
        f.write("""
[profile.default]
src = "src"
out = "out"
libs = ["lib"]
test = "test"
""")
    
    yield foundry_dir

@pytest.fixture(autouse=True)
def mock_logging():
    """로깅 출력을 억제하여 테스트 출력을 깔끔하게 유지"""
    with patch('logging.getLogger'):
        yield

@pytest.fixture(autouse=True)
def isolated_db():
    """각 테스트마다 독립적인 임시 DB 사용"""
    # 임시 DB 파일 생성
    temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
    temp_db.close()
    
    # database.manager의 _DB 변수를 임시 DB로 패치
    with patch('database.manager._DB', temp_db.name):
        # DB 초기화 함수 호출
        from database.manager import init_db
        init_db()
        yield temp_db.name
    
    # 테스트 후 임시 DB 삭제
    try:
        os.unlink(temp_db.name)
    except FileNotFoundError:
        pass

@pytest.fixture
def sample_scenario():
    """테스트용 샘플 시나리오 데이터"""
    return {
        "meta": {
            "id": "TEST_001",
            "title": "테스트 시나리오",
            "category": "test",
            "severity": "medium",
            "tags": ["test"],
            "author": "test_user",
            "created": "2024-01-01T00:00:00Z"
        },
        "spec": {
            "description": "테스트용 시나리오입니다",
            "actors": [{"id": "user", "role": "EOA", "trust_level": "trusted"}],
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
            "poc_contract": "contract Test {}",
            "target_contract_name": "TestContract",
            "deployment_script": ""
        },
        "unit_tests": [
            {
                "test_name": "test_basic",
                "description": "기본 테스트",
                "test_code": "function test_basic() public {}",
                "expected_behavior": "성공",
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

@pytest.fixture
def temp_foundry_project():
    """임시 Foundry 프로젝트 디렉토리"""
    with tempfile.TemporaryDirectory() as temp_dir:
        # 기본 Foundry 구조 생성
        os.makedirs(os.path.join(temp_dir, "test"), exist_ok=True)
        os.makedirs(os.path.join(temp_dir, "src"), exist_ok=True)
        
        # foundry.toml 파일 생성
        foundry_toml = """[profile.default]
src = "src"
out = "out"
libs = ["lib"]
test = "test"

[rpc_endpoints]
mainnet = "https://eth-mainnet.alchemyapi.io/v2/YOUR-API-KEY"
"""
        with open(os.path.join(temp_dir, "foundry.toml"), "w") as f:
            f.write(foundry_toml)
            
        yield temp_dir

@pytest.fixture
def mock_mcp_server():
    """Mock MCP 서버"""
    from unittest.mock import AsyncMock, MagicMock
    
    server = MagicMock()
    server.call_tool = AsyncMock()
    return server

# 테스트 마커 정의
def pytest_configure(config):
    """pytest 설정"""
    config.addinivalue_line(
        "markers", "slow: 느린 테스트 (실제 파일 I/O 포함)"
    )
    config.addinivalue_line(
        "markers", "integration: 통합 테스트"
    )
    config.addinivalue_line(
        "markers", "unit: 단위 테스트"
    )

# 테스트 수집 시 경고 무시
def pytest_collection_modifyitems(config, items):
    """테스트 수집 시 설정"""
    for item in items:
        # 느린 테스트 마킹
        if "integration" in item.nodeid:
            item.add_marker(pytest.mark.slow)
        
        # 단위 테스트 마킹
        if any(keyword in item.nodeid for keyword in ["test_unit", "test_basic"]):
            item.add_marker(pytest.mark.unit) 