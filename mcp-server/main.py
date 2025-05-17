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

    def update_hints_from_run(self, run_id: str, status: str, stdout: str, stderr: str):
        """실행 결과를 바탕으로 hints 업데이트"""
        self.hints.setdefault("runtime", {})["last_run_id"] = run_id
        
        # stdout, stderr 파싱하여 hints 채우기 (예시)
        # 실제 파싱 로직은 Foundry 출력 형식에 따라 매우 복잡해질 수 있음
        
        # Revert selector (간단한 예시: stderr에서 "Reverted"로 시작하는 라인 찾기)
        revert_selector = ""
        if "Reverted" in stderr: # 실제로는 더 정교한 패턴 매칭 필요
            # 예시: "Reverted: HookAddressNotValid" 에서 "HookAddressNotValid" 추출
            # 이 부분은 Foundry 출력에 맞춰 구체적인 파싱 로직 구현 필요
            # 지금은 단순화하여 stderr의 일부를 저장하거나, 특정 키워드 존재 여부만 기록
            # 실제 selector 추출은 복잡할 수 있어 플레이스홀더로 남겨둠
            # self.hints["runtime"]["revert_selector"] = "EXTRACTED_SELECTOR_EXAMPLE" 
            pass

        # Decoded logs (console.log 등)
        decoded_logs = []
        for line in stdout.splitlines():
            if "CONSOLE:" in line: # forge test -vvv 이상에서 CONSOLE: 접두사로 출력
                 # "CONSOLE: Scenario: S-ID - Precondition: Some precondition"
                log_content = line.split("CONSOLE:", 1)[1].strip()
                decoded_logs.append(log_content)
            # 이벤트 로그 파싱은 더 복잡하며, abi와 함께 디코딩 필요
        if decoded_logs:
            self.hints["runtime"].setdefault("decoded_logs", []).extend(decoded_logs)
            # 중복 방지 및 최신 로그 유지를 위해, 예를 들어 마지막 N개만 저장할 수도 있음
            self.hints["runtime"]["decoded_logs"] = list(set(self.hints["runtime"]["decoded_logs"]))


        # Gas usage (예시: stdout에서 "gas used" 라인 찾기)
        # self.hints.setdefault("gas", {})["used"] = EXTRACTED_GAS_USED_EXAMPLE
        
        # Compiler errors/warnings (테스트 실행 단계에서는 주로 런타임 에러지만, stderr에 컴파일 관련 내용이 있을 수도 있음)
        if "Error:" in stderr or "Warning:" in stderr: # 매우 일반적인 체크
            self.hints.setdefault("compiler", {}).setdefault("errors", []).append(stderr[:500]) # 예시로 일부만 저장

        # Traces (실패 시 트레이스 정보 파싱은 매우 복잡, 일단 플레이스홀더)
        # if status == "TEST_FAILURE":
        #     self.hints["runtime"].setdefault("traces", {})["root_fn"] = "EXTRACTED_FAILING_FUNCTION_EXAMPLE"
        
        # 성공/실패 상태도 hints에 기록 가능
        self.hints["runtime"]["last_run_status"] = status

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

