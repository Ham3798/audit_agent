import inspect
import traceback
from typing import List, Dict, Any, Type, Optional

from slither import Slither
from slither.detectors import all_detectors
from slither.detectors.abstract_detector import AbstractDetector, DetectorClassification
from crytic_compile import CryticCompile, InvalidCompilation

from .state import AuditState

def run_slither_analysis(state: AuditState) -> dict:
    """CryticCompile 인스턴스를 사용하여 Slither 정적 분석을 실행합니다."""
    print("--- Slither 정적 분석 시작 ---")
    compile_instance = state.get("compile_instance")
    repo_analysis = state.get("repo_analysis", {}) # repo_analysis 가져오기

    if not compile_instance:
        compile_status = repo_analysis.get("compile_status", "unknown")
        err_msg = f"Slither 분석 실패: 유효한 CryticCompile 인스턴스가 없습니다 (이전 단계 상태: {compile_status})."
        print(f"  ! {err_msg}")
        # compile_instance가 없으므로 None 반환
        return {"slither_results": None, "error": err_msg, "compile_instance": None}

    compile_status = repo_analysis.get("compile_status", "unknown")
    if compile_status not in ["success", "success_info_error"]:
         err_msg = f"Slither 분석 건너<0xEB><0x9C><0x84>: 컴파일 실패 (상태: {compile_status})"
         print(f"  ! {err_msg}")
         # 실패 시 compile_instance는 None으로 반환
         return {"slither_results": None, "error": err_msg, "compile_instance": None}

    slither_results: List[Dict[str, Any]] = []
    slither_errors: List[str] = []
    final_error: Optional[str] = None # 최종 에러 메시지

    try:
        print(f"  > Slither 인스턴스 생성 (CryticCompile 객체 사용)...")
        slither = Slither(compile_instance)

        print("  > 사용 가능한 모든 Detector 등록...")
        detector_classes = [d for d in vars(all_detectors).values()
                          if inspect.isclass(d) and issubclass(d, AbstractDetector) and d != AbstractDetector]
        for detector_cls in detector_classes:
            slither.register_detector(detector_cls)

        print("  > Detector 실행...")
        results = slither.run_detectors()

        flat_results = [item for sublist in results if sublist for item in sublist]
        print(f"  > 총 {len(flat_results)}개의 결과 발견.")

        for res in flat_results:
            element_details = []
            if 'elements' in res:
                for elem in res['elements']:
                    detail = {
                        "type": elem.get('type', 'N/A'),
                        "name": elem.get('name', 'N/A'),
                        "source_mapping": {
                            "filename": elem.get('source_mapping', {}).get('filename_relative', 'N/A'),
                            "lines": elem.get('source_mapping', {}).get('lines', [])
                        }
                    }
                    element_details.append(detail)
            formatted_res = {
                "check": res.get('check', 'N/A'),
                "impact": res.get('impact', 'N/A'),
                "confidence": res.get('confidence', 'N/A'),
                "description": res.get('description', 'N/A').strip(),
                "elements": element_details
            }
            slither_results.append(formatted_res)

        print("--- Slither 정적 분석 완료 ---")

    except Exception as e:
        err_msg = f"Slither 실행 중 예기치 않은 오류: {e}"
        print(f"  ! {err_msg}")
        traceback.print_exc()
        slither_errors.append(err_msg)
        final_error = "; ".join(slither_errors)

    # Slither 분석 완료 후 compile_instance를 None으로 설정하여 다음 노드로 전달 X
    return {"slither_results": slither_results, "error": final_error, "compile_instance": None}