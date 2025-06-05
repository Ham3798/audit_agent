#!/usr/bin/env python3
"""
시나리오 등록 테스트 스크립트
"""

import sys
import os
import json

# 현재 디렉토리를 Python path에 추가
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database.manager import init_db
from services.scenario_service import ScenarioService

def test_scenario_registration():
    """시나리오 등록 테스트"""
    
    # 데이터베이스 초기화
    init_db()
    
    # ScenarioService 초기화
    service = ScenarioService()
    
    # 테스트 시나리오 데이터
    scenario_data = {
        "meta": {
            "id": "BGT_BOOST_MANIPULATION_001",
            "title": "BGT 부스트 시스템 조작 취약점",
            "category": "Boost System Manipulation",
            "severity": "high",
            "tags": ["boost", "queue", "timing", "validation", "bgt"]
        },
        "spec": {
            "description": "BGT 컨트랙트의 부스트 큐 시스템에서 발생할 수 있는 조작 취약점. 악의적 사용자가 부스트 큐와 드롭 큐를 조작하여 시스템을 악용할 수 있음",
            "actors": [
                {"id": "attacker", "role": "malicious_user", "trust_level": "untrusted"},
                {"id": "validator", "role": "network_validator", "trust_level": "trusted"},
                {"id": "normal_user", "role": "bgt_holder", "trust_level": "trusted"}
            ],
            "assets": [
                {"name": "BGT", "type": "governance_token", "critical": True},
                {"name": "validator_rewards", "type": "staking_rewards", "critical": True},
                {"name": "boost_balance", "type": "staked_amount", "critical": True}
            ],
            "attack_vectors": [
                "큐 시스템 타이밍 조작을 통한 부스트 우선순위 획득",
                "부스트 활성화와 드롭의 비동기성을 이용한 이중 스펜딩",
                "userBoosts 상태와 큐 상태 간의 불일치 악용"
            ],
            "trust_boundaries": [
                "BGT 컨트랙트와 외부 사용자 간의 경계",
                "부스트 큐 시스템과 실제 스테이킹 간의 경계",
                "시간 지연 메커니즘과 즉시 실행 요구사항 간의 경계"
            ]
        },
        "code": {
            "target_contract_name": "BGT",
            "vulnerable_functions": ["queueBoost", "activateBoost", "queueDropBoost", "dropBoost", "cancelBoost", "cancelDropBoost"],
            "vulnerability_pattern": "부스트 큐 시스템의 상태 관리와 타이밍 검증 로직에서 발생하는 취약점"
        },
        "hints": {
            "vulnerability_details": {
                "root_cause": "부스트 큐와 드롭 큐의 상태 업데이트가 원자적이지 않고, 시간 기반 검증에 의존",
                "attack_flow": "1. 공격자가 queueBoost로 부스트 예약 -> 2. activateBoost 전에 추가 조작 -> 3. 타이밍을 이용한 상태 불일치 생성",
                "impact": "부정한 밸리데이터 부스트 획득, 스테이킹 보상 조작, 시스템 무결성 훼손"
            },
            "key_patterns": {
                "queue_state_management": "큐 상태와 사용자 상태가 별도로 관리되어 불일치 가능",
                "timing_dependency": "블록 번호 기반 지연시간 검증에 의존",
                "unchecked_arithmetic": "unchecked 블록 사용으로 오버플로우/언더플로우 가능성"
            }
        }
    }
    
    print("=== 시나리오 등록 테스트 시작 ===")
    print(f"시나리오 ID: {scenario_data['meta']['id']}")
    
    # 등록 시도
    result = service.register_scenario(scenario_data)
    
    print("\n=== 등록 결과 ===")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    
    if result.get("success"):
        print("\n✅ 시나리오 등록 성공!")
    else:
        print("\n❌ 시나리오 등록 실패!")
        if "error" in result:
            print(f"오류: {result['error']}")

if __name__ == "__main__":
    test_scenario_registration() 