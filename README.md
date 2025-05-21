# mcp-server config
```
{
    "audit-agent": {
        "command": "/Users/ham-yunsig/.local/bin/uv",
        "args":[
          "--directory",
          "/Users/ham-yunsig/Documents/github/audit_agent/mcp-server",
          "run",
          "main.py"
        ]
      }
}
```

# 사용 방법
> audit-agent tool 사용해서 유닛테스트 검증해줘 @PoolManager.t.sol 


# MCP 서버 전체 설명
> v1.1.0 (2024-07-1)  
> 최종 업데이트: 코드 리팩토링 및 에러 처리 개선

## 개요
이 MCP 서버는 스마트컨트랙트 보안 검증 자동화의 핵심 백엔드입니다.

## 역할 및 구조
- MCP는 '테스트 우선' 접근 방식을 지원하여, 기존 시나리오가 없어도 최초 유닛테스트부터 시작하여 보안 검증을 수행할 수 있습니다.
- 최초 유닛테스트 검증 후 LLM이 분석하여 생성한 메타데이터와 스펙을 register_scenario로 등록하는 흐름을 주로 지원합니다.
- 모든 "추론"(시나리오 생성/수정/피드백/코드 diff 해석 등)은 LLM(상위 계층)이 담당하며, MCP는 LLM이 넘겨준 dict(시나리오, 변경사항 등)를 그대로 DB에 저장/업데이트/로깅만 합니다.
- MCP는 입력값의 의미 해석, 적합성 판단, 자동 보정/생성 등은 일절 하지 않습니다.

## 주요 툴 및 사용 흐름

### 1. execute_single_unit_test(sid, test_contract_name, foundry_root_path)
- 기존에 등록된 시나리오가 있는 경우에만 이 방식으로 테스트 실행
- 시나리오가 없으면 에러 반환(추가 시나리오를 먼저 등록해야 함)

### 2. register_scenario(scenario: dict)
- 유닛테스트 분석 후 LLM이 schema_1.0.yaml 구조에 맞게 추론한 시나리오 전체를 입력받아 등록
- meta, spec, code 등 모든 필드를 LLM이 완성해야 하며, MCP는 단순 저장만 함

### 3. update_scenario(sid: str, update_dict: dict)
- LLM이 추론한 시나리오 변경사항(피드백 등)을 입력받아 해당 시나리오를 업데이트
- MCP는 단순히 DB에 반영만 하며, 의미 해석/적합성 판단은 하지 않음

### 4. detect_test_code_diff(sid, test_contract_name, foundry_root_path)
- 테스트 코드(.t.sol) 변경(diff) 자체만 patch log에 기록
- diff의 의미 해석/정합성 판단/추론은 LLM이 담당

## 테스트 우선 워크플로우
1. 최초 유닛테스트(.t.sol)를 실행하고 결과 분석
2. LLM이 테스트 결과를 분석하여 시나리오 구조 및 메타데이터 생성
3. 분석된 시나리오를 register_scenario로 등록
4. 이후 필요에 따라 테스트 코드 변경 및 시나리오 업데이트

## 순차적 사고 과정을 통한 분석 프로세스
1. 초기 관찰 단계: 테스트 로그를 검토하고 기본적인 패턴 식별
2. 심층 분석 단계: 실행 흐름, 상태 변화, 조건부 행동 분석
3. 가설 형성 단계: 시스템 동작 및 보안 영향에 대한 가설 수립
4. 가설 검증 단계: 데이터를 재검토하여 가설 검증 및 대안 고려
5. 인사이트 도출 단계: 검증된 발견 사항을 구조화된 형태로 정리

## 주요 툴 및 사용 흐름
1. execute_single_unit_test(sid, test_contract_name, foundry_root_path) - 유닛테스트 실행 및 결과 수집
2. register_scenario(scenario: dict) - 유닛테스트 분석 후 LLM이 추론한 시나리오 등록
3. update_scenario(sid: str, update_dict: dict) - LLM이 추론한 시나리오 변경사항을 입력받아 업데이트
4. detect_test_code_diff(sid, test_contract_name, foundry_root_path) - 테스트 코드 변경을 patch log에 기록
5. analyze_test_results(sid, run_id, insights) - LLM이 순차적 사고 과정을 통해 테스트 실행 결과를 분석하여 추출한 인사이트를 저장
6. get_cumulative_insights(sid) - 특정 시나리오에 대해 누적된 테스트 분석 인사이트를 조회하고 메타 분석을 수행

## LLM과의 협업 구조
- 최초 테스트 코드 분석 및 시나리오 구조화는 LLM이 주도합니다.
- LLM은 복잡한 스마트 컨트랙트 보안 시나리오를 순차적 사고 과정을 통해 단계적으로 분석합니다.
- 각 사고 단계는 이전 단계를 기반으로 하며, 필요에 따라 이전 사고를 수정하거나 분기하여 더 깊은 분석이 가능합니다.
- 인사이트는 테스트 실행마다 누적되며, 메타 분석을 통해 더 높은 수준의 이해와 패턴 발견으로 이어집니다.
- MCP는 LLM의 순차적 사고 과정을 위한 데이터와 컨텍스트를 제공하고, 도출된 인사이트를 저장하는 역할을 합니다.

## 예시
- 기존 유닛테스트(.t.sol) 실행 및 분석
- LLM이 분석 결과를 바탕으로 schema_1.0.yaml 구조에 맞는 dict 생성
- register_scenario로 시나리오 등록
- 필요시 update_scenario로 변경사항 전달
- 이후 테스트 실행은 execute_single_unit_test로 요청

## 참고
- 각 필드/입력 구조/예시는 schema_1.0.yaml 및 실제 시나리오 예시(D-3.1.yaml 등) 참고