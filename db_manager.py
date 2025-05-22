import os, json, uuid, sqlite3, datetime, logging
from dataclasses import dataclass, asdict, field, fields
from typing import Any, Dict, List, Optional

# 로거 설정
logger = logging.getLogger("db-manager")
logger.setLevel(logging.INFO)
handler = logging.FileHandler("db-manager.log")
handler.setLevel(logging.INFO)
logger.addHandler(handler)

# DB 경로 설정
_DB = os.getenv("SCENARIO_DB", "scenario_dyn.db")

@dataclass
class ScenarioDoc:
    """전체 YAML 을 JSON 으로 파싱 후 보관 + 최소 PK(id)만 강제."""

    meta: Dict[str, Any] = field(default_factory=dict)
    spec: Dict[str, Any] = field(default_factory=dict)
    hints: Dict[str, Any] = field(default_factory=dict)
    prompt_ctx: Dict[str, Any] = field(default_factory=dict)
    patches: List[Dict[str, Any]] = field(default_factory=list)
    runlog: List[Dict[str, Any]] = field(default_factory=list)
    extras: Dict[str, Any] = field(default_factory=dict)  # 미래 섹션
    test_insights: List[Dict[str, Any]] = field(default_factory=list)  # 테스트 결과에서 LLM이 추출한 인사이트 저장
    test_code_snapshots: Dict[str, str] = field(default_factory=dict) # 추가: 테스트 코드 스냅샷 저장

    # --- util ---------------------------------------------------------------
    @property
    def id(self) -> str:
        """시나리오 ID 반환"""
        return self.meta.get("id", "")

    def to_json(self) -> str:
        """ScenarioDoc을 JSON 문자열로 변환"""
        return json.dumps(asdict(self))

    @staticmethod
    def from_json(js: str) -> "ScenarioDoc":
        """JSON 문자열에서 ScenarioDoc 생성"""
        data = json.loads(js)
        field_names = {f.name for f in fields(ScenarioDoc)}
        
        # 기본값 설정 및 extras 처리
        processed_data = {}
        current_extras = data.get("extras", {})

        for fname_in_class in field_names:
            if fname_in_class == "extras": # extras 필드는 아래에서 별도 처리
                continue
            if fname_in_class in data:
                processed_data[fname_in_class] = data[fname_in_class]
            else: # 클래스에 정의된 필드지만 입력 데이터에 없는 경우 기본값 사용
                if fname_in_class in ["patches", "runlog", "test_insights"]:
                    processed_data[fname_in_class] = []
                else:
                    processed_data[fname_in_class] = {}

        # 입력 데이터에 있지만 ScenarioDoc 클래스 필드에 없는 최상위 키를 extras에 추가
        for key_in_data, value_in_data in data.items():
            if key_in_data not in field_names:
                current_extras[key_in_data] = value_in_data
        
        processed_data["extras"] = current_extras
        
        return ScenarioDoc(**processed_data)

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
        return run_id  # 편의를 위해 run_id 반환

    def add_patch(self, author: str, reason: str, diff_text: str):
        """시나리오에 코드 변경 패치 추가"""
        patch_entry = {
            "ts": datetime.datetime.utcnow().isoformat(),
            "author": author,
            "reason": reason,
            "diff": diff_text
        }
        self.patches.append(patch_entry)
        return patch_entry  # 편의를 위해 추가된 patch_entry 반환

    def add_test_insight(self, run_id: str, insight: Dict[str, Any]):
        """
        LLM이 순차적 사고 과정(Sequential Thinking)을 통해 테스트 실행 결과에서 추출한 인사이트를 저장합니다.
        
        순차적 사고 과정은 다음과 같은 단계로 구성됩니다:
        1. 초기 관찰: 테스트 로그 검토 및 기본 패턴 식별
        2. 심층 분석: 실행 흐름, 상태 변화, 조건부 행동 분석
        3. 가설 형성: 시스템 동작 및 보안 영향에 대한 가설 수립
        4. 가설 검증: 데이터 재검토를 통한 가설 검증 및 대안 고려
        5. 인사이트 도출: 검증된 발견 사항을 구조화된 형태로 정리
        
        Args:
            run_id: 테스트 실행 ID (인사이트의 출처가 되는 실행)
            insight: 인사이트 정보 딕셔너리, 다음 필드 포함 가능:
              - precondition: 테스트의 전제 조건 (예: "reverting hook 설정 시")
              - state_changes: 관찰된 상태 변화 (예: "pool.liquidity 값이 0으로 유지됨")
              - patterns: 감지된 패턴 (예: "특정 주소로부터의 호출만 revert됨")
              - security_implications: 보안 영향 (예: "hook이 항상 revert하면 사용자는 swap 불가")
              - additional_info: 추가 정보, 대안 가설, 또는 분석 과정의 특이점
              - confidence: 인사이트의 신뢰도 (0-1 범위의 값)
        
        Returns:
            Dict[str, Any]: 저장된 인사이트 (타임스탬프 및 run_id 추가)
        """
        # insight가 문자열인 경우 딕셔너리로 변환
        if isinstance(insight, str):
            try:
                insight = json.loads(insight)
            except json.JSONDecodeError:
                logger.error(f"add_test_insight: 유효하지 않은 JSON 문자열 - {insight[:50]}...")
                # 기본 형태의 딕셔너리로 변환
                insight = {
                    "precondition": "정보 없음",
                    "state_changes": "정보 없음",
                    "patterns": "정보 없음",
                    "security_implications": "정보 없음",
                    "additional_info": f"원본 데이터: {insight[:100]}...",
                    "confidence": 0.5
                }
        
        # 타임스탬프 추가
        insight["ts"] = datetime.datetime.utcnow().isoformat()
        insight["run_id"] = run_id
        
        # test_insights가 존재하지 않거나 딕셔너리인 경우 리스트로 초기화
        if not hasattr(self, 'test_insights') or not isinstance(self.test_insights, list):
            logger.warning("test_insights 필드가 없거나 리스트가 아닙니다. 새 리스트로 초기화합니다.")
            self.test_insights = []
            
        # 동일 run_id에 대한 기존 인사이트가 있으면 업데이트, 없으면 추가
        updated = False
        for i, existing in enumerate(self.test_insights):
            if existing.get("run_id") == run_id:
                self.test_insights[i] = insight
                updated = True
                break
        
        if not updated:
            self.test_insights.append(insight)
        
        return insight  # 편의를 위해 추가/업데이트된 insight 반환

    def get_cumulative_insights(self) -> List[Dict[str, Any]]:
        """
        시나리오에 대해 저장된 모든 인사이트를 시간순으로 반환합니다.
        이를 통해 LLM은 해당 시나리오에 대해 발견된 모든 패턴과 정보를 종합적으로 분석할 수 있습니다.
        """
        # test_insights가 존재하지 않거나 딕셔너리인 경우 리스트로 초기화
        if not hasattr(self, 'test_insights'):
            logger.warning("test_insights 필드가 없습니다. 빈 리스트로 초기화합니다.")
            return []
            
        if not isinstance(self.test_insights, list):
            logger.warning(f"test_insights 필드가 리스트가 아닙니다. 현재 타입: {type(self.test_insights)}. 빈 리스트로 초기화합니다.")
            return []
            
        # 각 인사이트가 문자열인 경우 처리
        processed_insights = []
        for insight in self.test_insights:
            if isinstance(insight, str):
                try:
                    # 문자열을 딕셔너리로 변환 시도
                    parsed_insight = json.loads(insight)
                    processed_insights.append(parsed_insight)
                except json.JSONDecodeError:
                    # 파싱 실패 시 원본 정보로 새 딕셔너리 생성
                    logger.warning(f"잘못된 형식의 인사이트: {insight[:50]}...")
                    parsed_insight = {
                        "ts": datetime.datetime.utcnow().isoformat(),
                        "run_id": "unknown",
                        "precondition": "정보 없음",
                        "state_changes": "정보 없음",
                        "patterns": "정보 없음",
                        "security_implications": "정보 없음",
                        "additional_info": f"원본 데이터: {insight[:100]}...",
                        "confidence": 0.5
                    }
                    processed_insights.append(parsed_insight)
            else:
                processed_insights.append(insight)
        
        # 타임스탬프 기준 정렬 (최신순)
        # 문자열 형태의 타임스탬프도 처리할 수 있도록 안전하게 처리
        def get_timestamp(item):
            if not isinstance(item, dict):
                return ""
            
            ts = item.get("ts", "")
            if isinstance(ts, (datetime.datetime, datetime.date)):
                return ts.isoformat()
            return ts
        
        return sorted(processed_insights, key=get_timestamp, reverse=True)

    def update_hints_from_run(self, run_id: str, status: str, stdout: str, stderr: str):
        """실행 결과를 바탕으로 hints 업데이트"""
        from schema_validator import extract_hints
        
        self.hints.setdefault("runtime", {})["last_run_id"] = run_id
        self.hints["runtime"]["last_run_status"] = status
        
        # schema_validator.py의 extract_hints 사용하여 힌트 업데이트
        scenario_data = json.loads(self.to_json())
        updated_scenario = extract_hints(scenario_data, stdout, stderr)
        
        # 업데이트된 힌트를 현재 객체에 반영
        self.hints = updated_scenario.get("hints", self.hints)
        
        return self.hints  # 편의를 위해 업데이트된 hints 반환


