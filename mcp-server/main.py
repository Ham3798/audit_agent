################################################################################
# MCP 서버 전체 설명
################################################################################
#
# 이 MCP 서버는 시나리오 기반 스마트컨트랙트 보안 검증 자동화의 핵심 백엔드입니다.
#
# [역할 및 구조]
# - MCP는 시나리오(위협 모델) 등록, 수정, 실행, 테스트 코드 변경(diff) 기록 등
#   시나리오 중심의 검증 데이터 관리와 실행만을 담당합니다.
# - 모든 "추론"(시나리오 생성/수정/피드백/코드 diff 해석 등)은 LLM(상위 계층)이 담당하며,
#   MCP는 LLM이 넘겨준 dict(시나리오, 변경사항 등)를 그대로 DB에 저장/업데이트/로깅만 합니다.
# - MCP는 입력값의 의미 해석, 적합성 판단, 자동 보정/생성 등은 일절 하지 않습니다.
#
# [주요 툴 및 사용 흐름]
#
# 1. register_scenario(scenario: dict)
#    - LLM이 schema_1.0.yaml 구조에 맞게 추론한 시나리오 전체를 입력받아 신규 등록
#    - meta, spec, code 등 모든 필드를 LLM이 완성해야 하며, MCP는 단순 저장만 함
#
# 2. update_scenario(sid: str, update_dict: dict)
#    - LLM이 추론한 시나리오 변경사항(피드백 등)을 입력받아 해당 시나리오를 업데이트
#    - MCP는 단순히 DB에 반영만 하며, 의미 해석/적합성 판단은 하지 않음
#
# 3. execute_single_unit_test(sid, test_contract_name, foundry_root_path)
#    - DB에 등록된 시나리오만 대상으로 테스트 실행
#    - 시나리오가 없으면 에러 반환(자동 생성/수정/피드백 반영 X)
#
# 4. detect_test_code_diff(sid, test_contract_name, foundry_root_path)
#    - 테스트 코드(.t.sol) 변경(diff) 자체만 patch log에 기록
#    - diff의 의미 해석/정합성 판단/추론은 LLM이 담당
#
# [LLM과의 협업 구조]
# - LLM이 모든 시나리오 생성/수정/피드백/코드 diff 해석을 담당
# - MCP는 입력값을 그대로 저장/업데이트/로깅/실행만 담당(Stateless)
#
# [예시]
# - LLM이 schema_1.0.yaml 구조에 맞는 dict를 생성 → register_scenario로 등록
# - 피드백/수정이 필요하면 update_scenario로 변경사항 전달
# - 테스트 실행은 execute_single_unit_test로 요청
# - 테스트 코드가 변경되면 detect_test_code_diff로 diff 기록
#
# [참고]
# - 각 필드/입력 구조/예시는 schema_1.0.yaml 및 실제 시나리오 예시(D-3.1.yaml 등) 참고
#
################################################################################

################################################################################
# 0. imports & logger
################################################################################
import os, json, uuid, sqlite3, datetime, logging, subprocess, glob, yaml, difflib
from dataclasses import dataclass, asdict, field
from typing import Any, Dict, List, Optional

from mcp.server.fastmcp import FastMCP

logger = logging.getLogger("dyn-schema-mcp")
logger.setLevel(logging.INFO)
logger.handlers.clear()  # 기존 핸들러 제거
file_handler = logging.FileHandler("mcp-server.log")
file_handler.setLevel(logging.INFO)
logger.addHandler(file_handler)

mcp = FastMCP("dyn-schema-mcp")

# 시스템 설명 전체 텍스트를 상수로 정의
SYSTEM_CONTEXT_TEXT = """
[MCP 시스템 컨텍스트]
이 MCP 서버는 시나리오 기반 스마트컨트랙트 보안 검증 자동화의 핵심 백엔드입니다.

[역할 및 구조]
- MCP는 시나리오(위협 모델) 등록, 수정, 실행, 테스트 코드 변경(diff) 기록 등
  시나리오 중심의 검증 데이터 관리와 실행만을 담당합니다.
- 모든 "추론"(시나리오 생성/수정/피드백/코드 diff 해석 등)은 LLM(상위 계층)이 담당하며,
  MCP는 LLM이 넘겨준 dict(시나리오, 변경사항 등)를 그대로 DB에 저장/업데이트/로깅만 합니다.
- MCP는 입력값의 의미 해석, 적합성 판단, 자동 보정/생성 등은 일절 하지 않습니다.

[주요 툴 및 사용 흐름]
1. register_scenario(scenario: dict) - LLM이 schema_1.0.yaml 구조에 맞게 추론한 시나리오 전체를 입력받아 신규 등록
2. update_scenario(sid: str, update_dict: dict) - LLM이 추론한 시나리오 변경사항을 입력받아 업데이트
3. execute_single_unit_test(sid, test_contract_name, foundry_root_path) - DB에 등록된 시나리오 대상으로 테스트 실행
4. detect_test_code_diff(sid, test_contract_name, foundry_root_path) - 테스트 코드 변경을 patch log에 기록
5. analyze_test_results(sid, run_id, insights) - LLM이 테스트 실행 결과를 분석하여 추출한 인사이트를 저장
6. get_cumulative_insights(sid) - 특정 시나리오에 대해 누적된 테스트 분석 인사이트 조회

[LLM과의 협업 구조]
- LLM이 모든 시나리오 생성/수정/피드백/코드 diff 해석을 담당
- MCP는 입력값을 그대로 저장/업데이트/로깅/실행만 담당(Stateless)
- LLM은 테스트 실행 결과를 분석하여 유용한 정보(상태 변화, 조건부 행동 패턴 등)를 추출하고, 
  이를 누적하여 시나리오 검증과 개선에 활용합니다.
"""

# 시나리오 필드 설명 상수 정의
SCENARIO_FIELDS_DESCRIPTION = """
[필드별 상세 설명 및 예시]
meta: 시나리오의 식별, 분류, 작성자 등 메타데이터
  - id: "D_3_1"
  - title: "Hook Revert DoS (BeforeSwap): beforeSwap 훅이 revert하여 swap 방해"
  - category: "Denial of Service"
  - severity: "medium"
  - tags: []
  - author: "llm-auto"
  - created: "2024-06-10T12:00:00Z"

spec: 위협 시나리오의 행위자, 자산, 동작, 기대 결과 등 논리적/행위적 설명
  - description: "PoolKey에 설정된 훅의 beforeSwap 함수가 항상 revert하도록 설정"
  - actors: [{"id": "user", "role": "EOA user", "trust_level": "untrusted"}]
  - assets: [{"name": "Hook", "type": "address", "critical": true}]
  - components: [{"name": "PoolManager", "type": "contract", "deployed_at": ""}]
  - trust_boundaries: [{"from": "user", "to": "PoolManager", "enforcement": "msg.sender check"}]
  - data_flows: [{"source": "user", "target": "PoolManager", "function": "swap", "params": [{"name": "key", "value": "reverting"}, ...]}]
  - behaviors: [{"actor": "user", "action": "calls swap with reverting beforeSwap hook"}]
  - precondition: "PoolKey에 설정된 훅의 beforeSwap 함수가 항상 revert하도록 설정"
  - action: "targetContract.swap(key, params, hookData); // Via Unlock"
  - expected: "vm.expectRevert(Hooks.HookCallFailed.selector)"

code: 실제 테스트 코드/컨텍스트 생성 정보
  - compiler_version: "^0.8.24"
  - target_contract_name: "PoolManager"
  - target_contract_declaration: "PoolManager internal _targetContract; ..."
  - target_contract_instance_name: "_targetContract"
  - required_imports: ["import { PoolManager } from 'src/PoolManager.sol';", ...]
  - setup_code: "token0 = new TestERC20(1e27); ..."
  - test_setup_code: "key = PoolKey({ ... }); ..."
  - action_function: null 또는 "swap"
  - action_code: "// Use the callback instance ..."
  - expected_revert_selector: "Hooks.HookCallFailed.selector"
  - assertion_code: null
  - helper_contracts: [{"name": "RevertingHook", ...}, ...]
"""

