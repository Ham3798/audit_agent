# audit_agent 테스트 가이드

이 디렉토리는 audit_agent 프로젝트의 모든 모듈에 대한 포괄적인 테스트를 제공합니다.

## 📁 테스트 구조

```
tests/
├── __init__.py                 # 테스트 패키지 초기화
├── conftest.py                 # pytest 설정 및 공통 픽스처
├── test_db_manager.py          # 데이터베이스 관리 기능 테스트
├── test_file_monitor.py        # 파일 모니터링 기능 테스트
├── test_schema_validator.py    # 스키마 검증 기능 테스트
├── test_main_mcp_tools.py      # MCP 도구들 테스트
└── README.md                   # 이 파일
```

## 🧪 테스트 모듈 설명

### 1. test_db_manager.py
- **ScenarioDoc 클래스** 테스트
- **유닛테스트 관리** 기능 테스트
- **데이터베이스 CRUD** 작업 테스트
- **실행 로그 및 인사이트** 관리 테스트

### 2. test_file_monitor.py
- **파일 등록 및 모니터링** 테스트
- **테스트별 파일 관리** 테스트
- **변경 감지** 기능 테스트
- **매핑 및 상태 관리** 테스트

### 3. test_schema_validator.py
- **스키마 로드 및 검증** 테스트
- **버전별 검증 로직** 테스트
- **힌트 추출** 기능 테스트
- **에러 처리 및 검증 결과** 테스트

### 4. test_main_mcp_tools.py
- **시나리오 관리 도구들** 테스트
- **유닛테스트 관리 도구들** 테스트
- **실행 및 분석 도구들** 테스트
- **LLM 자율적 검증 도구들** 테스트

## 🚀 테스트 실행 방법

### 기본 실행
```bash
# 모든 테스트 실행
pytest tests/

# 상세 출력으로 실행
pytest tests/ -v

# 특정 모듈 테스트
pytest tests/test_db_manager.py
pytest tests/test_file_monitor.py
pytest tests/test_schema_validator.py
pytest tests/test_main_mcp_tools.py
```

### 마커별 실행
```bash
# 단위 테스트만 실행
pytest tests/ -m unit

# 통합 테스트만 실행
pytest tests/ -m integration

# 느린 테스트 제외하고 실행
pytest tests/ -m "not slow"

# MCP 도구 테스트만 실행
pytest tests/ -m mcp
```

### 커버리지 측정
```bash
# 커버리지와 함께 실행
pytest tests/ --cov=.

# 커버리지 리포트 생성
pytest tests/ --cov=. --cov-report=html

# 특정 모듈 커버리지
pytest tests/ --cov=db_manager --cov=file_monitor
```

### 병렬 실행
```bash
# pytest-xdist 설치 후 병렬 실행
pip install pytest-xdist
pytest tests/ -n auto
```

## 🔧 테스트 설정

### pytest.ini
프로젝트 루트의 `pytest.ini` 파일에서 기본 설정을 관리합니다:
- 테스트 디렉토리: `tests`
- 기본 옵션: 상세 출력, 짧은 traceback, 컬러 출력
- 마커 정의: unit, integration, slow, mcp

### conftest.py
공통 픽스처와 설정을 제공합니다:
- `temp_test_dir`: 테스트용 임시 디렉토리
- `temp_db_file`: 테스트용 임시 데이터베이스 파일
- `mock_foundry_project`: 테스트용 Foundry 프로젝트 구조
- `mock_logging`: 로깅 출력 억제

## 📊 테스트 커버리지 목표

각 모듈별 커버리지 목표:
- **db_manager.py**: 95% 이상
- **file_monitor.py**: 90% 이상
- **schema_validator.py**: 95% 이상
- **main.py (MCP 도구들)**: 85% 이상

## 🐛 테스트 작성 가이드

### 1. 테스트 클래스 구조
```python
class TestModuleName:
    """모듈 테스트"""
    
    def setup_method(self):
        """각 테스트 전 실행되는 설정"""
        pass
    
    def teardown_method(self):
        """각 테스트 후 실행되는 정리"""
        pass
    
    def test_function_name(self):
        """특정 기능 테스트"""
        # Given
        # When
        # Then
        pass
```

### 2. Mock 사용 예시
```python
@patch('module.function')
def test_with_mock(self, mock_function):
    """Mock을 사용한 테스트"""
    mock_function.return_value = "expected_value"
    
    result = function_under_test()
    
    assert result == "expected_value"
    mock_function.assert_called_once()
```

### 3. 픽스처 사용 예시
```python
def test_with_fixture(self, temp_db_file):
    """픽스처를 사용한 테스트"""
    # temp_db_file은 자동으로 생성되고 정리됨
    db = Database(temp_db_file)
    # 테스트 로직
```

## 🔍 디버깅 팁

### 1. 특정 테스트만 실행
```bash
# 클래스별
pytest tests/test_db_manager.py::TestScenarioDoc

# 메서드별
pytest tests/test_db_manager.py::TestScenarioDoc::test_initialization

# 키워드로 필터링
pytest tests/ -k "test_add_unit_test"
```

### 2. 실패한 테스트만 재실행
```bash
pytest tests/ --lf  # last failed
pytest tests/ --ff  # failed first
```

### 3. 디버그 모드
```bash
# pdb 디버거 사용
pytest tests/ --pdb

# 첫 번째 실패에서 중단
pytest tests/ -x
```

## 📝 테스트 결과 해석

### 성공적인 테스트 실행 예시
```
tests/test_db_manager.py::TestScenarioDoc::test_initialization PASSED
tests/test_file_monitor.py::TestFileMonitor::test_register_file PASSED
tests/test_schema_validator.py::TestSchemaValidator::test_validate PASSED
tests/test_main_mcp_tools.py::TestScenarioBasicManagement::test_get_scenario PASSED

========================= 4 passed in 2.34s =========================
```

### 실패한 테스트 분석
- **AssertionError**: 예상값과 실제값 불일치
- **AttributeError**: 존재하지 않는 속성/메서드 접근
- **FileNotFoundError**: 파일 경로 문제
- **Mock 관련 오류**: Mock 설정 문제

## 🚨 주의사항

1. **임시 파일 정리**: 테스트에서 생성한 임시 파일은 반드시 정리해야 합니다.
2. **Mock 사용**: 외부 의존성(파일 I/O, 네트워크, 데이터베이스)은 Mock으로 처리합니다.
3. **테스트 독립성**: 각 테스트는 다른 테스트에 영향을 주지 않아야 합니다.
4. **명확한 테스트명**: 테스트 함수명은 테스트하는 기능을 명확히 표현해야 합니다.

## 📚 추가 자료

- [pytest 공식 문서](https://docs.pytest.org/)
- [unittest.mock 가이드](https://docs.python.org/3/library/unittest.mock.html)
- [Python 테스트 베스트 프랙티스](https://docs.python-guide.org/writing/tests/) 