# DB 초기화 함수
def init_db():
    """DB 초기화 및 테이블 생성"""
    with sqlite3.connect(_DB) as c:
        c.execute("""CREATE TABLE IF NOT EXISTS scenario
                     (id TEXT PRIMARY KEY, json TEXT NOT NULL)""")
        c.execute("""CREATE TABLE IF NOT EXISTS runlog
                     (run_id TEXT PRIMARY KEY, scenario_id TEXT, ts TEXT,
                      status TEXT, diff TEXT, stdout TEXT, stderr TEXT)""")
    logger.info(f"DB 초기화 완료: {_DB}")

# 초기화 실행
init_db()

def _conn():
    """SQLite 연결 생성 (Row Factory 설정)"""
    cx = sqlite3.connect(_DB)
    cx.row_factory = sqlite3.Row
    return cx

# CRUD helpers --------------------------------------------------------------
def save_scenario(doc: ScenarioDoc) -> bool:
    """시나리오 저장/업데이트 (meta.id 필수)"""
    if not doc.id:
        logger.error("save_scenario 호출 시 meta.id가 없습니다.")
        raise ValueError("meta.id is required")
    
    try:
        # 저장 전 누락 필드 보완
        doc_json = doc.to_json()
        doc = ScenarioDoc.from_json(doc_json)
        with _conn() as c:
            c.execute("INSERT OR REPLACE INTO scenario VALUES (?,?)",
                      (doc.id, doc.to_json()))
        logger.info(f"시나리오 {doc.id} 저장 완료")
        return True
    except Exception as e:
        logger.error(f"시나리오 {doc.id} 저장 중 오류: {e}")
        raise