################################################################################
# 1.  데이터 모델 (유동 필드 허용)
################################################################################
@dataclass
class ScenarioDoc:
    """전체 YAML 을 JSON 으로 파싱 후 보관 + 최소 PK(id)만 강제."""

    meta: Dict[str, Any] = field(default_factory=dict)
    spec: Dict[str, Any] = field(default_factory=dict)
    code: Dict[str, Any] = field(default_factory=dict)
    hints: Dict[str, Any] = field(default_factory=dict)
    prompt_ctx: Dict[str, Any] = field(default_factory=dict)
    patches: List[Dict[str, Any]] = field(default_factory=list)
    runlog: List[Dict[str, Any]] = field(default_factory=list)
    extras: Dict[str, Any] = field(default_factory=dict)  # 미래 섹션
    test_insights: List[Dict[str, Any]] = field(default_factory=list)  # 테스트 결과에서 LLM이 추출한 인사이트 저장

    # --- util ---------------------------------------------------------------
    @property
    def id(self) -> str:
        return self.meta.get("id", "")

    def to_json(self) -> str:
        return json.dumps(asdict(self))

    @staticmethod
    def from_json(js: str) -> "ScenarioDoc":
        data = json.loads(js)
        from dataclasses import fields
        field_names = {f.name for f in fields(ScenarioDoc)}
        for fname in field_names:
            if fname not in data:
                if fname in ["patches", "runlog"]:
                    data[fname] = []
                else:
                    data[fname] = {}
        return ScenarioDoc(**data)

    def add_run_log(self, run_id: str, status: str, diff: str, stdout: str = "", stderr: str = ""):
        """시나리오에 실행 로그 추가"""
        log_entry = {
            "run_id": run_id,
            "ts": datetime.datetime.utcnow().isoformat(),
            "status": status,
            "diff": diff,
            "stdout": stdout[:4000] if stdout else "",  # 로그 크기 제한
            "stderr": stderr[:4000] if stderr else ""   # 로그 크기 제한
        }
        self.runlog.append(log_entry)

    def add_patch(self, author: str, reason: str, diff_text: str):
        """시나리오에 코드 변경 패치 추가"""
        patch_entry = {
            "ts": datetime.datetime.utcnow().isoformat(),
            "author": author,
            "reason": reason,
            "diff": diff_text
        }
        self.patches.append(patch_entry)

    def add_test_insight(self, run_id: str, insight: Dict[str, Any]):
        """
        LLM이 테스트 실행 결과에서 추출한 통찰력/인사이트를 저장합니다.
        
        - run_id: 테스트 실행 ID
        - insight: 인사이트 정보 딕셔너리, 다음 필드 포함 가능:
          - precondition: 테스트의 전제 조건 (예: "reverting hook 설정 시")
          - state_changes: 관찰된 상태 변화 (예: "pool.liquidity 값이 0으로 유지됨")
          - patterns: 감지된 패턴 (예: "특정 주소로부터의 호출만 revert됨")
          - security_implications: 보안 영향 (예: "hook이 항상 revert하면 사용자는 swap 불가")
          - additional_info: 추가 정보 (예: 패턴, 가설 등)
          - confidence: 인사이트의 신뢰도 (0-1 범위의 값)
        """
        # 타임스탬프 추가
        insight["ts"] = datetime.datetime.utcnow().isoformat()
        insight["run_id"] = run_id
        
        # 동일 run_id에 대한 기존 인사이트가 있으면 업데이트, 없으면 추가
        updated = False
        for i, existing in enumerate(self.test_insights):
            if existing.get("run_id") == run_id:
                self.test_insights[i] = insight
                updated = True
                break
        
        if not updated:
            self.test_insights.append(insight)

    def get_cumulative_insights(self) -> List[Dict[str, Any]]:
        """
        시나리오에 대해 저장된 모든 인사이트를 시간순으로 반환합니다.
        이를 통해 LLM은 해당 시나리오에 대해 발견된 모든 패턴과 정보를 종합적으로 분석할 수 있습니다.
        """
        # 타임스탬프 기준 정렬 (최신순)
        return sorted(self.test_insights, key=lambda x: x.get("ts", ""), reverse=True)

    def update_hints_from_run(self, run_id: str, status: str, stdout: str, stderr: str):
        """실행 결과를 바탕으로 hints 업데이트"""
        self.hints.setdefault("runtime", {})["last_run_id"] = run_id
        self.hints["runtime"]["last_run_status"] = status
        
        # stdout, stderr 파싱하여 hints 채우기
        decoded_logs = []
        for line in stdout.splitlines():
            if "CONSOLE:" in line: # forge test -vvv 이상에서 CONSOLE: 접두사로 출력
                log_content = line.split("CONSOLE:", 1)[1].strip()
                decoded_logs.append(log_content)
            # Event 로그 파싱 (이벤트 탐지)
            elif "emit" in line.lower():
                decoded_logs.append(f"EVENT: {line.strip()}")
            # Gas 사용량 탐지
            elif "gas" in line.lower() and "used" in line.lower():
                self.hints.setdefault("gas", {})["used"] = line.strip()
        
        if decoded_logs:
            self.hints["runtime"].setdefault("decoded_logs", []).extend(decoded_logs)
            # 중복 제거 (집합으로 변환 후 다시 리스트로)
            self.hints["runtime"]["decoded_logs"] = list(set(self.hints["runtime"]["decoded_logs"]))
        
        # Revert 정보 파싱
        if "Reverted" in stderr:
            revert_lines = [line for line in stderr.splitlines() if "Reverted" in line]
            if revert_lines:
                self.hints.setdefault("runtime", {})["revert_info"] = revert_lines[0]
        
        # 컴파일러 에러/경고 수집
        if "Error:" in stderr or "Warning:" in stderr:
            error_lines = [line for line in stderr.splitlines() 
                          if "Error:" in line or "Warning:" in line]
            if error_lines:
                self.hints.setdefault("compiler", {}).setdefault("errors", []).extend(error_lines[:5])

################################################################################
# 2.  SQLite Tool
################################################################################
_DB = os.getenv("SCENARIO_DB", "scenario_dyn.db")
with sqlite3.connect(_DB) as c:
    c.execute("""CREATE TABLE IF NOT EXISTS scenario
                 (id TEXT PRIMARY KEY, json TEXT NOT NULL)""")
    c.execute("""CREATE TABLE IF NOT EXISTS runlog
                 (run_id TEXT PRIMARY KEY, scenario_id TEXT, ts TEXT,
                  status TEXT, diff TEXT, stdout TEXT, stderr TEXT)""")

def _conn():
    cx = sqlite3.connect(_DB)
    cx.row_factory = sqlite3.Row
    return cx

# CRUD helpers --------------------------------------------------------------
def save_scenario(doc: ScenarioDoc):
    if not doc.id:
        raise ValueError("meta.id is required")
    # 저장 전 누락 필드 보완
    doc_json = doc.to_json()
    doc = ScenarioDoc.from_json(doc_json)
    with _conn() as c:
        c.execute("INSERT OR REPLACE INTO scenario VALUES (?,?)",
                  (doc.id, doc.to_json()))

def load_scenario(sid: str) -> Optional[ScenarioDoc]:
    row = _conn().execute("SELECT json FROM scenario WHERE id=?", (sid,)).fetchone()
    if row:
        return ScenarioDoc.from_json(row["json"])
    return None