def add_run(sid: str, status: str, diff: str,
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
    """DB에서 특정 시나리오의 전체 정보를 JSON 형태로 반환하며, 이는 시나리오 기반 검증 및 분석에 사용됩니다."""
    logger.info(f"[get_scenario] 호출: {sid}")
    doc = load_scenario(sid)
    return json.loads(doc.to_json()) if doc else {}

@mcp.tool()
async def list_scenarios() -> List[str]:
    """DB에 저장된 모든 시나리오의 ID 목록을 반환하여, 사용자가 검증 대상을 선택하거나 전체 시나리오 현황을 파악하는 데 도움을 줍니다."""
    logger.info(f"[list_scenarios] 호출")
    return list_ids()

@mcp.tool()
def export_scenario_to_yaml(sid: str, path: str) -> str:
    """DB에 저장된 특정 시나리오를 YAML 파일 형태로 내보냅니다. 이는 시나리오의 외부 공유나 백업 목적으로 사용될 수 있지만, 감사 중에는 DB를 기준으로 작업해야 합니다."""
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
    """지정된 폴더 내의 YAML 파일들을 읽어와 각 시나리오 정보를 DB에 일괄적으로 저장합니다. 주로 시스템 초기 설정이나 대량의 시나리오를 마이그레이션할 때 사용하며, 이후에는 DB를 통해 시나리오를 관리해야 합니다."""
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
# 6.  MCP Foundry/UnitTest/ScenarioValidation 도구 클래스 구조
################################################################################

class FoundryTool:
    """
    Foundry 관련 도구: 컴파일, 유닛테스트 실행, forge 로그 수집
    """

    def runUnitTest(self, test_contract_name=None, path=None, sid=None):
        """유닛테스트 실행 및 결과를 runlog에 자동 저장 (path: 테스트 파일이 위치한 디렉토리 경로)"""
        try:
            cmd = ["forge", "test", "-vvv"]
            if test_contract_name:
                cmd.extend(["--match-contract", test_contract_name])
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=path if path else None
            )
            success = result.returncode == 0
            status = "SUCCESS" if success else "TEST_FAILURE"
            diff = f"runUnitTest 실행: {test_contract_name if test_contract_name else ''}"
            if sid:
                add_run(sid, status, diff, result.stdout, result.stderr)
            return success, result.stdout, result.stderr
        except Exception as e:
            logger.error(f"테스트 실행 오류: {e}")
            if sid:
                add_run(sid, "ERROR", "runUnitTest 실행 중 오류", "", str(e))
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
        
        test_contract_name = f"MCPTest_{spec['meta']['id'].replace('-', '_').replace('.', '_')}"
        scenario_id_snake_case = re.sub(r'[^a-zA-Z0-9_]', '_', spec['meta']['id']).lower()
        
        # code 섹션을 scenario에 통합
        scenario = {**spec['meta'], **spec['code']}
        scenario['description'] = spec['spec']['description']
        scenario['precondition'] = spec['spec'].get('precondition', '')
        scenario['action'] = spec['spec'].get('action', '')
        scenario['expected'] = spec['spec'].get('expected', '')
        
        context = {
            "scenario": scenario,
            "test_contract_name": test_contract_name,
            "scenario_id_snake_case": scenario_id_snake_case,
            "compiler_version": scenario.get("compiler_version", "^0.8.24"),
            "target_contract_declaration": scenario.get("target_contract_declaration", "// Target contract declaration missing"),
            "target_contract_instance_name": scenario.get("target_contract_instance_name", "targetContract"),
            "helper_contracts": scenario.get("helper_contracts", []),
        }
        
        template = Template(self.template, trim_blocks=True, lstrip_blocks=True)
        rendered_code = template.render(context)
        filename = f"{test_contract_name}.t.sol"
        
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

    # --- 시나리오 처리 및 테스트 생성 ---
    def handleScenario(self, scenario: dict):
        """시나리오(YAML) 처리"""
        import os
        
        sid = scenario.get("meta", {}).get("id", "unknown")
        logger.info(f"시나리오 처리 시작: {sid}")
        start_time = datetime.datetime.now()
        
        try:
            # 1. 테스트 코드 생성
            filename, test_code = self.unittest_gen_tool.generateTestCode(scenario)
            
            # 2. 테스트 파일 저장
            test_dir = "test/generated"
            os.makedirs(test_dir, exist_ok=True)
            test_path = os.path.join(test_dir, filename)
            
            with open(test_path, "w", encoding="utf-8") as f:
                f.write(test_code)
            
            # 3. 컨트랙트 컴파일
            compile_success, compile_stdout, compile_stderr = self.foundry_tool.compileContracts()
            if not compile_success:
                diff = f"컴파일 오류 발생: {test_path}"
                add_run(sid, "COMPILE_ERROR", diff, compile_stdout, compile_stderr)
                
                return {
                    "status": "COMPILE_ERROR",
                    "message": "컴파일 오류 발생",
                    "stdout": compile_stdout,
                    "stderr": compile_stderr
                }
            
            # 4. 테스트 실행
            test_contract_name = filename.replace(".t.sol", "")
            test_success, test_stdout, test_stderr = self.foundry_tool.runUnitTest(test_contract_name)
            
            # 5. 결과 검증
            validation_prompt = self.validation_tool.buildValidationPrompt(scenario, test_stdout)
            
            end_time = datetime.datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            # 실행 로그 기록
            status = "SUCCESS" if test_success else "TEST_FAILURE"
            diff = f"시나리오 처리 {status}: {sid} (소요시간: {duration:.2f}초)"
            add_run(sid, status, diff, test_stdout, test_stderr)
            
            return {
                "status": status,
                "test_file": test_path,
                "test_output": test_stdout,
                "validation_prompt": validation_prompt,
                "duration": f"{duration:.2f}초"
            }
            
        except Exception as e:
            logger.error(f"시나리오 처리 오류: {e}")
            
            # 실행 로그 기록
            diff = f"시나리오 처리 중 오류 발생: {sid}"
            add_run(sid, "ERROR", diff, "", str(e))
            
            return {
                "status": "ERROR",
                "message": f"처리 중 오류 발생: {str(e)}"
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

    # --- 유닛테스트 실행용 메서드 추가 ---
    def run_unit_test_via_server(self, sid: str, test_contract_name: str, path: str):
        """
        FoundryTool의 runUnitTest를 감싸고, 코드 변경 감지, 실행 결과를 runlog(DB) 및 hints에 기록.
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
        # UnitTestGenTool에서 생성되는 파일명 규칙을 따라 경로 구성
        # test_dir = "test/generated" -> path는 foundry 프로젝트 루트여야 함
        # test_file_path = os.path.join(path, "test", "generated", f"{test_contract_name}.t.sol")
        # 단순화를 위해 path가 test_contract_name을 포함한 전체 파일 경로라고 가정하거나,
        # 혹은 test_contract_name이 'test/generated/MyTest.t.sol' 형태일 수 있음.
        # 여기서는 test_contract_name이 파일명이고 path가 디렉토리라고 가정하고 수정.
        # 일반적으로 forge test는 프로젝트 루트에서 실행되므로, path는 프로젝트 루트.
        # test_contract_name은 ContractName.t.sol 형태가 아니라, ContractName 만 주어지는 경우가 많음 (FoundryTool.runUnitTest의 --match-contract 인자)
        # 이 부분을 명확히 해야 함. 일단은 test_contract_name이 파일의 실제 이름(예: MyContract.t.sol)이라고 가정하고,
        # 그것이 path (프로젝트 루트) 아래 특정 위치 (예: test/)에 있다고 가정.
        # 정확한 테스트 파일 경로를 얻는 로직이 필요.
        # 여기서는 임시로 `path`를 테스트 파일이 있는 디렉토리로, `test_contract_name`을 파일명으로 가정.
        # 하지만 `execute_unit_test` 주석에는 path가 "foundry 프로젝트 디렉토리 경로"로 되어 있으므로,
        # 테스트 파일은 `path/test/{test_contract_name}.sol` 또는 `path/script/{test_contract_name}.s.sol` 등
        # 보다 구체적인 경로 규칙이 필요함.
        # `UnitTestGenTool.generateTestCode`는 `test/generated/{test_contract_name}.t.sol` 로 생성.
        # 따라서, `path`가 프로젝트 루트라면,
        test_file_relative_path = os.path.join("test", "generated", f"{test_contract_name}.t.sol")
        test_file_full_path = os.path.join(path, test_file_relative_path)
        
        current_code = ""
        try:
            with open(test_file_full_path, "r", encoding="utf-8") as f:
                current_code = f.read()
        except FileNotFoundError:
            logger.error(f"테스트 파일 {test_file_full_path}를 찾을 수 없습니다.")
            # 이 경우, 테스트 실행 자체가 불가하므로 오류 처리
            # add_run(sid, "ERROR", f"Test file {test_file_full_path} not found", "", "File not found")
            # doc.update_hints_from_run("N/A", "ERROR", "", f"Test file {test_file_full_path} not found")
            # save_scenario(doc)
            # return {"success": False, "stdout": "", "stderr": f"Test file {test_file_full_path} not found"}
            # 파일이 없는 경우, 코드 비교 및 실행을 할 수 없으므로 바로 반환하거나 에러 상태로 처리.
            # 일단은 빈 코드로 진행하여 diff가 크게 잡히도록 유도하고, unittest 실행 시 에러 발생 예상.
            pass


        # 2. 코드 변경 감지 및 patches 기록
        doc.code.setdefault("test_code_snapshots", {})
        last_known_code = doc.code["test_code_snapshots"].get(test_contract_name, "")
        
        if last_known_code != current_code:
            diff_text = "\\n".join(difflib.unified_diff(
                last_known_code.splitlines(),
                current_code.splitlines(),
                fromfile=f"previous_{test_contract_name}",
                tofile=f"current_{test_contract_name}",
                lineterm="\\n" # 개행문자 \n으로 통일
            ))
            if diff_text: # 실제로 차이가 있을 때만 패치 추가
                 doc.add_patch(
                    author="system-auto-detect",
                    reason=f"Code for {test_contract_name} changed since last run.",
                    diff_text=diff_text
                )
            doc.code["test_code_snapshots"][test_contract_name] = current_code # 최신 코드로 업데이트

        # 3. 유닛테스트 실행 (FoundryTool.runUnitTest는 프로젝트 루트에서 실행되어야 함)
        # self.foundry_tool.runUnitTest의 path 인자는 cwd로 사용됨.
        # test_contract_name은 --match-contract 인자로 전달됨.
        success, stdout, stderr = self.foundry_tool.runUnitTest(
            test_contract_name=test_contract_name, # 컨트랙트 이름 (예: MCPTest_S_1_1)
            path=path, # Foundry 프로젝트 루트 경로
            sid=None
        )
        
        # 4. runlog 기록
        status = "SUCCESS" if success else "TEST_FAILURE"
        diff_for_runlog = f"run_unit_test_via_server 실행: {test_contract_name}"
        run_id = add_run(sid, status, diff_for_runlog, stdout, stderr) # add_run이 run_id 반환 가정
        
        # 5. hints 업데이트
        doc.update_hints_from_run(run_id, status, stdout, stderr)
        
        # 6. 변경된 ScenarioDoc 저장
        save_scenario(doc)
        
        return {
            "success": success,
            "stdout": stdout,
            "stderr": stderr,
            "run_id": run_id # 실행 ID 반환
        }

    # --- 도구 디스패치 ---
    def dispatchTool(self, toolName: str, **kwargs):
        """도구 이름에 따라 해당 도구 실행"""
        tools = {
            # Foundry 도구
            "compile": self.foundry_tool.compileContracts,
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
            "handle": self.handleScenario
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
                add_run(sid, status, diff, stdout, stderr)
            
            return result
        except Exception as e:
            logger.error(f"{toolName} 도구 실행 오류: {e}")

            # runlog에 기록
            sid = kwargs.get("sid", None)
            if sid:
                diff = f"{toolName} 도구 실행 중 오류 발생"
                add_run(sid, "ERROR", diff, "", str(e))
            
            return {
                "status": "ERROR",
                "message": f"{toolName} 도구 실행 중 오류 발생: {str(e)}"
            }

@mcp.tool()
async def get_or_create_scenario_context_for_test(sid: str, test_contract_name: str, path: str) -> Dict[str, Any]:
    """
    주어진 시나리오 ID(sid)에 해당하는 테스트 시나리오가 DB에 존재하는지 확인합니다.
    존재하면 해당 시나리오의 모든 정보(메타데이터, 스펙, 코드 조각, 힌트, 실행 로그 등)를 컨텍스트로 반환합니다.
    존재하지 않으면, 제공된 test_contract_name과 path를 기반으로 기본적인 시나리오 정보를 생성하여 DB에 등록하고 그 정보를 반환합니다.
    이는 특정 유닛 테스트를 실행하거나 분석하기 전에 필요한 컨텍스트를 확보하는 데 사용됩니다.
    - sid: 시나리오 ID (예: "D-3-1")
    - test_contract_name: 테스트 컨트랙트 이름 (예: "MCPTest_D_3_1")
    - path: Foundry 프로젝트 디렉토리 경로 (예: "/foundry_project")
    """
    logger.info(f"[get_or_create_scenario_context_for_test] 호출: sid={sid}, test_contract_name={test_contract_name}, path={path}")
    doc = load_scenario(sid)

    if doc:
        logger.info(f"시나리오 {sid} 발견. 컨텍스트 반환.")
        return json.loads(doc.to_json())
    else:
        logger.info(f"시나리오 {sid} 없음. 새로 생성합니다.")
        new_doc = ScenarioDoc(
            meta={
                "id": sid,
                "title": f"Auto-generated scenario for {test_contract_name}",
                "category": "Uncategorized", # 기본 카테고리
                "severity": "medium" # 기본 심각도
            },
            spec={
                "description": f"This scenario was auto-generated for the unit test contract '{test_contract_name}' located in the project at '{path}'. Please provide a detailed description, precondition, action, and expected outcome.",
                "precondition": "// TODO: Define precondition",
                "action": "// TODO: Define action",
                "expected": "// TODO: Define expected outcome"
            },
            code={
                "test_contract_name": test_contract_name, # 생성될 테스트 파일의 컨트랙트 이름 (e.g. MCPTest_D_3_1)
                "project_path": path,
                "compiler_version": "^0.8.24", # 기본 컴파일러 버전
                "required_imports": ["import \"forge-std/Test.sol\";"],
                "target_contract_declaration": f"// TODO: Declare your target contract instance for {test_contract_name}",
                # 실제 테스트 대상 컨트랙트 이름은 사용자가 명시해야 함
                "target_contract_name": "", # 예: "MyLogicContract" (사용자가 채워야 함)
                "target_contract_instance_name": "targetContract", # 기본 인스턴스명
                "setup_code": "// TODO: Add general setup code for the test contract here.",
                "test_setup_code": "// TODO: Add test-specific setup code if needed.",
                "action_code": "// TODO: Add code to execute the action to be tested.",
                "assertion_code": "// TODO: Add assertion code to verify the outcome.",
                "expected_revert_selector": "", # 비워두면 revert 예상 안 함
                "test_code_snapshots": {} # 초기화
            },
            hints={}, # 초기화
            patches=[], # 초기화
            runlog=[], # 초기화
            extras={}
        )
        try:
            save_scenario(new_doc)
            logger.info(f"새로운 시나리오 {sid} 생성 및 저장 완료.")
            return json.loads(new_doc.to_json())
        except Exception as e:
            logger.error(f"새로운 시나리오 {sid} 저장 실패: {e}")
            # 실패 시 빈 객체나 에러 메시지를 포함한 객체 반환 가능
            return {"error": f"Failed to create and save scenario {sid}: {str(e)}"}

@mcp.tool()
async def execute_unit_test(sid: str, test_contract_name: str, path: str):
    """
    지정된 시나리오 ID에 해당하는 Foundry 유닛 테스트를 실행하고, 그 결과를 DB의 runlog에 기록합니다.
    이를 통해 특정 시나리오의 검증을 자동화하고, 실행 이력을 관리할 수 있습니다.

    - sid: 시나리오 ID (실행 로그 기록용)
    - test_contract_name: 테스트 컨트랙트 이름 (예: MCPTest_S_1_1)
    - path: foundry 프로젝트 디렉토리 경로 (예: /foundry_project)
    """
    result = local_server.run_unit_test_via_server(
        sid=sid,
        test_contract_name=test_contract_name,
        path=path
    )
    return result


# 클래스 관계 다이어그램
# LocalMCPServer --> FoundryTool            : foundry 작업 위임
# LocalMCPServer --> UnitTestGenTool        : 테스트 코드 생성 
# LocalMCPServer --> ScenarioValidationTool : 시나리오 검증
# LocalMCPServer --> SchemaAnalysisTool     : 스키마 분석
# LocalMCPServer -.-> SQLite DB             : runlog 저장
# FoundryTool    -.-> ScenarioValidationTool : forge 로그 제공

################################################################################
# run server
################################################################################
if __name__ == "__main__":
    logger.info("🔄 dynamic-schema MCP server started")
    local_server = LocalMCPServer()
    mcp.run(transport="stdio")