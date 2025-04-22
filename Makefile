# Makefile for Audit Agent Project

# --- 변수 --- #
PYTHON = python3
PIP = pip
VENV_DIR = .venv
SRC_DIR = src
MAIN_SCRIPT = $(SRC_DIR)/main.py

# --- 타겟 --- #
.PHONY: help install run clean

help:
	@echo "사용 가능한 명령어:"
	@echo "  make install : 가상 환경을 생성하고 의존성을 설치합니다."
	@echo "  make run     : 감사 에이전트를 실행합니다 (기본 URL 사용)."
	@echo "  make run url=<URL> : 특정 GitHub URL로 감사 에이전트를 실행합니다."
	@echo "  make clean   : 가상 환경과 생성된 파일/디렉토리를 삭제합니다."

# 가상 환경 생성 및 의존성 설치
install: $(VENV_DIR)/bin/activate

$(VENV_DIR)/bin/activate:
	@echo "Creating virtual environment in $(VENV_DIR)..."
	$(PYTHON) -m venv $(VENV_DIR)
	@echo "Installing dependencies from requirements.txt..."
	$(VENV_DIR)/bin/$(PIP) install -r requirements.txt
	@echo "Installation complete."

# 감사 에이전트 실행
run:
	@echo "Running Audit Agent..."
	$(VENV_DIR)/bin/$(PYTHON) -m $(SRC_DIR).main $(url)

# 정리
clean:
	@echo "Cleaning up..."
	rm -rf $(VENV_DIR)
	rm -rf audit_repo
	find . -type f -name '*.pyc' -delete
	find . -type d -name '__pycache__' -delete
	@echo "Cleanup complete." 