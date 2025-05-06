# scenario schema

사람-가독성 + LLM-친화성 > 자연어 섹션과 구조화 섹션을 모두 둔다.
Very-High ↔ Low-Level 완전 분리 > “뭐가 일어나야 하나” (변하지 않음) vs. “어떻게 코드로 쓰나” (LLM이 채움).
옵셔널 오버라이드 > LLM이 못 맞추면 사람이 코드-힌트를 덧붙일 수 있다.

# 파이프라인
```
author.yaml
   ↓ (1) pydantic.validate()
ThreatScenario 객체
   ↓ (2) render_tests()
*.t.sol  (Forge 템플릿)
   ↓ (3) forge test
raw-json results
   ↓ (4) parse_forge_json()
TestSuite 객체  ←─────┐
   └───────────> (5) slither, fuzz, dashboard, LLM
```

## 0. 파일 전체 골격
```
schema_version: "scenario-schema-1.0"

###############################################################################
# L0. META – 고정 식별자
###############################################################################
meta:
  id          : ""                        # e.g. "S-1.1"
  title       : ""                        # 시나리오 요약
  category    : ""                        # 예: "Spoofing"
  severity    : ""                        # 예: "critical"
  tags        : []                        # 예: [ hooks, pool ]
  author      : ""                        # 작성자
  created     : ""                        # ISO8601: "YYYY-MM-DDTHH:MM:SS+TZ"

###############################################################################
# L1. SPEC – 위협 모델링 기반 구조화 시나리오
###############################################################################
spec:
  description: ""                           # 시나리오 개요 (자연어)

  actors:
    - id: "user"
      role: "EOA user"
      trust_level: "untrusted"

  assets:
    - name: "Hook"
      type: "address"
      critical: true

  components:
    - name: "PoolManager"
      type: "contract"
      deployed_at: "0x..."

  trust_boundaries:
    - from: "user"
      to: "PoolManager"
      enforcement: "msg.sender check"

  data_flows:
    - source: "user"
      target: "PoolManager"
      function: "initialize"
      params:
        - name: "hook"
          value: "0x0"

  behaviors:
    - actor: "user"
      action: "calls initialize with invalid hook address"

  precondition: >
    The PoolManager has not yet been initialized.
    The provided hook address is not whitelisted.

  action: >
    User calls initialize(hook = address(0x0)).

  expected: >
    Transaction must revert with `HookAddressNotValid` selector.

###############################################################################
# L1. GEN_REQUIRED_EXECUTION_CONTEXT_PROMPT
###############################################################################

gen_prompt:
  model_info:
    name: "gpt-4o"
    temperature: 0.2
    seed: 1234

  prompt_template: |
    You are given a threat scenario that should be tested and possibly disproven using Foundry (Solidity) unit tests.

    Your job is to generate the **required execution context** to allow this test to run, including:
    - import statements for external modules
    - helper contracts that need to be defined (e.g., mock hooks or dummy tokens)
    - mock deployment logic for setUp()
    - the target contract instance declaration

    ### Threat Scenario Metadata ###
    - ID        : {{ meta.id }}
    - Title     : {{ meta.title }}
    - Category  : {{ meta.category }}
    - Severity  : {{ meta.severity }}
    - Tags      : {{ meta.tags | join(', ') }}

    ### SPEC: System Model ###
    - Actors:
    {% for actor in spec.actors %}
      - {{ actor.id }} ({{ actor.role }}, trust: {{ actor.trust_level }})
    {% endfor %}

    - Assets:
    {% for asset in spec.assets %}
      - {{ asset.name }} (type: {{ asset.type }}, critical: {{ asset.critical }})
    {% endfor %}

    - Components:
    {% for comp in spec.components %}
      - {{ comp.name }} ({{ comp.type }})
    {% endfor %}

    - Trust Boundaries:
    {% for tb in spec.trust_boundaries %}
      - {{ tb.from }} → {{ tb.to }} (enforced by: {{ tb.enforcement }})
    {% endfor %}

    - Data Flows:
    {% for flow in spec.data_flows %}
      - {{ flow.source }} calls {{ flow.function }} on {{ flow.target }} with params: {{ flow.params }}
    {% endfor %}

    - Behaviors:
    {% for behavior in spec.behaviors %}
      - {{ behavior.actor | default(behavior.component) }} → {{ behavior.action }}
    {% endfor %}

    ### SPEC: Scenario Summary ###
    - Precondition: {{ spec.precondition }}
    - Action      : {{ spec.action }}
    - Expected    : {{ spec.expected }}

    ### INSTRUCTIONS ###
    Based on the above:
    1. Output a list of required import lines under key `required_imports`
    2. Output a list of helper contracts (with `name` and `definition_code`)
    3. Output a `mock_deployments_code` block as a Solidity snippet for setUp()
    4. Output the `target_contract_declaration` and `target_instance_name` to be used

    Output your result as YAML.


###############################################################################
# L2. CODE – 템플릿 슬롯
###############################################################################
code:
  compiler_version : ""                   # "^0.8.24"
  imports          : []                   # list of import lines
  helpers          : []                   # list of HelperContract objects (명시적 정의)
  target:
    declaration   : ""                    # "PoolManager internal manager;"
    instance_name : ""                    # "manager"
  mock_deployments: ""                    # mock/fixture 배포 코드
  setup            : |                   # setUp() 내부 general setup
    ""
  test_setup       : |                   # test-specific setup
    ""
  action:
    function : ""                         # "initialize"
    code     : |                         # 실행 코드 블록
      ""
  oracle:
    revert_selector : ""                 # e.g. "Hooks.HookAddressNotValid.selector"
    assertion_code  : ""                 # 추가 상태검사 코드

###############################################################################
# L2-HINTS – 컴파일러/정적 분석/런타임 힌트
###############################################################################
hints:
  compiler:
    errors        : []                   # solc 에러 메시지 리스트
    warnings      : []                   # solc 경고 메시지 리스트
    bytecode_hash : ""                   # keccak(bytecode)
  static:
    slither:
      findings:                          # Slither 결과
        - id       : ""                  # detector ID
          severity : ""                  # "low"/"medium"/"high"
          location : ""                  # 함수명 또는 파일:line
  runtime:
    last_run_id     : ""                 # runlog[-1].run_id
    revert_selector : ""                 # 실제 revert selector
    decoded_logs    : []                 # console.log 또는 이벤트 메시지
    traces:
      root_fn        : ""                # 실패 발생 함수
      first_error_pc  : 0                 # EVM PC
  gas:
    used     : 0                         # 마지막 실행 gas
    snapshot : {}                       # label → gas

###############################################################################
# L3. PROMPT_CTX – LLM 호출용 실패 진단 컨텍스트
###############################################################################
prompt_ctx:
  include:
    - compiler.errors
    - runtime.revert_selector
    - runtime.decoded_logs
    - runtime.traces.root_fn
    - runtime.traces.first_error_pc
    - code.action.code
    - code.oracle.revert_selector
    - code.oracle.assertion_code
    - spec.precondition
    - spec.expected

  system_template: |
    You are a smart contract test analysis agent. A scenario-based test has failed.

    ### TASK ###
    Given the context below, analyze **why the test failed**, and determine whether:
    - (1) The test scenario is incorrectly defined
    - (2) The code under test behaves unexpectedly (i.e., a bug or unhandled case)
    - (3) The revert expectation/assertion is missing or incorrect

    Then:
    - Suggest a patch (e.g., add vm.expectRevert, fix the assertion)
    - Update the `expected_revert_selector` and/or `assertion_code` as needed
    - Comment clearly whether the test proves a real vulnerability, or a false alarm

    ### SPEC ###
    - Precondition: {{ spec.precondition }}
    - Action      : {{ spec.action }}
    - Expected    : {{ spec.expected }}

    ### ACTION CODE ###
    {{ code.action.code | truncate(300) }}

    ### EXPECTED ORACLE ###
    - expected_revert_selector: {{ code.oracle.revert_selector | default('None') }}
    - assertion_code: |
      {{ code.oracle.assertion_code | default('None') }}

    ### COMPILER ERRORS ###
    {{ hints.compiler.errors | join('; ') }}

    ### RUNTIME INFO ###
    - RevertSelector: {{ hints.runtime.revert_selector }}
    - DecodedLog    : {{ hints.runtime.decoded_logs[0] | default('None') }}
    - TraceRootFn   : {{ hints.runtime.traces.root_fn }}
    - FirstErrorPC  : {{ hints.runtime.traces.first_error_pc }}

    ### INSTRUCTIONS ###
    1. Write a one-line explanation of **why the test failed**.
    2. Suggest an updated `patch_suggestion` (in natural language or code diff).
    3. If applicable, suggest:
       - corrected `expected_revert_selector`
       - corrected `assertion_code`


###############################################################################
# L3. PATCHES – 코드/계획 수정 이력 (append-only)
###############################################################################
patches:
  - ts      : ""                       # ISO8601 timestamp
    author  : ""                       # "forge-runner" or human
    reason  : ""                       # 오류 원인 또는 요청
    diff    : |                        # json-patch 또는 @@ field @@ 형태
      ""

###############################################################################
# L3-HINTS – 
###############################################################################

###############################################################################
# L4. RUNLOG – 실행 결과 (append-only)
###############################################################################
runlog:
  - run_id            : ""             # 고유 ID
    ts                : ""             # ISO8601
    toolchain         : ""             # e.g. "forge 0.2.1 --ffi"
    status            : ""             # "success"/"failure"
    duration          : ""             # e.g. "628µs"
    vm_seed           : 0
    output_hash       : ""             # keccak(stdout)
    revert_selector   : ""             # 실패 시 selector
    gas_used          : 0
    diagnostics:
      counterexample:
        calldata      : ""             # raw calldata
      trace_root      : ""             # 실패 위치 함수
      decoded_logs    : []             # 리스트
    patch_suggestion  : |              # 다음 수정 제안
      ""

```