def update_scenario_partial(sid: str, update_dict: dict):
    doc = load_scenario(sid)
    if not doc:
        raise ValueError("해당 시나리오가 없습니다.")
    doc_dict = asdict(doc)
    for k, v in update_dict.items():
        doc_dict[k] = v
    doc_json = json.dumps(doc_dict)
    doc = ScenarioDoc.from_json(doc_json)
    save_scenario(doc)

def delete_scenario(sid: str):
    with _conn() as c:
        c.execute("DELETE FROM scenario WHERE id=?", (sid,))

def list_ids() -> List[str]:
    return [r["id"] for r in _conn().execute("SELECT id FROM scenario")]

def add_runlog_entry(sid: str, status: str, diff: str,
            stdout: str = "", stderr: str = ""):
    run_id = str(uuid.uuid4())
    with _conn() as c:
        c.execute("""INSERT INTO runlog VALUES (?,?,?,?,?,?,?)""",
                  (run_id, sid,
                   datetime.datetime.utcnow().isoformat(),
                   status, diff, stdout[:8000], stderr[:8000]))
    
    # 시나리오 문서에도 로그 추가
    doc = load_scenario(sid)
    if doc:
        doc.add_run_log(run_id, status, diff, stdout, stderr)
        save_scenario(doc)
    
    return run_id

################################################################################
# 3.  MCP tools (DB 기반 시나리오 관리, YAML은 import/export 용도만)
################################################################################

@mcp.tool()
async def get_scenario(sid: str) -> Dict[str, Any]:
    """
    [MCP 시스템 컨텍스트]
    DB에서 특정 시나리오의 전체 정보를 JSON 형태로 반환하며, 이는 시나리오 기반 검증 및 분석에 사용됩니다.
    """
    logger.info(f"[get_scenario] 호출: {sid}")
    doc = load_scenario(sid)
    return json.loads(doc.to_json()) if doc else {}

@mcp.tool()
async def list_scenarios() -> List[str]:
    """
    [MCP 시스템 컨텍스트]
    DB에 저장된 모든 시나리오의 ID 목록을 반환하여, 사용자가 검증 대상을 선택하거나 전체 시나리오 현황을 파악하는 데 도움을 줍니다.
    """
    logger.info(f"[list_scenarios] 호출")
    return list_ids()

@mcp.tool()
def export_scenario_to_yaml(sid: str, path: str) -> str:
    """
    [MCP 시스템 컨텍스트]
    DB에 저장된 특정 시나리오를 YAML 파일 형태로 내보냅니다. 이는 시나리오의 외부 공유나 백업 목적으로 사용될 수 있지만, 감사 중에는 DB를 기준으로 작업해야 합니다.
    """
    doc = load_scenario(sid)
    if not doc:
        raise ValueError("해당 시나리오가 없습니다.")
    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(json.loads(doc.to_json()), f, allow_unicode=True)
    logger.info(f"시나리오 {sid}를 {path}로 export 완료")
    return f"exported {sid} to {path}"

################################################################################
# 4.  스키마-버전 필드 초기 캡처 (YAML → DB 부트스트랩만 허용)
################################################################################

@mcp.tool()
async def bootstrap_from_yaml_files(folder="scenarios"):
    """
    [MCP 시스템 컨텍스트]
    지정된 폴더 내의 YAML 파일들을 읽어와 각 시나리오 정보를 DB에 일괄적으로 저장합니다.
    주로 시스템 초기 설정이나 대량의 시나리오를 마이그레이션할 때 사용하며, 이후에는 DB를 통해 시나리오를 관리해야 합니다.
    """
    import glob as glob_module
    success, failed = [], []
    for fp in glob_module.glob(os.path.join(folder, "*.yaml")):
        try:
            with open(fp, "r") as f:
                raw = yaml.safe_load(f)
            doc = ScenarioDoc.from_json(json.dumps(raw))
            save_scenario(doc)
            success.append(os.path.basename(fp))
        except Exception as e:
            logger.error(f"bootstrap error: {fp} - {e}")
            failed.append({"file": os.path.basename(fp), "error": str(e)})
    logger.info(f"bootstrap complete: {len(success)} success, {len(failed)} failed")
    return {
        "success_count": len(success),
        "failed_count": len(failed),
        "success_files": success,
        "failed_files": failed
    }

################################################################################
# 5.  MCP Foundry/UnitTest/ScenarioValidation 도구 클래스 구조
################################################################################

class FoundryTool:
    """
    Foundry 관련 도구: 컴파일, 유닛테스트 실행, forge 로그 수집
    """

    def runUnitTest(self, test_contract_name=None, foundry_root_path=None, sid=None):
        """유닛테스트 실행 및 결과를 runlog에 자동 저장 (foundry_root_path: 테스트 파일이 위치한 디렉토리 경로)"""
        try:
            cmd = ["forge", "test", "-vvv"]
            if test_contract_name:
                cmd.extend(["--match-contract", test_contract_name])
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=foundry_root_path if foundry_root_path else None
            )
            success = result.returncode == 0
            status = "SUCCESS" if success else "TEST_FAILURE"
            diff = f"runUnitTest 실행: {test_contract_name if test_contract_name else ''}"
            if sid:
                add_runlog_entry(sid, status, diff, result.stdout, result.stderr)
            return success, result.stdout, result.stderr
        except Exception as e:
            logger.error(f"테스트 실행 오류: {e}")
            if sid:
                add_runlog_entry(sid, "ERROR", "runUnitTest 실행 중 오류", "", str(e))
            return False, "", str(e)

    def collectForgeLogs(self, sid=None):
        """실행 로그를 DB(runlog) 또는 시나리오 객체의 runlog에서 수집"""
        try:
            if sid:
                doc = load_scenario(sid)
                if doc and doc.runlog:
                    # 최신 실행 로그 반환
                    return doc.runlog[-1]
                else:
                    return "해당 시나리오의 실행 로그가 없습니다."
            else:
                cx = _conn()
                row = cx.execute("SELECT * FROM runlog ORDER BY ts DESC LIMIT 1").fetchone()
                return dict(row) if row else "실행 로그가 없습니다."
        except Exception as e:
            logger.error(f"로그 수집 오류: {e}")
            return f"로그 수집 오류: {str(e)}"

