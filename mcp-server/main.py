################################################################################
# 0. imports & logger
################################################################################
import os, json, uuid, sqlite3, datetime, logging
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

    meta: Dict[str, Any]
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
        return ScenarioDoc(**data)

################################################################################
# 2.  SQLite DAO
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
    with _conn() as c:
        c.execute("INSERT OR REPLACE INTO scenario VALUES (?,?)",
                  (doc.id, doc.to_json()))

def load_scenario(sid: str) -> Optional[ScenarioDoc]:
    row = _conn().execute("SELECT json FROM scenario WHERE id=?", (sid,)).fetchone()
    return ScenarioDoc.from_json(row["json"]) if row else None

def list_ids() -> List[str]:
    return [r["id"] for r in _conn().execute("SELECT id FROM scenario")]

def add_run(sid: str, status: str, diff: str,
            stdout: str = "", stderr: str = ""):
    with _conn() as c:
        c.execute("""INSERT INTO runlog VALUES (?,?,?,?,?,?)""",
                  (str(uuid.uuid4()), sid,
                   datetime.datetime.utcnow().isoformat(),
                   status, diff, (stdout + stderr)[:8000]))

################################################################################
# 3.  MCP tools
################################################################################
@mcp.tool()
async def store_scenario(scenario_json: Dict[str, Any]) -> str:
    """(Upsert) 전체 YAML-JSON 구조를 그대로 저장."""
    logger.info(f"[store_scenario] 호출: {scenario_json.get('meta', {}).get('id', 'no-id')}")
    doc = ScenarioDoc.from_json(json.dumps(scenario_json))
    save_scenario(doc)
    return f"stored {doc.id}"

@mcp.tool()
async def get_scenario(sid: str) -> Dict[str, Any]:
    """시나리오 전체 JSON 반환 (없으면 빈 dict)."""
    logger.info(f"[get_scenario] 호출: {sid}")
    doc = load_scenario(sid)
    return json.loads(doc.to_json()) if doc else {}

@mcp.tool()
async def list_scenarios() -> List[str]:
    """모든 시나리오 id 리스트."""
    logger.info(f"[list_scenarios] 호출")
    return list_ids()

@mcp.tool()
async def record_run(sid: str, status: str,
                     diff: str, stdout: str = "", stderr: str = "") -> str:
    """테스트 실행 결과 diff 및 로그 저장."""
    logger.info(f"[record_run] 호출: scenario_id={sid}, status={status}")
    add_run(sid, status, diff, stdout, stderr)
    return "ok"

################################################################################
# 4.  (선택) 스키마-버전 필드 초기 캡처
################################################################################
def bootstrap_from_yaml_files(folder="scenarios"):
    import glob, yaml
    for fp in glob.glob(os.path.join(folder, "*.yaml")):
        with open(fp, "r") as f:
            raw = yaml.safe_load(f)
        doc = ScenarioDoc.from_json(json.dumps(raw))
        save_scenario(doc)
    logger.info("bootstrap complete")

################################################################################
# 5.  run server
################################################################################
if __name__ == "__main__":
    logger.info("🔄 dynamic-schema MCP server started")
    mcp.run(transport="stdio")
