"""
Scenario management service

시나리오 등록, 조회, 수정, 삭제 등 시나리오 관리와 관련된 모든 비즈니스 로직을 담당합니다.
main.py의 시나리오 관련 MCP 도구들의 백엔드 로직을 제공합니다.
"""

import json
import os
import yaml
import glob
from typing import Any, Dict, List, Optional

from config.logging_config import get_logger
from database.models import ScenarioDoc
from database.manager import save_scenario, load_scenario, update_scenario_partial, delete_scenario, list_ids
from validation import normalize_input_form

logger = get_logger("services.scenario")


class ScenarioService:
    """
    시나리오 관리 서비스
    
    시나리오의 생성, 조회, 수정, 삭제 및 YAML 가져오기/내보내기 기능을 제공합니다.
    """
    
    def __init__(self):
        """ScenarioService 초기화"""
        self.logger = logger
    
    def get_scenario(self, sid: str) -> Dict[str, Any]:
        """
        특정 시나리오 조회
        
        Args:
            sid: 시나리오 ID
            
        Returns:
            Dict[str, Any]: 시나리오 데이터 또는 빈 딕셔너리
        """
        self.logger.info(f"시나리오 조회: {sid}")
        doc = load_scenario(sid)
        if doc:
            return json.loads(doc.to_json())
        else:
            self.logger.warning(f"시나리오 {sid}를 찾을 수 없음")
            return {}
    
    def list_scenarios(self) -> List[str]:
        """
        모든 시나리오 ID 목록 조회
        
        Returns:
            List[str]: 시나리오 ID 목록
        """
        self.logger.info("시나리오 목록 조회")
        return list_ids()
    
    def register_scenario(self, scenario: Dict[str, Any]) -> Dict[str, Any]:
        """
        새로운 시나리오 등록
        
        Args:
            scenario: 시나리오 데이터
            
        Returns:
            Dict[str, Any]: 등록 결과
        """
        try:
            # 입력 데이터 정규화
            if "scenario" in scenario:
                normalized_scenario = normalize_input_form(scenario)
            else:
                normalized_scenario = normalize_input_form({"scenario": scenario})
            
            sid = normalized_scenario.get("meta", {}).get("id")
            if not sid:
                return {"error": "meta.id 필드는 필수입니다."}
            
            # 중복 확인
            if load_scenario(sid):
                return {"error": f"시나리오 {sid}가 이미 존재합니다."}
            
            # 시나리오 저장
            scenario_doc = ScenarioDoc.from_json(json.dumps(normalized_scenario))
            success = save_scenario(scenario_doc)
            
            if success:
                self.logger.info(f"시나리오 등록 완료: {sid}")
                return {
                    "success": True, 
                    "message": f"시나리오 {sid}가 등록되었습니다.",
                    "schema_version": "1.4",
                    "supported_extensions": [
                        "attack_vectors", "vulnerable_functions", "vulnerability_pattern",
                        "vulnerability_details", "mitigation"
                    ]
                }
            else:
                return {"error": f"시나리오 {sid} 저장에 실패했습니다."}
                
        except Exception as e:
            error_msg = f"시나리오 등록 중 오류 발생: {str(e)}"
            self.logger.error(error_msg)
            return {"error": error_msg}
    
    def update_scenario(self, sid: str, update_dict: Dict[str, Any]) -> Dict[str, Any]:
        """
        시나리오 부분 업데이트
        
        Args:
            sid: 시나리오 ID
            update_dict: 업데이트할 필드와 값
            
        Returns:
            Dict[str, Any]: 업데이트 결과
        """
        doc = load_scenario(sid)
        if not doc:
            return {"error": f"시나리오 {sid}가 존재하지 않습니다."}

        # meta 또는 spec 필드 수정 제한
        if "meta" in update_dict or "spec" in update_dict:
            disallowed_keys = [k for k in ["meta", "spec"] if k in update_dict]
            return {
                "error": f"시나리오의 핵심 정의인 '{', '.join(disallowed_keys)}' 필드는 수정할 수 없습니다. "
                        "'hints', 'patches', 'runlog', 'extras', 'test_insights', 'test_code_snapshots' 필드만 업데이트 가능합니다."
            }

        try:
            # 업데이트 수행
            success = update_scenario_partial(sid, update_dict)
            if success:
                self.logger.info(f"시나리오 업데이트 완료: {sid}")
                return {"success": True, "message": f"시나리오 {sid}가 업데이트되었습니다."}
            else:
                return {"error": f"시나리오 {sid} 업데이트에 실패했습니다."}
                
        except Exception as e:
            error_msg = f"시나리오 업데이트 중 오류: {str(e)}"
            self.logger.error(error_msg)
            return {"error": error_msg}
    
    def delete_scenario(self, sid: str) -> Dict[str, Any]:
        """
        시나리오 삭제
        
        Args:
            sid: 시나리오 ID
            
        Returns:
            Dict[str, Any]: 삭제 결과
        """
        try:
            success = delete_scenario(sid)
            if success:
                self.logger.info(f"시나리오 삭제 완료: {sid}")
                return {"success": True, "message": f"시나리오 {sid}가 삭제되었습니다."}
            else:
                return {"error": f"시나리오 {sid}가 존재하지 않거나 삭제에 실패했습니다."}
                
        except Exception as e:
            error_msg = f"시나리오 삭제 중 오류: {str(e)}"
            self.logger.error(error_msg)
            return {"error": error_msg}
    
    def export_scenario_to_yaml(self, sid: str, path: str) -> Dict[str, Any]:
        """
        시나리오를 YAML 파일로 내보내기
        
        Args:
            sid: 시나리오 ID
            path: 출력 파일 경로
            
        Returns:
            Dict[str, Any]: 내보내기 결과
        """
        try:
            doc = load_scenario(sid)
            if not doc:
                return {"error": "해당 시나리오가 없습니다."}
            
            with open(path, "w", encoding="utf-8") as f:
                yaml.dump(json.loads(doc.to_json()), f, allow_unicode=True)
            
            self.logger.info(f"시나리오 {sid}를 {path}로 export 완료")
            return {"success": True, "message": f"시나리오 {sid}를 {path}로 내보냈습니다."}
            
        except Exception as e:
            error_msg = f"YAML 내보내기 중 오류: {str(e)}"
            self.logger.error(error_msg)
            return {"error": error_msg}
    
    def bootstrap_from_yaml_files(self, folder: str = "scenarios") -> Dict[str, Any]:
        """
        YAML 파일들로부터 시나리오 일괄 등록
        
        Args:
            folder: YAML 파일들이 있는 폴더 경로
            
        Returns:
            Dict[str, Any]: 일괄 등록 결과
        """
        success_files, failed_files = [], []
        
        try:
            yaml_files = glob.glob(os.path.join(folder, "*.yaml"))
            if not yaml_files:
                return {"error": f"폴더 {folder}에 YAML 파일이 없습니다."}
            
            for file_path in yaml_files:
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        raw_data = yaml.safe_load(f)
                    
                    doc = ScenarioDoc.from_json(json.dumps(raw_data))
                    success = save_scenario(doc)
                    
                    if success:
                        success_files.append(os.path.basename(file_path))
                    else:
                        failed_files.append({
                            "file": os.path.basename(file_path), 
                            "error": "저장 실패"
                        })
                        
                except Exception as e:
                    self.logger.error(f"파일 처리 오류: {file_path} - {e}")
                    failed_files.append({
                        "file": os.path.basename(file_path), 
                        "error": str(e)
                    })
            
            self.logger.info(f"일괄 등록 완료: {len(success_files)} 성공, {len(failed_files)} 실패")
            
            return {
                "success": True,
                "success_count": len(success_files),
                "failed_count": len(failed_files),
                "success_files": success_files,
                "failed_files": failed_files
            }
            
        except Exception as e:
            error_msg = f"일괄 등록 중 오류: {str(e)}"
            self.logger.error(error_msg)
            return {"error": error_msg}
    
    def get_scenario_context(self, sid: str, test_contract_name: str, foundry_root_path: str) -> Dict[str, Any]:
        """
        시나리오 컨텍스트 조회 (순차적 검증 프로세스 1단계)
        
        Args:
            sid: 시나리오 ID
            test_contract_name: 테스트 컨트랙트 이름
            foundry_root_path: Foundry 프로젝트 경로
            
        Returns:
            Dict[str, Any]: 시나리오 전체 컨텍스트
        """
        self.logger.info(f"시나리오 컨텍스트 조회: sid={sid}, test_contract={test_contract_name}, foundry_root={foundry_root_path}")
        
        # 1. 시나리오 ID 검증
        if not sid or not sid.strip():
            return {
                "error": "시나리오 ID가 비어있습니다.",
                "details": "유효한 시나리오 ID를 제공해주세요.",
                "sid": sid
            }
        
        # 2. Foundry 프로젝트 경로 검증
        if not foundry_root_path or not foundry_root_path.strip():
            return {
                "error": "Foundry 프로젝트 경로가 비어있습니다.",
                "details": "유효한 Foundry 프로젝트 디렉토리 경로를 제공해주세요.",
                "foundry_root_path": foundry_root_path
            }
        
        if not os.path.exists(foundry_root_path):
            return {
                "error": f"Foundry 프로젝트 디렉토리가 존재하지 않습니다: {foundry_root_path}",
                "details": "디렉토리 경로를 확인하거나 프로젝트를 초기화해주세요.",
                "foundry_root_path": foundry_root_path
            }
        
        # foundry.toml 파일 확인 (Foundry 프로젝트인지 검증)
        foundry_toml_path = os.path.join(foundry_root_path, "foundry.toml")
        if not os.path.exists(foundry_toml_path):
            return {
                "error": f"유효한 Foundry 프로젝트가 아닙니다: {foundry_root_path}",
                "details": "foundry.toml 파일이 없습니다. 'forge init' 명령으로 프로젝트를 초기화해주세요.",
                "foundry_root_path": foundry_root_path,
                "missing_file": foundry_toml_path
            }
        
        # 3. 시나리오 DB 조회
        try:
            doc = load_scenario(sid)
            if not doc:
                self.logger.warning(f"시나리오 {sid} DB에서 찾을 수 없음")
                return {
                    "error": f"시나리오 '{sid}'를 DB에서 찾을 수 없습니다.",
                    "details": "시나리오가 등록되지 않았습니다. register_scenario 도구를 사용하여 먼저 시나리오를 등록하세요.",
                    "sid": sid,
                    "suggestion": "최초 유닛테스트 분석 시에는 먼저 테스트 코드를 직접 검토한 후 register_scenario로 시나리오를 등록해야 합니다."
                }
            
            # 4. 성공 시 컨텍스트 반환
            context_data = json.loads(doc.to_json())
            self.logger.info(f"시나리오 {sid} 컨텍스트 조회 성공. 데이터 크기: {len(str(context_data))} 문자")
            
            return context_data
            
        except Exception as e:
            error_msg = f"시나리오 컨텍스트 조회 중 데이터베이스 오류: {str(e)}"
            self.logger.error(error_msg)
            return {
                "error": error_msg,
                "details": "DB 연결 또는 데이터 로드 중 오류가 발생했습니다.",
                "sid": sid,
                "exception_type": type(e).__name__
            } 