class UnitTestGenTool:
    """
    시나리오 spec 기반 테스트 코드 생성 도구
    """
    def __init__(self):
        self.template = """// SPDX-License-Identifier: UNLICENSED
// Generated by Audit Agent for Scenario: {{ scenario.id }}
pragma solidity {{ compiler_version | default('^0.8.24') }};

import "forge-std/Test.sol";
{%- if scenario.required_imports %}
// Scenario-specific imports:
{% for imp in scenario.required_imports %}{{ imp }}
{% endfor %}
{%- endif %}

{% for helper in helper_contracts %}
{{ helper.definition_code }}
{% endfor %}

contract {{ test_contract_name }} is Test {
    // --- State Variables ---
    // Target contract instance (filled by generator)
    {{ target_contract_declaration }} // 예: TargetContract internal targetContract;

    // Mock contract instances (filled by generator)
    {% if scenario.mock_deployments_code -%}
    {{ scenario.mock_deployments_code | indent(4) }}
    {%- endif %}

    // --- Setup ---
    function setUp() public {
        // General setup logic (filled by generator)
        {% if scenario.setup_code -%}
        {{ scenario.setup_code | indent(8) }}
        {%- else -%}
        // Default setup: Deploy target contract?
        // targetContract = new TargetContract();
        {%- endif %}
        
        console.log("Executing setUp for {{ test_contract_name }}");
    }

    // --- Test Function ---
    // MCP Test for Scenario: {{ scenario.id }} - {{ scenario.category }}
    // Description: {{ scenario.description }}
    function test_{{ scenario_id_snake_case }}() public {
        console.log(unicode"Scenario: {{ scenario.id }} - Precondition: {{ scenario.precondition }}");

        // --- Test Specific Setup ---
        {% if scenario.test_setup_code -%}
        {{ scenario.test_setup_code | indent(8) }}
        {%- else -%}
        // No specific test setup provided for this scenario.
        {%- endif %}
        
        console.log("Applying test-specific setup for {{ scenario.id }}...");

        // --- Execution & Assertion ---
        console.log("Action: {{ scenario.action }}"); // 설명용
        console.log("Expected: {{ scenario.expected }}"); // 설명용

        {% if scenario.expected_revert_selector -%}
        // Expect Revert
        vm.expectRevert({{ scenario.expected_revert_selector }});
        {% endif -%}

        // Execute the action (filled by generator)
        {% if scenario.action_code -%}
        {{ scenario.action_code | indent(8) }}
        {%- else -%}
        // Placeholder: Execute the action described in scenario.action
        // Example: {{ target_contract_instance_name | default('targetContract') }}.{{ scenario.action_function | default('someAction') }}(...);\n",
        {%- endif %}
        
        console.log("Executing action for {{ scenario.id }}...");

        {% if not scenario.expected_revert_selector and scenario.assertion_code -%}
        // Assert State Changes (filled by generator)
        {{ scenario.assertion_code | indent(8) }}
        {%- elif not scenario.expected_revert_selector -%}
        // Default assertion if no specific assertion code is provided and no revert is expected
        assertTrue(true, "Execution completed without revert (no specific assertions)");
        {%- endif %}
    }
}
"""
    def generateTestCode(self, spec: dict):
        """테스트 코드 생성"""
        import re
        from jinja2 import Template
        
        test_contract_name = sid_to_contract_name(spec['meta']['id'])
        scenario_id_snake_case = re.sub(r'[^a-zA-Z0-9_]', '_', spec['meta']['id']).lower()
        
        # code 섹션을 scenario에 통합
        scenario = {**spec['meta'], **spec['code']}
        scenario['description'] = spec['spec']['description']
        scenario['precondition'] = spec['spec'].get('precondition', '')
        scenario['action'] = spec['spec'].get('action', '')
        scenario['expected'] = spec['spec'].get('expected', '')
        
        context = {
            "scenario": scenario,
            "test_contract_name": test_contract_name.replace('.t.sol',''),
            "scenario_id_snake_case": scenario_id_snake_case,
            "compiler_version": scenario.get("compiler_version", "^0.8.24"),
            "target_contract_declaration": scenario.get("target_contract_declaration", "// Target contract declaration missing"),
            "target_contract_instance_name": scenario.get("target_contract_instance_name", "targetContract"),
            "helper_contracts": scenario.get("helper_contracts", []),
        }
        
        template = Template(self.template, trim_blocks=True, lstrip_blocks=True)
        rendered_code = template.render(context)
        filename = test_contract_name
        
        logger.info(f"생성된 테스트 코드 파일: {filename}")
        return filename, rendered_code

class ScenarioValidationTool:
    """
    시나리오와 forge 로그 기반 검증 도구
    """
    def buildValidationPrompt(self, scenarioInfo: dict, forgeLogs: str):
        """검증용 프롬프트 생성"""
        prompt = f"""
시나리오 ID: {scenarioInfo['meta']['id']}
카테고리: {scenarioInfo['meta']['category']}
설명: {scenarioInfo['spec']['description']}
전제조건: {scenarioInfo['spec'].get('precondition', '')}
수행동작: {scenarioInfo['spec'].get('action', '')}
기대결과: {scenarioInfo['spec'].get('expected', '')}

Forge 테스트 결과 로그:
{forgeLogs[:2000]}...  # 로그가 너무 긴 경우 일부만 포함

위 시나리오와 테스트 결과를 분석하여 다음을 판단해주세요:
1. 테스트가 성공적으로 실행되었는가?
2. 시나리오의 기대 결과와 실제 결과가 일치하는가?
3. 보안 취약점이 효과적으로 검증되었는가?
4. 개선이 필요한 부분이 있다면 무엇인가?
"""
        return prompt

    def runValidation(self, unittest_path: str):
        """unittest(.t.sol) 실행 및 검증"""
        try:
            # Forge 테스트 실행
            forge_tool = FoundryTool()
            test_contract_name = os.path.basename(unittest_path).replace(".t.sol", "")
            success, stdout, stderr = forge_tool.runUnitTest(test_contract_name)
            
            # 결과 분석
            if success:
                return "SUCCESS", "테스트가 성공적으로 실행되었습니다.", stdout, stderr
            else:
                return "FAILURE", "테스트 실행 중 오류가 발생했습니다.", stdout, stderr
        except Exception as e:
            logger.error(f"검증 실행 오류: {e}")
            return "ERROR", f"검증 과정에서 오류 발생: {str(e)}", "", str(e)

class SchemaAnalysisTool:
    """
    스키마 파일 분석 및 정보 추출 도구
    """
    def loadSchemaFile(self, schema_path: str = "mcp-server/schemas/schema_1.0.yaml") -> Dict[str, Any]:
        """스키마 파일을 로드하고 구조를 분석"""
        try:
            with open(schema_path, "r") as f:
                schema_data = yaml.safe_load(f)
            
            logger.info(f"스키마 파일 로드 성공: {schema_path}")
            return {
                "success": True,
                "schema_version": schema_data.get("schema_version", "unknown"),
                "structure": {
                    "meta": self._extractFieldInfo(schema_data.get("meta", {})),
                    "spec": self._extractFieldInfo(schema_data.get("spec", {})),
                    "gen_prompt": self._extractFieldInfo(schema_data.get("gen_prompt", {})),
                    "code": self._extractFieldInfo(schema_data.get("code", {})),
                    "hints": self._extractFieldInfo(schema_data.get("hints", {})),
                    "prompt_ctx": self._extractFieldInfo(schema_data.get("prompt_ctx", {})),
                    "patches": self._extractFieldInfo(schema_data.get("patches", [])),
                    "runlog": self._extractFieldInfo(schema_data.get("runlog", []))
                },
                "schema_data": schema_data  # 전체 스키마 데이터
            }
        except Exception as e:
            logger.error(f"스키마 파일 로드 오류: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _extractFieldInfo(self, section):
        """스키마 섹션의 필드 정보 추출"""
        if isinstance(section, dict):
            return {k: self._getFieldType(v) for k, v in section.items()}
        elif isinstance(section, list) and section and isinstance(section[0], dict):
            # 리스트 안의 첫 항목으로 구조 추정
            return [self._extractFieldInfo(section[0])]
        else:
            return type(section).__name__
    
    def _getFieldType(self, value):
        """값의 타입 정보 추출"""
        if isinstance(value, dict):
            return {k: self._getFieldType(v) for k, v in value.items()}
        elif isinstance(value, list):
            if value and all(isinstance(x, dict) for x in value):
                return [self._getFieldType(value[0])]
            else:
                return "list"
        else:
            return type(value).__name__

    def validateScenario(self, scenario: Dict[str, Any], schema_path: str = "mcp-server/schemas/schema_1.0.yaml") -> Dict[str, Any]:
        """시나리오가 스키마에 맞는지 검증"""
        schema_info = self.loadSchemaFile(schema_path)
        if not schema_info.get("success", False):
            return {
                "valid": False,
                "errors": [f"스키마 로드 실패: {schema_info.get('error')}"]
            }
        
        errors = []
        
        # 필수 필드 검증
        if "meta" not in scenario:
            errors.append("필수 섹션 'meta'가 없습니다.")
        elif "id" not in scenario["meta"]:
            errors.append("필수 필드 'meta.id'가 없습니다.")
        
        if "spec" not in scenario:
            errors.append("필수 섹션 'spec'가 없습니다.")
        elif "description" not in scenario["spec"]:
            errors.append("필수 필드 'spec.description'이 없습니다.")
        
        # spec 하위 필수 필드 검증
        if "spec" in scenario:
            spec = scenario["spec"]
            for field in ["actors", "assets", "components", "trust_boundaries", "data_flows", "behaviors"]:
                if field not in spec or not isinstance(spec[field], list):
                    errors.append(f"필수 필드 'spec.{field}' 배열이 없거나 잘못되었습니다.")
            
            for field in ["precondition", "action", "expected"]:
                if field not in spec or not spec[field]:
                    errors.append(f"필수 필드 'spec.{field}'가 없거나 비어 있습니다.")
        
        # code 섹션 검증 (코드 생성에 필요한 필드)
        if "code" in scenario:
            code = scenario["code"]
            if "target_contract_name" not in code or not code["target_contract_name"]:
                errors.append("코드 생성을 위한 'code.target_contract_name'이 없거나 비어 있습니다.")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "schema_version": schema_info.get("schema_version", "unknown")
        }

