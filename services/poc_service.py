"""
PoC (Proof of Concept) service

PoC 코드 생성, LLM 자율적 개선, 테스트 향상 등 PoC 개발과 관련된 모든 비즈니스 로직을 담당합니다.
main.py의 PoC 관련 MCP 도구들의 백엔드 로직을 제공합니다.
"""

import os
import json
import datetime
from typing import Any, Dict, List, Optional

from config.logging_config import get_logger
from database.models import ScenarioDoc
from database.manager import save_scenario, load_scenario

logger = get_logger("services.poc")


class PocService:
    """
    PoC 개발 및 관리 서비스
    
    PoC 코드 생성, LLM 자율적 개선, 테스트 향상 등의 기능을 제공합니다.
    """
    
    def __init__(self):
        """PocService 초기화"""
        self.logger = logger
    
    def generate_poc_code(self, sid: str, foundry_root_path: str, poc_type: str = "contract") -> Dict[str, Any]:
        """
        독립적인 PoC 코드 생성
        
        Args:
            sid: 시나리오 ID
            foundry_root_path: Foundry 프로젝트 루트 경로
            poc_type: PoC 유형 ("contract", "script", "exploit")
            
        Returns:
            Dict[str, Any]: PoC 생성 결과
        """
        self.logger.info(f"PoC 코드 생성: sid={sid}, type={poc_type}")
        
        doc = load_scenario(sid)
        if not doc:
            return {"error": f"시나리오 {sid}가 존재하지 않습니다."}
        
        try:
            # 시나리오 데이터 분석
            scenario_data = json.loads(doc.to_json())
            meta = scenario_data.get("meta", {})
            spec = scenario_data.get("spec", {})
            code_info = scenario_data.get("code", {})
            hints = scenario_data.get("hints", {})
            
            # PoC 파일명 생성
            poc_id = meta.get("id", sid)
            file_extension = ".sol" if poc_type == "contract" else ".s.sol"
            poc_filename = f"{poc_id}_PoC{file_extension}"
            
            # 출력 디렉토리 결정
            if poc_type == "script":
                output_dir = os.path.join(foundry_root_path, "script")
            else:
                output_dir = os.path.join(foundry_root_path, "src", "exploits")
            
            # 디렉토리 생성
            os.makedirs(output_dir, exist_ok=True)
            
            # PoC 코드 생성
            poc_code = self._generate_poc_template(
                poc_type=poc_type,
                scenario_data=scenario_data,
                foundry_root_path=foundry_root_path
            )
            
            # 파일 저장
            file_path = os.path.join(output_dir, poc_filename)
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(poc_code)
            
            self.logger.info(f"PoC 코드 생성 완료: {file_path}")
            
            return {
                "success": True,
                "message": f"PoC 코드가 성공적으로 생성되었습니다.",
                "poc_code": poc_code,
                "file_path": file_path,
                "poc_type": poc_type,
                "dependencies": self._extract_dependencies(poc_code)
            }
        except Exception as e:
            error_msg = f"PoC 코드 생성 중 오류: {str(e)}"
            self.logger.error(error_msg)
            return {"error": error_msg}
    
    def llm_generate_test_improvement(self, sid: str, improvement_plan: str, foundry_root_path: str) -> Dict[str, Any]:
        """
        LLM 자율적 검증 - 2단계: 테스트 개선사항 코드에 적용
        
        Args:
            sid: 시나리오 ID
            improvement_plan: LLM이 생성한 개선 계획 (JSON 문자열)
            foundry_root_path: Foundry 프로젝트 경로
            
        Returns:
            Dict[str, Any]: 개선 적용 결과
        """
        self.logger.info(f"LLM 테스트 개선 적용: sid={sid}")
        
        doc = load_scenario(sid)
        if not doc:
            return {"error": f"시나리오 {sid}가 존재하지 않습니다."}
        
        try:
            # 개선 계획 파싱
            try:
                plan = json.loads(improvement_plan)
            except json.JSONDecodeError:
                return {"error": "improvement_plan이 유효한 JSON 형식이 아닙니다."}
            
            # 필수 필드 확인
            required_fields = ["analysis_summary", "new_test_functions", "modification_reason", "expected_improvement"]
            missing_fields = [field for field in required_fields if field not in plan]
            
            if missing_fields:
                return {"error": f"개선 계획에 다음 필드가 누락되었습니다: {missing_fields}"}
            
            # 새로운 테스트 함수 코드 추출
            new_test_code = plan["new_test_functions"]
            
            # 테스트 파일 경로 결정
            test_file_name = f"{sid}_Enhanced.t.sol"
            test_file_path = os.path.join(foundry_root_path, "test", "generated", test_file_name)
            
            # generated 디렉토리 생성
            os.makedirs(os.path.dirname(test_file_path), exist_ok=True)
            
            # 기존 테스트와 통합하여 새로운 테스트 파일 생성
            enhanced_test_code = self._create_enhanced_test_file(
                sid=sid,
                scenario_data=json.loads(doc.to_json()),
                new_test_code=new_test_code,
                foundry_root_path=foundry_root_path
            )
            
            # 파일 저장
            with open(test_file_path, "w", encoding="utf-8") as f:
                f.write(enhanced_test_code)
            
            # 개선 내역을 시나리오에 기록
            doc.add_patch(
                author="llm_autonomous",
                reason=plan["modification_reason"],
                diff_text=f"새로운 향상된 테스트 파일 생성: {test_file_name}"
            )
            
            # 테스트 코드 스냅샷 업데이트
            contract_name = test_file_name.replace(".t.sol", "")
            doc.test_code_snapshots[contract_name] = enhanced_test_code
            
            # extras에 개선 이력 저장
            if "llm_improvements" not in doc.extras:
                doc.extras["llm_improvements"] = []
            
            doc.extras["llm_improvements"].append({
                "timestamp": str(datetime.datetime.now()),
                "analysis_summary": plan["analysis_summary"],
                "expected_improvement": plan["expected_improvement"],
                "test_file": test_file_name
            })
            
            save_scenario(doc)
            
            self.logger.info(f"LLM 테스트 개선 적용 완료: {test_file_path}")
            
            return {
                "success": True,
                "message": "테스트 개선사항이 성공적으로 적용되었습니다.",
                "test_file_path": test_file_path,
                "enhanced_test_code": enhanced_test_code,
                "improvement_summary": plan["analysis_summary"],
                "expected_improvement": plan["expected_improvement"]
            }
        except Exception as e:
            error_msg = f"LLM 테스트 개선 적용 중 오류: {str(e)}"
            self.logger.error(error_msg)
            return {"error": error_msg}
    
    def llm_autonomous_verification_cycle(self, sid: str, foundry_root_path: str) -> Dict[str, Any]:
        """
        LLM 자율적 검증 사이클 시작
        
        Args:
            sid: 시나리오 ID
            foundry_root_path: Foundry 프로젝트 루트 경로
            
        Returns:
            Dict[str, Any]: 자율적 사이클 시작 정보 및 LLM 가이드
        """
        self.logger.info(f"LLM 자율적 검증 사이클 시작: sid={sid}")
        
        doc = load_scenario(sid)
        if not doc:
            return {"error": f"시나리오 {sid}가 존재하지 않습니다."}
        
        try:
            # 현재 상황 분석 데이터 수집
            scenario_data = json.loads(doc.to_json())
            
            # 분석 데이터 구성
            initial_analysis_data = {
                "scenario_overview": {
                    "id": scenario_data.get("meta", {}).get("id"),
                    "title": scenario_data.get("meta", {}).get("title"),
                    "category": scenario_data.get("meta", {}).get("category"),
                    "severity": scenario_data.get("meta", {}).get("severity")
                },
                "current_tests": {
                    "total_tests": len(doc.unit_tests),
                    "test_list": [test.get("test_name", "") for test in doc.unit_tests]
                },
                "execution_history": {
                    "total_runs": len(doc.runlog),
                    "recent_runs": doc.runlog[-5:] if doc.runlog else [],
                    "success_rate": self._calculate_success_rate(doc.runlog)
                },
                "current_insights": {
                    "total_insights": len(doc.test_insights),
                    "latest_insights": doc.test_insights[-3:] if doc.test_insights else []
                },
                "coverage_assessment": self._assess_test_coverage(scenario_data, doc)
            }
            
            # LLM을 위한 자율적 실행 지침
            llm_instructions = {
                "phase": "autonomous_verification_cycle",
                "next_steps": [
                    "1. initial_analysis_data를 분석하여 현재 PoC 완성도 평가",
                    "2. 부족한 테스트 케이스나 공격 벡터 식별",
                    "3. llm_generate_test_improvement로 개선 계획 수립 및 적용",
                    "4. execute_unit_test로 새로운 테스트 검증",
                    "5. analyze_test_results로 결과 분석",
                    "6. 추가 개선이 필요하면 사이클 반복",
                    "7. 완성도가 충분하면 generate_poc_code로 최종 PoC 생성"
                ],
                "success_criteria": {
                    "minimum_test_coverage": "핵심 공격 벡터별 최소 1개 테스트",
                    "success_rate_threshold": 0.8,
                    "insight_depth": "보안 영향 분석 포함된 인사이트 3개 이상"
                },
                "autonomous_decision_points": [
                    "현재 테스트 커버리지가 충분한가?",
                    "발견된 취약점의 심각도가 제대로 검증되었는가?",
                    "추가 공격 시나리오가 필요한가?",
                    "PoC 코드 생성을 위한 충분한 인사이트가 축적되었는가?"
                ]
            }
            
            self.logger.info(f"자율적 검증 사이클 시작 준비 완료: sid={sid}")
            
            return {
                "cycle_started": True,
                "initial_analysis_data": initial_analysis_data,
                "llm_instructions": llm_instructions,
                "success": True,
                "message": "LLM 자율적 검증 사이클이 시작되었습니다. 제공된 지침에 따라 진행하세요."
            }
        except Exception as e:
            error_msg = f"자율적 검증 사이클 시작 중 오류: {str(e)}"
            self.logger.error(error_msg)
            return {"error": error_msg}
    
    def _generate_poc_template(self, poc_type: str, scenario_data: Dict[str, Any], foundry_root_path: str) -> str:
        """
        PoC 템플릿 생성
        
        Args:
            poc_type: PoC 유형
            scenario_data: 시나리오 데이터
            foundry_root_path: Foundry 프로젝트 경로
            
        Returns:
            str: 생성된 PoC 코드
        """
        meta = scenario_data.get("meta", {})
        spec = scenario_data.get("spec", {})
        code_info = scenario_data.get("code", {})
        
        poc_id = meta.get("id", "UnknownPoC")
        title = meta.get("title", "Unknown Vulnerability")
        category = meta.get("category", "Unknown")
        
        if poc_type == "contract":
            return self._generate_contract_poc(poc_id, title, category, scenario_data)
        elif poc_type == "script":
            return self._generate_script_poc(poc_id, title, category, scenario_data)
        elif poc_type == "exploit":
            return self._generate_exploit_poc(poc_id, title, category, scenario_data)
        else:
            return self._generate_contract_poc(poc_id, title, category, scenario_data)
    
    def _generate_contract_poc(self, poc_id: str, title: str, category: str, scenario_data: Dict[str, Any]) -> str:
        """독립적인 공격 컨트랙트 PoC 생성"""
        vulnerable_functions = scenario_data.get("code", {}).get("vulnerable_functions", [])
        attack_vectors = scenario_data.get("spec", {}).get("attack_vectors", [])
        
        return f'''// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

/**
 * @title {poc_id} - {title}
 * @notice {category} vulnerability PoC
 * @dev 독립적인 공격 컨트랙트
 */

import "forge-std/Test.sol";
import "forge-std/console.sol";

contract {poc_id}_PoC is Test {{
    
    // 취약한 컨트랙트 인터페이스 (실제 프로젝트에 맞게 수정 필요)
    interface IVulnerableContract {{
        // 취약한 함수들: {", ".join(vulnerable_functions) if vulnerable_functions else "함수 정보 없음"}
        // TODO: 실제 취약한 컨트랙트의 인터페이스로 교체
    }}
    
    // 공격자 주소
    address attacker = makeAddr("attacker");
    address victim = makeAddr("victim");
    
    // 컨트랙트 인스턴스
    IVulnerableContract vulnerableContract;
    
    function setUp() public {{
        // TODO: 취약한 컨트랙트 배포 및 초기화
        // vulnerableContract = IVulnerableContract(address(...));
        
        console.log("=== {title} PoC Setup ===");
        console.log("Attacker:", attacker);
        console.log("Victim:", victim);
    }}
    
    /**
     * @dev 주요 공격 시나리오
     * 공격 벡터: {", ".join(attack_vectors) if attack_vectors else "공격 벡터 정보 없음"}
     */
    function test_MainExploit() public {{
        vm.startPrank(attacker);
        
        console.log("\\n=== {category} 공격 시작 ===");
        
        // TODO: 공격 로직 구현
        // 1. 초기 상태 확인
        // 2. 공격 실행
        // 3. 결과 검증
        
        console.log("공격 성공!");
        
        vm.stopPrank();
    }}
    
    /**
     * @dev 공격 전후 상태 비교
     */
    function test_StateComparison() public {{
        // TODO: 공격 전후 상태 변화 확인
        console.log("\\n=== 상태 변화 분석 ===");
    }}
    
    /**
     * @dev 방어 메커니즘 우회 테스트
     */
    function test_DefenseBypass() public {{
        // TODO: 방어 메커니즘 우회 시나리오
        console.log("\\n=== 방어 우회 테스트 ===");
    }}
}}

/**
 * 사용법:
 * forge test --match-contract {poc_id}_PoC -vvvv
 * 
 * 주의사항:
 * 1. IVulnerableContract를 실제 취약한 컨트랙트 인터페이스로 교체
 * 2. setUp()에서 실제 컨트랙트 배포 로직 구현
 * 3. 각 테스트 함수에 실제 공격 로직 구현
 * 4. 테스트넷에서만 사용하고 메인넷에서는 절대 실행 금지
 */'''
    
    def _generate_script_poc(self, poc_id: str, title: str, category: str, scenario_data: Dict[str, Any]) -> str:
        """Foundry 배포 스크립트 PoC 생성"""
        return f'''// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

import "forge-std/Script.sol";
import "forge-std/console.sol";

/**
 * @title {poc_id} Deployment Script
 * @notice {title} 배포 및 실행 스크립트
 */
contract {poc_id}_Script is Script {{
    
    function run() public {{
        uint256 deployerPrivateKey = vm.envUint("PRIVATE_KEY");
        vm.startBroadcast(deployerPrivateKey);
        
        console.log("=== {title} 배포 스크립트 ===");
        
        // TODO: PoC 컨트랙트 배포 로직
        
        vm.stopBroadcast();
    }}
}}

/**
 * 사용법:
 * forge script script/{poc_id}_PoC.s.sol --rpc-url <RPC_URL> --broadcast
 */'''
    
    def _generate_exploit_poc(self, poc_id: str, title: str, category: str, scenario_data: Dict[str, Any]) -> str:
        """완전한 exploit 시나리오 PoC 생성"""
        return f'''// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

import "forge-std/Test.sol";
import "forge-std/console.sol";

/**
 * @title {poc_id} Complete Exploit
 * @notice {title} 완전한 exploit 시나리오
 */
contract {poc_id}_Exploit is Test {{
    
    // 공격자 컨트랙트
    contract Exploiter {{
        // TODO: 실제 공격 로직 구현
        
        function exploit() external {{
            // 공격 실행
        }}
    }}
    
    function test_FullExploit() public {{
        console.log("=== {title} 완전한 공격 시나리오 ===");
        
        // TODO: 전체 시나리오 구현
    }}
}}'''
    
    def _extract_dependencies(self, poc_code: str) -> List[str]:
        """PoC 코드에서 의존성 추출"""
        dependencies = []
        
        # import 문에서 의존성 추출
        lines = poc_code.split('\n')
        for line in lines:
            if line.strip().startswith('import'):
                dependencies.append(line.strip())
        
        return dependencies
    
    def _create_enhanced_test_file(self, sid: str, scenario_data: Dict[str, Any], new_test_code: str, foundry_root_path: str) -> str:
        """향상된 테스트 파일 생성"""
        meta = scenario_data.get("meta", {})
        title = meta.get("title", "Enhanced Test")
        
        return f'''// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

import "forge-std/Test.sol";
import "forge-std/console.sol";

/**
 * @title {sid} Enhanced Tests
 * @notice {title} - LLM 자율적 개선된 테스트
 */
contract {sid}_Enhanced is Test {{
    
    function setUp() public {{
        // TODO: 테스트 환경 설정
    }}
    
    // LLM이 생성한 새로운 테스트 함수들
{new_test_code}
    
}}'''
    
    def _calculate_success_rate(self, runlog: List[Dict[str, Any]]) -> float:
        """테스트 성공률 계산"""
        if not runlog:
            return 0.0
        
        success_count = sum(1 for log in runlog if log.get("status") == "SUCCESS")
        return success_count / len(runlog)
    
    def _assess_test_coverage(self, scenario_data: Dict[str, Any], doc: ScenarioDoc) -> Dict[str, Any]:
        """테스트 커버리지 평가"""
        spec = scenario_data.get("spec", {})
        attack_vectors = spec.get("attack_vectors", [])
        vulnerable_functions = scenario_data.get("code", {}).get("vulnerable_functions", [])
        
        coverage_assessment = {
            "attack_vectors_total": len(attack_vectors),
            "vulnerable_functions_total": len(vulnerable_functions),
            "current_tests": len(doc.unit_tests),
            "test_coverage_ratio": len(doc.unit_tests) / max(len(attack_vectors), 1),
            "has_insights": len(doc.test_insights) > 0,
            "recommendation": "충분" if len(doc.unit_tests) >= len(attack_vectors) else "부족"
        }
        
        return coverage_assessment 