def load_scenario(sid: str) -> Optional[ScenarioDoc]:
    """ID로 시나리오 로드"""
    try:
        row = _conn().execute("SELECT json FROM scenario WHERE id=?", (sid,)).fetchone()
        if row:
            return ScenarioDoc.from_json(row["json"])
        logger.info(f"시나리오 {sid} 로드 실패: 존재하지 않음")
        return None
    except Exception as e:
        logger.error(f"시나리오 {sid} 로드 중 오류: {e}")
        return None

def update_scenario_partial(sid: str, update_dict: dict) -> bool:
    """시나리오 부분 업데이트"""
    try:
        doc = load_scenario(sid)
        if not doc:
            logger.error(f"update_scenario_partial: 시나리오 {sid} 없음")
            raise ValueError(f"해당 시나리오가 없습니다: {sid}")
        
        doc_dict = asdict(doc)
        for k, v in update_dict.items():
            doc_dict[k] = v
        doc_json = json.dumps(doc_dict)
        doc = ScenarioDoc.from_json(doc_json)
        save_scenario(doc)
        logger.info(f"시나리오 {sid} 부분 업데이트 완료")
        return True
    except Exception as e:
        logger.error(f"시나리오 {sid} 부분 업데이트 중 오류: {e}")
        raise

def delete_scenario(sid: str) -> bool:
    """ID로 시나리오 삭제"""
    try:
        with _conn() as c:
            c.execute("DELETE FROM scenario WHERE id=?", (sid,))
        logger.info(f"시나리오 {sid} 삭제 완료")
        return True
    except Exception as e:
        logger.error(f"시나리오 {sid} 삭제 중 오류: {e}")
        return False

def list_ids() -> List[str]:
    """저장된 모든 시나리오 ID 목록 반환"""
    try:
        ids = [r["id"] for r in _conn().execute("SELECT id FROM scenario")]
        logger.info(f"시나리오 ID 목록 조회: {len(ids)}개")
        return ids
    except Exception as e:
        logger.error(f"시나리오 ID 목록 조회 중 오류: {e}")
        return []

def add_runlog_entry(sid: str, status: str, diff: str,
            stdout: str = "", stderr: str = "") -> str:
    """실행 로그 추가 (DB + 시나리오 문서)"""
    run_id = str(uuid.uuid4())
    try:
        # 1. DB의 runlog 테이블에 추가
        with _conn() as c:
            c.execute("""INSERT INTO runlog VALUES (?,?,?,?,?,?,?)""",
                      (run_id, sid,
                       datetime.datetime.utcnow().isoformat(),
                       status, diff, stdout[:8000], stderr[:8000]))
        
        # 2. 시나리오 문서에도 로그 추가
        doc = load_scenario(sid)
        if doc:
            doc.add_run_log(run_id, status, diff, stdout, stderr)
            save_scenario(doc)
        
        logger.info(f"실행 로그 추가 완료: sid={sid}, run_id={run_id}, status={status}")
        return run_id
    except Exception as e:
        logger.error(f"실행 로그 추가 중 오류: sid={sid}, {e}")
        # 에러가 발생해도 run_id는 반환 (부분 기록은 될 수 있으므로)
        return run_id 