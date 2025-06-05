"""
Database manager for audit_agent project

이 모듈은 audit_agent에서 사용되는 데이터베이스 CRUD 작업을 관리합니다.
SQLite를 사용하여 시나리오 데이터를 저장하고 관리합니다.
"""

import os
import json
import uuid
import sqlite3
from typing import Optional, List

from config.logging_config import get_logger
from config.settings import settings
from .models import ScenarioDoc

logger = get_logger("database")


def init_db(verbose: bool = True):
    """
    데이터베이스를 완전히 초기화합니다.
    파일이 없으면 새로 생성하고, 빈 데이터베이스 처리도 포함합니다.
    
    Args:
        verbose: 상세 로그 출력 여부
    """
    db_path = settings.database_path
    is_new_db = not os.path.exists(db_path)
    
    try:
        if is_new_db and verbose:
            logger.info(f"데이터베이스 파일이 존재하지 않습니다: {db_path}")
            logger.info("새로운 데이터베이스를 생성합니다...")
        elif verbose:
            logger.info(f"기존 데이터베이스를 사용합니다: {db_path}")
        
        # 테이블 생성
        with _conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS scenario (
                    id TEXT PRIMARY KEY,
                    data TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS runlog (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    scenario_id TEXT NOT NULL,
                    run_id TEXT NOT NULL,
                    test_name TEXT,
                    timestamp TEXT NOT NULL,
                    status TEXT NOT NULL,
                    stdout TEXT,
                    stderr TEXT,
                    FOREIGN KEY (scenario_id) REFERENCES scenario (id)
                )
            """)
            conn.commit()
        
        if verbose:
            if is_new_db:
                logger.info(f"✅ 새로운 데이터베이스가 생성되었습니다: {db_path}")
            else:
                logger.info("✅ 데이터베이스 초기화 완료")
        
        # 빈 데이터베이스 처리 및 무결성 확인
        _ensure_database_integrity(verbose)
        
    except Exception as e:
        logger.error(f"데이터베이스 초기화 실패: {e}")
        raise


def _conn():
    """
    데이터베이스 연결을 반환합니다.
    
    Returns:
        sqlite3.Connection: 데이터베이스 연결 객체
    """
    return sqlite3.connect(settings.database_path)


def save_scenario(doc: ScenarioDoc) -> bool:
    """
    시나리오를 데이터베이스에 저장하거나 업데이트합니다.
    
    Args:
        doc: 저장할 ScenarioDoc 객체
        
    Returns:
        bool: 저장 성공 여부
    """
    try:
        with _conn() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO scenario (id, data) VALUES (?, ?)",
                (doc.id, doc.to_json())
            )
            conn.commit()
            logger.info(f"시나리오 저장 성공: {doc.id}")
            return True
    except Exception as e:
        logger.error(f"시나리오 저장 실패 ({doc.id}): {e}")
        return False


def load_scenario(sid: str) -> Optional[ScenarioDoc]:
    """
    데이터베이스에서 시나리오를 로드합니다.
    
    Args:
        sid: 시나리오 ID
        
    Returns:
        Optional[ScenarioDoc]: 로드된 ScenarioDoc 객체 또는 None
    """
    try:
        with _conn() as conn:
            cursor = conn.execute("SELECT data FROM scenario WHERE id = ?", (sid,))
            row = cursor.fetchone()
            if row:
                doc = ScenarioDoc.from_json(row[0])
                logger.info(f"시나리오 로드 성공: {sid}")
                return doc
            else:
                logger.warning(f"시나리오를 찾을 수 없음: {sid}")
                return None
    except Exception as e:
        logger.error(f"시나리오 로드 실패 ({sid}): {e}")
        return None


def update_scenario_partial(sid: str, update_dict: dict) -> bool:
    """
    시나리오의 일부 필드를 업데이트합니다.
    
    Args:
        sid: 시나리오 ID
        update_dict: 업데이트할 필드와 값들
        
    Returns:
        bool: 업데이트 성공 여부
    """
    try:
        doc = load_scenario(sid)
        if not doc:
            logger.error(f"업데이트할 시나리오를 찾을 수 없음: {sid}")
            return False
        
        # 재귀적으로 딕셔너리 업데이트
        def _recursive_update(original, updates):
            for key, value in updates.items():
                if isinstance(value, dict) and key in original and isinstance(original[key], dict):
                    _recursive_update(original[key], value)
                else:
                    original[key] = value
        
        # ScenarioDoc 객체를 딕셔너리로 변환하여 업데이트
        doc_dict = json.loads(doc.to_json())
        _recursive_update(doc_dict, update_dict)
        
        # 업데이트된 딕셔너리로 새 ScenarioDoc 생성
        updated_doc = ScenarioDoc.from_json(json.dumps(doc_dict))
        
        # 저장
        success = save_scenario(updated_doc)
        if success:
            logger.info(f"시나리오 부분 업데이트 성공: {sid}")
        return success
        
    except Exception as e:
        logger.error(f"시나리오 부분 업데이트 실패 ({sid}): {e}")
        return False


def delete_scenario(sid: str) -> bool:
    """
    데이터베이스에서 시나리오를 삭제합니다.
    
    Args:
        sid: 삭제할 시나리오 ID
        
    Returns:
        bool: 삭제 성공 여부
    """
    try:
        with _conn() as conn:
            cursor = conn.execute("DELETE FROM scenario WHERE id = ?", (sid,))
            if cursor.rowcount > 0:
                # 관련 실행 로그도 삭제
                conn.execute("DELETE FROM runlog WHERE scenario_id = ?", (sid,))
                conn.commit()
                logger.info(f"시나리오 삭제 성공: {sid}")
                return True
            else:
                logger.warning(f"삭제할 시나리오를 찾을 수 없음: {sid}")
                return False
    except Exception as e:
        logger.error(f"시나리오 삭제 실패 ({sid}): {e}")
        return False


def list_ids() -> List[str]:
    """
    데이터베이스의 모든 시나리오 ID 목록을 반환합니다.
    
    Returns:
        List[str]: 시나리오 ID 목록 (에러 시 빈 리스트)
    """
    try:
        # 데이터베이스 파일 존재 확인
        if not os.path.exists(settings.database_path):
            logger.warning(f"데이터베이스 파일이 존재하지 않음: {settings.database_path}")
            return []
        
        with _conn() as conn:
            # 테이블 존재 확인
            cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='scenario'")
            if not cursor.fetchone():
                logger.warning("scenario 테이블이 존재하지 않음")
                return []
            
            cursor = conn.execute("SELECT id FROM scenario ORDER BY id")
            ids = [row[0] for row in cursor.fetchall()]
            logger.info(f"시나리오 ID 목록 조회: {len(ids)}개")
            return ids
            
    except sqlite3.Error as e:
        logger.error(f"SQLite 오류로 시나리오 ID 목록 조회 실패: {e}")
        return []
    except Exception as e:
        logger.error(f"시나리오 ID 목록 조회 중 예상치 못한 오류: {e}")
        logger.error(f"오류 타입: {type(e).__name__}")
        return []


def add_runlog_entry(sid: str, status: str, diff: str, stdout: str = "", stderr: str = "", test_name: str = "") -> str:
    """
    시나리오에 실행 로그 엔트리를 추가합니다.
    
    Args:
        sid: 시나리오 ID
        status: 실행 상태
        diff: 코드 변경 diff
        stdout: 표준 출력
        stderr: 표준 에러
        test_name: 테스트 이름
        
    Returns:
        str: 생성된 실행 ID
    """
    run_id = str(uuid.uuid4())
    
    try:
        # 시나리오 객체에 로그 추가
        doc = load_scenario(sid)
        if doc:
            doc.add_run_log(run_id, status, diff, stdout, stderr, test_name)
            save_scenario(doc)
        
        # 별도 runlog 테이블에도 기록 (검색 최적화용)
        with _conn() as conn:
            conn.execute("""
                INSERT INTO runlog (scenario_id, run_id, test_name, timestamp, status, stdout, stderr)
                VALUES (?, ?, ?, datetime('now'), ?, ?, ?)
            """, (sid, run_id, test_name, status, stdout[:settings.max_log_size], stderr[:settings.max_log_size]))
            conn.commit()
        
        logger.info(f"실행 로그 추가: {run_id} (시나리오: {sid}, 테스트: {test_name})")
        return run_id
        
    except Exception as e:
        logger.error(f"실행 로그 추가 실패 ({sid}): {e}")
        return run_id  # run_id는 반환하되 로그는 실패


def get_runlog_entries(sid: str, test_name: str = None, limit: int = 100) -> List[dict]:
    """
    시나리오의 실행 로그 엔트리들을 조회합니다.
    
    Args:
        sid: 시나리오 ID
        test_name: 특정 테스트 이름 (None이면 모든 테스트)
        limit: 최대 조회 개수
        
    Returns:
        List[dict]: 실행 로그 엔트리 목록
    """
    try:
        with _conn() as conn:
            if test_name:
                cursor = conn.execute("""
                    SELECT run_id, test_name, timestamp, status, stdout, stderr
                    FROM runlog 
                    WHERE scenario_id = ? AND test_name = ?
                    ORDER BY timestamp DESC 
                    LIMIT ?
                """, (sid, test_name, limit))
            else:
                cursor = conn.execute("""
                    SELECT run_id, test_name, timestamp, status, stdout, stderr
                    FROM runlog 
                    WHERE scenario_id = ?
                    ORDER BY timestamp DESC 
                    LIMIT ?
                """, (sid, limit))
            
            entries = []
            for row in cursor.fetchall():
                entries.append({
                    "run_id": row[0],
                    "test_name": row[1],
                    "timestamp": row[2],
                    "status": row[3],
                    "stdout": row[4],
                    "stderr": row[5]
                })
            
            logger.info(f"실행 로그 조회: {len(entries)}개 (시나리오: {sid})")
            return entries
            
    except Exception as e:
        logger.error(f"실행 로그 조회 실패 ({sid}): {e}")
        return []


def cleanup_old_runlogs(days: int = 30):
    """
    오래된 실행 로그를 정리합니다.
    
    Args:
        days: 보관할 기간 (일)
    """
    try:
        with _conn() as conn:
            cursor = conn.execute("""
                DELETE FROM runlog 
                WHERE timestamp < datetime('now', '-{} days')
            """.format(days))
            deleted_count = cursor.rowcount
            conn.commit()
            logger.info(f"오래된 실행 로그 정리: {deleted_count}개 삭제")
    except Exception as e:
        logger.error(f"실행 로그 정리 실패: {e}")


def get_database_stats() -> dict:
    """
    데이터베이스 통계 정보를 반환합니다.
    
    Returns:
        dict: 데이터베이스 통계
    """
    try:
        with _conn() as conn:
            # 시나리오 개수
            scenario_count = conn.execute("SELECT COUNT(*) FROM scenario").fetchone()[0]
            
            # 실행 로그 개수
            runlog_count = conn.execute("SELECT COUNT(*) FROM runlog").fetchone()[0]
            
            # 데이터베이스 파일 크기
            db_size = os.path.getsize(settings.database_path) if os.path.exists(settings.database_path) else 0
            
            return {
                "scenario_count": scenario_count,
                "runlog_count": runlog_count,
                "database_size_bytes": db_size,
                "database_size_mb": round(db_size / (1024 * 1024), 2),
                "database_path": settings.database_path
            }
    except Exception as e:
        logger.error(f"데이터베이스 통계 조회 실패: {e}")
        return {}


def _ensure_database_integrity(verbose: bool = True):
    """데이터베이스 무결성을 확인하고 빈 데이터베이스를 올바르게 처리합니다."""
    try:
        # 시나리오 목록 조회 테스트
        scenario_ids = list_ids()
        
        if scenario_ids is None or len(scenario_ids) == 0:
            if verbose:
                logger.info("빈 데이터베이스 감지 - 기본 설정을 확인합니다.")
            _setup_empty_database(verbose)
        else:
            if verbose:
                logger.info(f"기존 시나리오 {len(scenario_ids)}개 발견됨")
                
    except Exception as e:
        if verbose:
            logger.warning(f"데이터베이스 무결성 확인 중 오류: {str(e)}")
            logger.info("데이터베이스 기본 설정을 재초기화합니다.")
        _setup_empty_database(verbose)


def _setup_empty_database(verbose: bool = True):
    """빈 데이터베이스에 대한 기본 설정을 수행합니다."""
    try:
        # 리스트 조회 테스트
        test_ids = list_ids()
        if test_ids is None:
            if verbose:
                logger.warning("빈 데이터베이스에서 시나리오 리스트 조회가 None을 반환함")
        else:
            if verbose:
                logger.info(f"빈 데이터베이스 시나리오 리스트 조회 성공: {len(test_ids)}개")
        
        if verbose:
            logger.info("✅ 빈 데이터베이스 기본 설정 완료")
            logger.info("📋 빈 데이터베이스에서 MCP 도구 호출 시 에러가 발생하지 않도록 설정됨")
        
    except Exception as e:
        if verbose:
            logger.error(f"빈 데이터베이스 설정 중 오류: {str(e)}")
        # 에러가 발생해도 계속 진행
        pass


# 데이터베이스 초기화 (모듈 로드 시 자동 실행)
try:
    init_db()
except Exception as e:
    logger.error(f"데이터베이스 자동 초기화 실패: {e}")
    # 애플리케이션 시작 시 수동으로 다시 시도할 수 있도록 에러를 삼킴 