# === sid → 컨트랙트/테스트 파일명 변환 함수 추가 ===
def sid_to_contract_name(sid: str) -> str:
    """
    시나리오 ID(sid)를 기반으로 유효한 Solidity 컨트랙트 이름을 생성합니다.
    예: D_3_1 → D_3_1.t.sol
    """
    return f"{sid}.t.sol"

class LocalMCPServer:
    """
    MCP 서버: 시나리오 처리 및 도구 디스패치
    FoundryTool, UnitTestGenTool, ScenarioValidationTool을 활용
    """
    
    def __init__(self):
        self.foundry_tool = FoundryTool()
        self.unittest_gen_tool = UnitTestGenTool()
        self.validation_tool = ScenarioValidationTool()
        self.schema_tool = SchemaAnalysisTool()

    # --- 유닛테스트 실행용 메서드 ---
    def process_single_scenario_test(self, sid: str, test_contract_name: str, foundry_root_path: str):
        """
        단일 시나리오 단위 테스트 실행 및 결과 기록 (모든 도구 호출을 dispatchTool로 통일)
        """
        doc = load_scenario(sid)
        if not doc:
            return {
                "success": False,
                "message": f"시나리오 {sid}를 찾을 수 없습니다.",
                "stdout": "",
                "stderr": "Scenario not found"
            }
        # 1. 현재 테스트 코드 읽기
        test_file_relative_path = os.path.join("test", "generated", sid_to_contract_name(sid))
        test_file_full_path = os.path.join(foundry_root_path, test_file_relative_path)
        current_code = ""
        try:
            with open(test_file_full_path, "r", encoding="utf-8") as f:
                current_code = f.read()
        except FileNotFoundError:
            logger.error(f"테스트 파일 {test_file_full_path}를 찾을 수 없습니다.")
            pass
        doc.code.setdefault("test_code_snapshots", {})
        last_known_code = doc.code["test_code_snapshots"].get(test_contract_name, "")
        if last_known_code != current_code:
            import difflib
            diff_text = "\n".join(difflib.unified_diff(
                last_known_code.splitlines(),
                current_code.splitlines(),
                fromfile=f"previous_{test_contract_name}",
                tofile=f"current_{test_contract_name}",
                lineterm="\n"
            ))
            if diff_text:
                doc.add_patch(
                    author="system-auto-detect",
                    reason=f"Code for {test_contract_name} changed since last run.",
                    diff_text=diff_text
                )
            doc.code["test_code_snapshots"][test_contract_name] = current_code
        # 3. 유닛테스트 실행 (dispatchTool 사용)
        contract_name = test_contract_name.replace('.t.sol','')
        test_result = self.dispatchTool("test", test_contract_name=contract_name, foundry_root_path=foundry_root_path, sid=None)
        success, stdout, stderr = test_result if isinstance(test_result, tuple) else (False, "", "")
        # 4. runlog 기록
        status = "SUCCESS" if success else "TEST_FAILURE"
        diff_for_runlog = f"[{sid}] process_single_scenario_test 실행: {contract_name}"
        run_id = add_runlog_entry(sid, status, diff_for_runlog, stdout, stderr)
        # 5. hints 업데이트
        doc.update_hints_from_run(run_id, status, stdout, stderr)
        save_scenario(doc)
        return {
            "success": success,
            "stdout": stdout,
            "stderr": stderr,
            "run_id": run_id
        }

    # --- 도구 디스패치 ---
    def dispatchTool(self, toolName: str, **kwargs):
        """도구 이름에 따라 해당 도구 실행"""
        tools = {
            # Foundry 도구
            "test": self.foundry_tool.runUnitTest,
            "logs": self.foundry_tool.collectForgeLogs,
            # 테스트 생성 및 검증 도구
            "generate": self.unittest_gen_tool.generateTestCode,
            "validate": self.validation_tool.runValidation,
            # 스키마 분석 도구
            "analyze_schema": self.schema_tool.loadSchemaFile,
            "validate_schema": self.schema_tool.validateScenario,
            "create_template": self.createScenarioTemplate,
            "extract_hints": self.extractHintsFromResults,
            "validate_scenario": self.validateScenarioAgainstSchema,
            # 통합 시나리오 처리
            "process_single_scenario_test": self.process_single_scenario_test
        }
        if toolName not in tools:
            return {
                "status": "ERROR",
                "message": f"알 수 없는 도구: {toolName}"
            }
        try:
            result = tools[toolName](**kwargs)
            # runlog에 기록
            sid = kwargs.get("sid", None)
            if sid and isinstance(result, dict) and "status" in result:
                status = result.get("status", "UNKNOWN")
                message = result.get("message", "")
                stdout = result.get("stdout", "")
                stderr = result.get("stderr", "")
                diff = f"{toolName} 실행: {message}"
                add_runlog_entry(sid, status, diff, stdout, stderr)
            return result
        except Exception as e:
            logger.error(f"{toolName} 도구 실행 오류: {e}")
            # runlog에 기록
            sid = kwargs.get("sid", None)
            if sid:
                diff = f"{toolName} 도구 실행 중 오류 발생"
                add_runlog_entry(sid, "ERROR", diff, "", str(e))
            return {
                "status": "ERROR",
                "message": f"{toolName} 도구 실행 중 오류 발생: {str(e)}"
            }

    # --- 시나리오 스키마 관련 기능 ---
    def createScenarioTemplate(self):
        """새로운 시나리오 템플릿 생성"""
        return self.schema_tool.createScenarioTemplate()
    
    def extractHintsFromResults(self, scenario_id: str, forge_output: str, slither_output: str = None):
        """테스트 결과에서 힌트 추출하여 시나리오 업데이트"""
        try:
            # 시나리오 로드
            scenario_doc = load_scenario(scenario_id)
            if not scenario_doc:
                return {
                    "success": False,
                    "message": f"시나리오 ID '{scenario_id}'를 찾을 수 없습니다."
                }
            
            # JSON으로 변환
            scenario_data = json.loads(scenario_doc.to_json())
            
            # 힌트 추출 및 업데이트
            updated_scenario = self.schema_tool.extractHintsFromResults(scenario_data, forge_output, slither_output)
            
            # 업데이트된 시나리오 저장
            updated_doc = ScenarioDoc.from_json(json.dumps(updated_scenario))
            save_scenario(updated_doc)
            
            return {
                "success": True,
                "message": f"시나리오 '{scenario_id}'의 힌트가 업데이트되었습니다."
            }
        except Exception as e:
            logger.error(f"힌트 추출 중 오류 발생: {e}")
            return {
                "success": False,
                "message": f"힌트 추출 중 오류 발생: {str(e)}"
            }
    
    def validateScenarioAgainstSchema(self, scenario_id: str):
        """시나리오가 스키마에 맞는지 검증"""
        try:
            # 시나리오 로드
            scenario_doc = load_scenario(scenario_id)
            if not scenario_doc:
                return {
                    "valid": False,
                    "errors": [f"시나리오 ID '{scenario_id}'를 찾을 수 없습니다."]
                }
            
            # JSON으로 변환
            scenario_data = json.loads(scenario_doc.to_json())
            
            # 스키마 검증
            validation_result = self.schema_tool.validateScenario(scenario_data)
            
            return validation_result
        except Exception as e:
            logger.error(f"스키마 검증 중 오류 발생: {e}")
            return {
                "valid": False,
                "errors": [f"스키마 검증 중 오류 발생: {str(e)}"]
            }

