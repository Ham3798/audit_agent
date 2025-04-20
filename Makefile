# Makefile for Audit Agent

# 가상환경 디렉토리 이름
VENV_DIR := .venv
# 가상환경 내 Python 및 Pip 실행 파일 경로
PYTHON := $(VENV_DIR)/bin/python
PIP := $(VENV_DIR)/bin/pip
PYTEST := $(VENV_DIR)/bin/pytest

# 가상 타겟 정의
.PHONY: install venv run test clean distclean help

# 기본 실행 타겟
default: help

# 도움말
help:
	@echo "사용 가능한 명령어:"
	@echo "  make venv             : Python 가상환경 ($(VENV_DIR))을 생성합니다."
	@echo "  make install          : 가상환경을 생성하고 requirements.txt 의존성을 설치합니다."
	@echo "                          (주의: Slither, Mythril 등 외부 도구는 별도 설치 필요)"
	@echo "  make run              : 가상환경에서 오딧 에이전트 (audit_agent.py)를 실행합니다."
	@echo "  make test             : 가상환경에서 pytest를 사용하여 테스트를 실행합니다."
	@echo "  make clean            : Python 임시 파일 (__pycache__, *.pyc)을 삭제합니다."
	@echo "  make distclean        : 임시 파일과 가상환경 디렉토리를 모두 삭제합니다."

# 가상환경 생성
venv: $(VENV_DIR)/bin/activate

$(VENV_DIR)/bin/activate:
	python3 -m venv $(VENV_DIR)
	@echo "가상환경 '$(VENV_DIR)' 생성 완료."

# 의존성 설치 (가상환경 필요)
install: venv
	$(PIP) install -r requirements.txt
	@echo "--- Python 의존성 설치 완료 ($(VENV_DIR)) ---"
	@echo "주의: Slither, Mythril 등 외부 분석 도구는 시스템에 별도로 설치해야 합니다."
	@echo "requirements.txt 주석을 참고하세요."
	@echo "---"

# 오딧 에이전트 실행 (가상환경 사용)
run: venv
	$(PYTHON) audit_agent.py

# 테스트 실행 (가상환경 사용, 의존성 설치 필요)
# 'tests/' 디렉토리에 테스트 코드가 있다고 가정합니다.
test: install
	$(PYTEST) tests/
	@echo "테스트 실행 완료."

# 임시 파일 정리
clean:
	find . -type f -name '*.py[co]' -delete
	find . -type d -name '__pycache__' -exec rm -rf {} +
	@echo "Python 임시 파일 정리 완료."

# 전체 정리 (임시 파일 + 가상환경)
distclean: clean
	rm -rf $(VENV_DIR)
	@echo "가상환경 '$(VENV_DIR)' 삭제 완료." 