@mcp.tool()
async def scenario_context(sid: str, test_contract_name: str, foundry_root_path: str) -> Dict[str, Any]:
    """
    [MCP 시스템 컨텍스트]
    주어진 시나리오 ID(sid)에 해당하는 테스트 시나리오가 DB에 존재하는지 확인합니다.
    존재하면 해당 시나리오의 모든 정보(메타데이터, 스펙, 코드 조각, 힌트, 실행 로그 등)를 컨텍스트로 반환합니다.
    존재하지 않으면 빈 dict를 반환합니다.
    - sid: 시나리오 ID (예: "D-3-1")
    - test_contract_name: 테스트 컨트랙트 이름 (예: "MCPTest_D_3_1")
    - foundry_root_path: Foundry 프로젝트 디렉토리 경로 (예: "/foundry_project")
    """
    logger.info(f"[scenario_context] 호출: sid={sid}, test_contract_name={test_contract_name}, foundry_root_path={foundry_root_path}")
    doc = load_scenario(sid)
    if doc:
        logger.info(f"시나리오 {sid} 발견. 컨텍스트 반환.")
        return json.loads(doc.to_json())
    else:
        logger.info(f"시나리오 {sid} 없음. 빈 dict 반환.")
        return {}

@mcp.tool()
async def execute_single_unit_test(sid: str, test_contract_name: str, foundry_root_path: str):
    """
    [MCP 시스템 컨텍스트]
    지정된 시나리오 ID에 해당하는 Foundry 유닛 테스트를 실행하고, 그 결과를 DB의 runlog에 기록합니다.
    이를 통해 특정 시나리오의 검증을 자동화하고, 실행 이력을 관리할 수 있습니다.
    - sid: 시나리오 ID (실행 로그 기록용)
      
    - test_contract_name: 테스트 컨트랙트 이름 (예: MCPTest_S_1_1)
    - foundry_root_path: foundry 프로젝트 디렉토리 경로 (예: /foundry_project)

    [중요] sid는 반드시 언더스코어(_)로 변환된 형태로 입력해야 합니다.
    예시:
      올바른 예시:   { "sid": "D_3_1", "test_contract_name": "MCPTest_D_3_1", ... }
      잘못된 예시:   { "sid": "D-3-1", "test_contract_name": "MCPTest_D_3_1", ... }
    (즉, sid에 하이픈(-)이나 점(.)이 포함된 경우 모두 언더스코어(_)로 변환해서 요청해야 합니다.)
    """
    doc = load_scenario(sid)
    if not doc:
        return {"error": f"시나리오 {sid}가 DB에 존재하지 않습니다. 먼저 시나리오를 등록하세요."}
    else:
        return local_server.dispatchTool(
            "process_single_scenario_test",
            sid=sid,
            test_contract_name=test_contract_name,
            foundry_root_path=foundry_root_path
        )

@mcp.tool()
async def get_unit_test_logs(sid: str) -> list:
    """
    [MCP 시스템 컨텍스트]
    단일 유닛테스트의 실행 결과(runlog) 기록들을 조회하는 툴.
    sid(시나리오ID)를 받아 해당 runlog를 반환합니다.
    """
    doc = load_scenario(sid)
    if not doc:
        return {"error": f"시나리오 {sid}를 찾을 수 없습니다."}
    return doc.runlog

@mcp.tool()
def register_scenario(scenario: dict) -> dict:
    """
    [MCP 시스템 컨텍스트]
    [LLM ONLY] 신규 위협 시나리오를 등록하는 툴입니다.
    - 입력값은 반드시 schema_1.0.yaml의 구조(meta, spec, code, hints, prompt_ctx, patches, runlog, extras 등)를 모두 포함해야 하며,
      LLM이 모든 필드를 추론하여 완성해야 합니다.
    - MCP는 입력값을 그대로 DB에 등록만 하며, 자동 추론/보정은 하지 않습니다.
    - meta.id는 반드시 고유해야 하며, 이미 등록된 id는 에러가 발생합니다.
    - 모든 필드는 schema_1.0.yaml의 타입/예시/주석을 참고하여 생성해야 합니다.
    - 값이 없는 경우에도 빈 값(""), [], {} 등으로 명시해야 합니다.

    [필드별 상세 설명 및 예시]
    meta: 시나리오의 식별, 분류, 작성자 등 메타데이터
      - id: "D_3_1"
      - title: "Hook Revert DoS (BeforeSwap): beforeSwap 훅이 revert하여 swap 방해"
      - category: "Denial of Service"
      - severity: "medium"
      - tags: []
      - author: "llm-auto"
      - created: "2024-06-10T12:00:00Z"

    spec: 위협 시나리오의 행위자, 자산, 동작, 기대 결과 등 논리적/행위적 설명
      - description: "PoolKey에 설정된 훅의 beforeSwap 함수가 항상 revert하도록 설정"
      - actors: [{"id": "user", "role": "EOA user", "trust_level": "untrusted"}]
      - assets: [{"name": "Hook", "type": "address", "critical": true}]
      - components: [{"name": "PoolManager", "type": "contract", "deployed_at": ""}]
      - trust_boundaries: [{"from": "user", "to": "PoolManager", "enforcement": "msg.sender check"}]
      - data_flows: [{"source": "user", "target": "PoolManager", "function": "swap", "params": [{"name": "key", "value": "reverting"}, ...]}]
      - behaviors: [{"actor": "user", "action": "calls swap with reverting beforeSwap hook"}]
      - precondition: "PoolKey에 설정된 훅의 beforeSwap 함수가 항상 revert하도록 설정"
      - action: "targetContract.swap(key, params, hookData); // Via Unlock"
      - expected: "vm.expectRevert(Hooks.HookCallFailed.selector)"

    code: 실제 테스트 코드/컨텍스트 생성 정보
      - compiler_version: "^0.8.24"
      - target_contract_name: "PoolManager"
      - target_contract_declaration: "PoolManager internal _targetContract; ..."
      - target_contract_instance_name: "_targetContract"
      - required_imports: ["import { PoolManager } from 'src/PoolManager.sol';", ...]
      - setup_code: "token0 = new TestERC20(1e27); ..."
      - test_setup_code: "key = PoolKey({ ... }); ..."
      - action_function: null 또는 "swap"
      - action_code: "// Use the callback instance ..."
      - expected_revert_selector: "Hooks.HookCallFailed.selector"
      - assertion_code: null
      - helper_contracts: [{"name": "RevertingHook", ...}, ...]

    (자세한 구조와 예시는 D-3.1.yaml 및 schema_1.0.yaml을 참고하세요)
    """
    sid = scenario.get("meta", {}).get("id")
    if not sid:
        return {"error": "meta.id 필드는 필수입니다."}
    if load_scenario(sid):
        return {"error": f"시나리오 {sid}가 이미 존재합니다."}
    save_scenario(ScenarioDoc.from_json(json.dumps(scenario)))
    return {"success": True, "message": f"시나리오 {sid}가 등록되었습니다."}

@mcp.tool()
def update_scenario(sid: str, update_dict: dict) -> dict:
    """
    [MCP 시스템 컨텍스트]
    [LLM ONLY] 기존 시나리오의 일부 또는 전체를 업데이트하는 툴입니다.
    - 주로 초기 생성된 유닛테스트에 대한 피드백(시나리오 meta/spec/code 일부/전체 수정)에 사용합니다.
    - MCP는 LLM이 추론한 변경사항을 그대로 DB에 반영(저장)만 하며, 의미 해석/적합성 판단/자동 보정은 하지 않습니다.
    - 각 필드의 의미, 타입, 예시는 schema_1.0.yaml 및 실제 예시(D-3.1.yaml 등)를 참고하여 생성해야 합니다.
    - 예시: update_scenario("D_3_1", {"spec": {"expected": "Transaction must revert with ..."}})
    """
    doc = load_scenario(sid)
    if not doc:
        return {"error": f"시나리오 {sid}가 존재하지 않습니다."}
    doc_dict = asdict(doc)
    for k, v in update_dict.items():
        doc_dict[k] = v
    save_scenario(ScenarioDoc.from_json(json.dumps(doc_dict)))
    return {"success": True, "message": f"시나리오 {sid}가 업데이트되었습니다."}

@mcp.tool()
def detect_test_code_diff(sid: str, test_contract_name: str, foundry_root_path: str) -> dict:
    """
    [MCP 시스템 컨텍스트]
    테스트 코드(.t.sol) 변경(diff) 감지 및 기록 툴입니다.
    - MCP는 테스트 코드의 변경(diff) 자체만 patch log에 기록하며, 변경의 의미 해석/정합성 판단/추론은 하지 않습니다.
    - 변경된 diff의 의미 해석, 시나리오와의 정합성 판단, 추가 피드백 등은 반드시 LLM이 담당해야 합니다.
    - MCP는 단순히 이전 스냅샷과 현재 파일을 비교하여 diff가 있으면 patch log에 남기고, 없으면 아무 기록도 하지 않습니다.
    - sid: 시나리오 ID
    - test_contract_name: 테스트 컨트랙트 이름 (예: MCPTest_D_3_1)
    - foundry_root_path: Foundry 프로젝트 루트 경로
    """
    import os, difflib
    doc = load_scenario(sid)
    if not doc:
        return {"error": f"시나리오 {sid}가 존재하지 않습니다."}
    test_file_relative_path = os.path.join("test", "generated", f"{test_contract_name}.t.sol")
    test_file_full_path = os.path.join(foundry_root_path, test_file_relative_path)
    try:
        with open(test_file_full_path, "r", encoding="utf-8") as f:
            current_code = f.read()
    except FileNotFoundError:
        return {"error": f"테스트 파일 {test_file_full_path}를 찾을 수 없습니다."}
    doc.code.setdefault("test_code_snapshots", {})
    last_known_code = doc.code["test_code_snapshots"].get(test_contract_name, "")
    
    if current_code != last_known_code:
        # diff 생성 및 저장
        diff = difflib.unified_diff(
            last_known_code.splitlines(keepends=True),
            current_code.splitlines(keepends=True),
            fromfile=f"previous_{test_contract_name}.t.sol",
            tofile=f"current_{test_contract_name}.t.sol"
        )
        diff_text = "".join(diff)
        
        # 코드 스냅샷 업데이트
        doc.code["test_code_snapshots"][test_contract_name] = current_code
        
        # 패치 로그에 추가
        doc.add_patch(
            author="user",
            reason=f"{test_contract_name} 변경 감지",
            diff_text=diff_text
        )
        
        # DB 저장
        save_scenario(doc)
        
        return {
            "message": f"{test_contract_name} 변경사항이 기록되었습니다.",
            "diff": diff_text
        }
    else:
        return {"message": "테스트 코드 변경 없음."}

@mcp.tool()
def analyze_test_results(sid: str, run_id: str, insights: Dict[str, Any]) -> dict:
    """
    [MCP 시스템 컨텍스트]
    이 MCP 서버는 시나리오 기반 스마트컨트랙트 보안 검증 자동화의 핵심 백엔드입니다.
    MCP는 데이터 관리와 실행만 담당하며, 모든 "추론"은 LLM(상위 계층)이 담당합니다.
    
    [LLM ONLY] 유닛 테스트 실행 결과를 LLM이 분석하여 도출한 인사이트를 저장하는 툴입니다.
    
    - 이 기능은 LLM이 테스트 실행 결과(stdout, stderr, 상태 변화 등)를 심층 분석하여 
      추출한 통찰력을 시나리오에 누적 저장하는 데 사용됩니다.
    - 저장된 인사이트는 동일 시나리오의 반복 테스트를 통해 점진적으로 증가하며,
      LLM은 이를 활용하여 더 정교한 테스트 케이스를 생성하거나 시나리오를 개선할 수 있습니다.
    
    [매개변수]
    - sid: 시나리오 ID
    - run_id: 분석 대상 테스트 실행 ID (get_unit_test_logs 함수로 얻은 runlog의 run_id)
    - insights: LLM이 추출한 인사이트 정보 딕셔너리. 다음 필드를 포함할 수 있습니다:
        - precondition: 테스트의 전제 조건 (예: "reverting hook 설정 시")
        - state_changes: 관찰된 상태 변화 (예: "pool.liquidity 값이 0으로 유지됨")
        - patterns: 감지된 패턴 (예: "특정 주소로부터의 호출만 revert됨")
        - security_implications: 보안 영향 (예: "hook이 항상 revert하면 사용자는 swap 불가")
        - additional_info: 추가 정보 (예: 패턴, 가설 등)
        - confidence: 인사이트의 신뢰도 (0-1 범위의 값)
    
    [중요]
    LLM이 테스트 실행 로그와 결과를 자체적으로 깊이 분석하여 유의미한 패턴, 
    상태 변화, 조건부 행동, 보안 영향 등을 추출해야 합니다.
    MCP는 단순히 LLM이 제공한 인사이트를 저장만 하며, 내용에 대한 검증이나 추론은 하지 않습니다.
    """
    doc = load_scenario(sid)
    if not doc:
        return {"error": f"시나리오 {sid}가 존재하지 않습니다."}
    
    # 해당 run_id가 존재하는지 확인
    run_found = False
    for log in doc.runlog:
        if log.get("run_id") == run_id:
            run_found = True
            break
    
    if not run_found:
        return {"error": f"실행 ID {run_id}에 해당하는 로그를 찾을 수 없습니다."}
    
    # 인사이트 저장
    doc.add_test_insight(run_id, insights)
    save_scenario(doc)
    
    return {
        "success": True, 
        "message": f"시나리오 {sid}의 실행 {run_id}에 대한 인사이트가 저장되었습니다.",
        "insights_count": len(doc.test_insights)
    }

@mcp.tool()
def get_cumulative_insights(sid: str) -> dict:
    """
    [MCP 시스템 컨텍스트]
    이 MCP 서버는 시나리오 기반 스마트컨트랙트 보안 검증 자동화의 핵심 백엔드입니다.
    MCP는 데이터 관리와 실행만 담당하며, 모든 "추론"은 LLM(상위 계층)이 담당합니다.
    
    특정 시나리오에 대해 LLM이 분석하여 저장한 모든 테스트 인사이트를 시간순으로 조회합니다.
    
    - 이 기능은 시나리오의 여러 테스트 실행을 통해 LLM이 점진적으로 축적한 
      통찰력과 패턴을 종합적으로 분석하는 데 활용됩니다.
    - LLM은 이 누적된 인사이트를 바탕으로 시나리오의 행동을 더 정확히 이해하고,
      더 효과적인 테스트 케이스를 생성하거나 시나리오를 개선할 수 있습니다.
    
    [매개변수]
    - sid: 시나리오 ID
    
    [반환 값]
    - insights: 시나리오에 저장된 모든 인사이트 목록 (최신순)
    - 각 인사이트는 precondition, state_changes, patterns 등 LLM이 추출한 정보를 포함
    """
    doc = load_scenario(sid)
    if not doc:
        return {"error": f"시나리오 {sid}가 존재하지 않습니다."}
    
    return {
        "success": True,
        "insights": doc.get_cumulative_insights(),
        "insights_count": len(doc.test_insights)
    }

@mcp.tool()
def suggest_test_improvements(sid: str) -> dict:
    """
    [MCP 시스템 컨텍스트]
    이 MCP 서버는 시나리오 기반 스마트컨트랙트 보안 검증 자동화의 핵심 백엔드입니다.
    MCP는 데이터 관리와 실행만 담당하며, 모든 "추론"은 LLM(상위 계층)이 담당합니다.
    
    [LLM ONLY] 특정 시나리오의 누적된 인사이트를 바탕으로 테스트 개선 방안을 제안하는 툴입니다.
    
    - 이 기능은 LLM이 시나리오에 누적된 인사이트를 분석하여 
      더 효과적인 테스트 방법이나 새로운 테스트 케이스를 제안하는 데 사용됩니다.
    - MCP는 단순히 LLM이 제공한 제안을 저장만 하며, 제안의 질이나 타당성을 평가하지 않습니다.
    
    [매개변수]
    - sid: 시나리오 ID
    - suggestions: LLM이 추천하는 테스트 개선 방안 딕셔너리. 다음 필드를 포함할 수 있습니다:
        - new_test_cases: 추가해볼 새 테스트 케이스 목록
        - edge_conditions: 테스트해볼 엣지 케이스 조건
        - improvement_areas: 개선이 필요한 영역
        - refactoring_ideas: 리팩토링 아이디어
    
    [중요]
    LLM이 누적된 인사이트를 자체적으로 분석하여 의미 있는 개선 방안을 제시해야 합니다.
    MCP는 단순히 LLM이 제공한 제안을 시나리오에 추가만 하며, 내용을 평가하지 않습니다.
    """
    doc = load_scenario(sid)
    if not doc:
        return {"error": f"시나리오 {sid}가 존재하지 않습니다."}
    
    # 인사이트가 있는지 확인
    if not doc.test_insights:
        return {
            "success": False,
            "message": "이 시나리오에 대한 테스트 인사이트가 아직 없습니다. 테스트를 실행하고 analyze_test_results로 인사이트를 먼저 생성해주세요."
        }
    
    # 기존 인사이트 반환 (LLM이 이를 바탕으로 개선 방안 자체 추론)
    return {
        "success": True,
        "insights": doc.get_cumulative_insights(),
        "scenario": json.loads(doc.to_json())
    }

# 시스템 전체 설명 조회 엔드포인트 추가
@mcp.tool()
def get_system_context() -> dict:
    """
    MCP 시스템 전체 설명 및 협업 구조 안내
    
    이 엔드포인트는 MCP 시스템의 역할과 책임, LLM과의 협업 구조, 주요 툴의 목적 및 사용 흐름 등을 상세히 안내합니다.
    새로운 사용자나 개발자가 시스템을 이해하거나, LLM이 시스템 컨텍스트를 다시 확인할 때 사용할 수 있습니다.
    """
    return {
        "system_context": SYSTEM_CONTEXT_TEXT,
        "scenario_field_examples": SCENARIO_FIELDS_DESCRIPTION
    }

# 시스템 프로세스 설명 문서화 함수 추가
@mcp.tool()
def get_test_analysis_process() -> dict:
    """
    MCP의 테스트 결과 분석 및 인사이트 축적 프로세스에 대한 설명을 제공합니다.
    
    이 기능은 LLM이 유닛 테스트 결과를 분석하고 유용한 인사이트를 추출하여
    시나리오에 누적하는 프로세스를 이해하는 데 도움이 됩니다.
    """
    return {
        "process": """
테스트 결과 분석 및 인사이트 누적 프로세스:

1. 시나리오 등록 (register_scenario)
   - LLM이 시나리오를 생성하여 DB에 등록

2. 테스트 실행 (execute_single_unit_test)
   - 등록된 시나리오에 대한 유닛 테스트 실행
   - 실행 결과가 runlog에 저장됨

3. 테스트 결과 분석 (LLM 자체 분석)
   - LLM이 get_unit_test_logs 또는 get_single_unit_test_log로 실행 로그 조회
   - 테스트 결과(stdout, stderr)를 심층 분석하여 유용한 패턴, 상태 변화 등 추출

4. 인사이트 저장 (analyze_test_results)
   - LLM이 분석한 인사이트를 시나리오에 저장
   - 각 인사이트는 run_id와 연결되어 특정 테스트 실행과의 관계 유지

5. 누적 인사이트 활용 (get_cumulative_insights)
   - 시나리오에 대해 저장된 모든 인사이트를 조회
   - LLM이 이를 종합적으로 분석하여 더 깊은 이해 도출

6. 테스트 개선 제안 (suggest_test_improvements)
   - 누적된 인사이트를 바탕으로 테스트 개선 방안 도출
   - 새 테스트 케이스, 엣지 케이스, 개선 영역 등 식별

7. 시나리오 개선 (update_scenario)
   - 필요시 인사이트를 바탕으로 시나리오 자체를 업데이트하여 더 정확한 모델링

이 프로세스를 통해 LLM은 테스트 실행을 거듭하며 시나리오에 대한 이해를 점진적으로 
심화시키고, 이를 바탕으로 더 효과적인 보안 검증을 수행할 수 있습니다.
        """,
        
        "insight_example": {
            "precondition": "PoolKey에 revertingHook이 beforeSwap에 설정된 상태",
            "state_changes": "swap 호출 시 pool.liquidity 값이 변경되지 않음",
            "patterns": "모든 swap 호출이 동일한 revert 패턴을 보임 (HookCallFailed)",
            "security_implications": "악의적인 hook이 설정되면 유동성 공급자의 자금이 영구적으로 잠길 수 있음",
            "additional_info": "revert 발생 직전의 호출 스택에서 hook.beforeSwap이 마지막 호출임",
            "confidence": 0.95
        }
    }

@mcp.tool()
async def get_single_unit_test_log(sid: str, run_id: str) -> dict:
    """
    [MCP 시스템 컨텍스트]
    이 MCP 서버는 시나리오 기반 스마트컨트랙트 보안 검증 자동화의 핵심 백엔드입니다.
    MCP는 데이터 관리와 실행만 담당하며, 모든 "추론"은 LLM(상위 계층)이 담당합니다.
    
    단일 유닛테스트 실행 결과(runlog)를 조회하는 툴.
    sid(시나리오ID)와 run_id(실행ID)를 받아 해당 runlog를 반환합니다.
    
    [참고]
    이 함수로 조회한 테스트 실행 결과를 LLM이 분석하여 얻은 인사이트를
    analyze_test_results 함수를 통해 저장할 수 있습니다.
    """
    doc = load_scenario(sid)
    if not doc:
        return {"error": f"시나리오 {sid}를 찾을 수 없습니다."}
        
    for log in doc.runlog:
        if log.get("run_id") == run_id:
            return log
            
    return {"error": f"실행 ID {run_id}에 해당하는 로그를 찾을 수 없습니다."}

################################################################################
# run server
################################################################################

if __name__ == "__main__":
    logger.info("🔄 dynamic-schema MCP server started")
    local_server = LocalMCPServer()
    mcp.run(transport="stdio")

