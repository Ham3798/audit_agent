import os
from typing import Optional, List, Set, Dict, Any
from pathlib import Path
from crytic_compile import CryticCompile, InvalidCompilation
from crytic_compile.utils.naming import Filename # Filename 타입 임포트

from .state import AuditState

# --- Helper Functions for Information Extraction --- #

def _extract_framework(compile_instance: CryticCompile) -> Optional[str]:
    """CryticCompile 인스턴스에서 감지된 프레임워크 이름을 추출합니다."""
    try:
        if hasattr(compile_instance, 'platform') and compile_instance.platform:
            return compile_instance.platform.NAME
        if compile_instance.compilation_units:
            # 여러 컴파일 유닛이 있을 수 있으므로 첫 번째 유닛의 플랫폼을 대표로 사용
            first_unit = list(compile_instance.compilation_units.values())[0]
            if hasattr(first_unit, 'platform') and first_unit.platform:
                return first_unit.platform.NAME
    except Exception as e:
        print(f"  ! 프레임워크 추출 중 오류: {e}")
    return None

def _determine_artifacts_path(repo_path: str, framework: Optional[str]) -> Optional[str]:
    """감지된 프레임워크를 기반으로 아티팩트 경로를 결정합니다."""
    if not framework:
        return None

    paths = {
        'foundry': os.path.join(repo_path, 'out'),
        'hardhat': os.path.join(repo_path, 'artifacts'),
        # TODO: 다른 프레임워크 경로 추가
    }
    return paths.get(framework.lower())

def _extract_contract_names(compile_instance: CryticCompile) -> List[str]:
    """CryticCompile 인스턴스의 모든 컴파일 유닛에서 컨트랙트 이름을 추출하고 정렬합니다."""
    all_contract_names: Set[str] = set()
    try:
        if compile_instance and compile_instance.compilation_units:
            for unit in compile_instance.compilation_units.values():
                if hasattr(unit, 'source_units') and unit.source_units:
                    for source_unit in unit.source_units.values():
                        if hasattr(source_unit, 'contracts_names'):
                            all_contract_names.update(source_unit.contracts_names)
                        elif hasattr(source_unit, 'contracts'): # Fallback
                            all_contract_names.update(source_unit.contracts.keys())
    except Exception as e:
        print(f"  ! 컨트랙트 이름 추출 중 오류: {e}")
    return sorted(list(all_contract_names))

def _extract_compilation_unit_info(compile_instance: CryticCompile) -> Dict[str, Any]:
    """컴파일 단위 정보 (개수, 컴파일러 버전 등)를 추출합니다."""
    info = {"num_units": 0, "compiler_versions": set()}
    try:
        if compile_instance.compilation_units:
            info["num_units"] = len(compile_instance.compilation_units)
            for unit in compile_instance.compilation_units.values():
                # Solidity 컴파일러 버전 추출 시도
                if hasattr(unit, 'solc_version') and unit.solc_version:
                    info["compiler_versions"].add(f"solc-{unit.solc_version}")
                # Vyper 컴파일러 버전 추출 시도 (구조가 다를 수 있음, 예시)
                elif hasattr(unit, 'vyper_version') and unit.vyper_version:
                     info["compiler_versions"].add(f"vyper-{unit.vyper_version}")
                # TODO: 다른 컴파일러 타입 지원 추가
    except Exception as e:
        print(f"  ! 컴파일 단위 정보 추출 중 오류: {e}")
    # 집합(set)은 JSON 직렬화가 안되므로 리스트로 변환
    info["compiler_versions"] = sorted(list(info["compiler_versions"]))
    return info

def _extract_file_info(compile_instance: CryticCompile) -> Dict[str, List[str]]:
    """소스 파일 및 의존성 파일 목록을 추출합니다."""
    info = {"source_files": [], "dependencies": []}
    try:
        # Filename 객체에서 절대 경로 문자열만 추출
        all_files = [f.absolute for f in compile_instance.filenames]
        dependencies = [f for f in all_files if compile_instance.is_dependency(f)]
        source_files = [f for f in all_files if f not in dependencies]
        info["source_files"] = sorted(source_files)
        info["dependencies"] = sorted(dependencies)
    except Exception as e:
        print(f"  ! 파일 정보 추출 중 오류: {e}")
    return info

def _extract_project_properties(compile_instance: CryticCompile) -> Dict[str, Any]:
    """프로젝트 속성 (target, working_dir, bytecode_only, libraries)을 추출합니다."""
    properties = {
        "target": None,
        "working_dir": None,
        "bytecode_only": False,
        "linked_libraries": None
    }
    try:
        properties["target"] = compile_instance.target
        # Path 객체는 JSON 직렬화 안되므로 문자열로 변환
        properties["working_dir"] = str(compile_instance.working_dir)
        properties["bytecode_only"] = compile_instance.bytecode_only
        properties["linked_libraries"] = compile_instance.libraries
    except Exception as e:
        print(f"  ! 프로젝트 속성 추출 중 오류: {e}")
    return properties

# --- Main Analysis Function --- #

def analyze_repo_structure(state: AuditState) -> dict:
    """crytic-compile 라이브러리를 사용하여 리포지토리를 분석하고 컴파일합니다.
    자동 프레임워크 감지 및 컴파일을 시도하고, 성공 시 관련 정보를 추출합니다.
    """
    print("--- 리포지토리 분석 및 컴파일 시작 (crytic-compile 자동 감지) ---")
    repo_path = state.get("local_repo_path")
    if not repo_path or not os.path.isdir(repo_path):
        return {"error": "Repository path not valid or not found."}

    # 결과 저장을 위한 변수 초기화
    analysis_errors: List[str] = []
    compile_status: str = "pending"
    compile_instance: Optional[CryticCompile] = None
    detected_framework: Optional[str] = None
    artifacts_path: Optional[str] = None
    contract_names_list: List[str] = []
    compilation_unit_info: Dict[str, Any] = {"num_units": 0, "compiler_versions": []}
    file_info: Dict[str, List[str]] = {"source_files": [], "dependencies": []}
    project_properties: Dict[str, Any] = {
        "target": None,
        "working_dir": None,
        "bytecode_only": False,
        "linked_libraries": None
    }

    try:
        # 1. crytic-compile 라이브러리 실행
        print(f"  > crytic-compile 실행 (대상: {repo_path})...")
        try:
            compile_instance = CryticCompile(target=repo_path)
            compile_status = "success"
            print(f"\n  > crytic-compile 자동 감지 및 컴파일 성공.")

            # 2. 성공 시 정보 추출 (모든 영역 실행)
            print("  > 컴파일 성공, 상세 정보 추출 시작...")
            try:
                # 프레임워크 추출
                detected_framework = _extract_framework(compile_instance)
                print(f"    - 감지된 프레임워크: {detected_framework if detected_framework else '감지 불가'}")

                # 아티팩트 경로 결정
                artifacts_path = _determine_artifacts_path(repo_path, detected_framework)
                print(f"    - 아티팩트 경로: {artifacts_path if artifacts_path else '결정 불가'}")

                # 컨트랙트 이름 추출
                contract_names_list = _extract_contract_names(compile_instance)
                print(f"    - 컴파일된 총 컨트랙트 수: {len(contract_names_list)}")
                # print(f"    - 컴파일된 컨트랙트 (최대 5개): {contract_names_list[:5]}") # 로그 간결화 위해 주석 처리

                # 컴파일 단위 정보 추출
                compilation_unit_info = _extract_compilation_unit_info(compile_instance)
                print(f"    - 컴파일 단위 수: {compilation_unit_info['num_units']}")
                print(f"    - 사용된 컴파일러 버전: {compilation_unit_info['compiler_versions']}")

                # 파일 정보 추출
                file_info = _extract_file_info(compile_instance)
                print(f"    - 소스 파일 수: {len(file_info['source_files'])}")
                print(f"    - 의존성 파일 수: {len(file_info['dependencies'])}")
                # print(f"    - 소스 파일 목록 (최대 3개): {file_info['source_files'][:3]}") # 로그 간결화

                # 프로젝트 속성 추출
                project_properties = _extract_project_properties(compile_instance)
                print(f"    - 프로젝트 타겟: {project_properties['target']}")
                print(f"    - 작업 디렉토리: {project_properties['working_dir']}")
                print(f"    - 바이트코드만 존재: {project_properties['bytecode_only']}")
                print(f"    - 링크된 라이브러리: {project_properties['linked_libraries']}")

                # 사용 예시: 오프셋/라인 변환 유틸리티 (결과 상태에 저장하지는 않음)
                if file_info["source_files"]:
                    try:
                        first_file = compile_instance.filename_lookup(file_info["source_files"][0])
                        line_10_offset = compile_instance.get_global_offset_from_line(first_file, 10)
                        offset_100_line = compile_instance.get_line_from_offset(first_file, 100)
                        line_5_code = compile_instance.get_code_from_line(first_file, 5)
                        print(f"    - [유틸리티 예시] {first_file.relative}: line 10 offset={line_10_offset}, offset 100 line={offset_100_line}, line 5 code={line_5_code[:30]}..." if line_5_code else "")
                    except Exception as util_e:
                        print(f"    - [유틸리티 예시] 오류: {util_e}")

            except Exception as info_e:
                 err_msg = f"컴파일 성공 후 정보 추출 중 오류: {info_e}"
                 print(f"  ! {err_msg}")
                 analysis_errors.append(err_msg)
                 compile_status = "success_info_error"

        except InvalidCompilation as e:
            err_msg = f"CryticCompile 실패 (자동 감지): {e}"
            print(f"  ! {err_msg}")
            analysis_errors.append(err_msg)
            compile_status = "compile_failed"
        except Exception as e_other:
             err_msg = f"CryticCompile 실행 중 예기치 않은 예외 발생: {e_other}"
             print(f"  ! {err_msg}")
             analysis_errors.append(err_msg)
             compile_status = "compile_exception"

        # 3. 최종 결과 조합 (추가된 정보 포함)
        analysis_result = {
            "compile_status": compile_status,
            "framework": detected_framework,
            "artifacts_path": artifacts_path,
            "contracts": contract_names_list,
            "compiler_versions": compilation_unit_info["compiler_versions"],
            "num_compilation_units": compilation_unit_info["num_units"],
            "source_files": file_info["source_files"],
            "dependencies": file_info["dependencies"],
            "project_target": project_properties["target"],
            "working_directory": project_properties["working_dir"],
            "is_bytecode_only": project_properties["bytecode_only"],
            "linked_libraries": project_properties["linked_libraries"],
        }
        print(f"\n분석 및 컴파일 시도 완료: 최종 상태 = {compile_status}")
        # print(f"  최종 결과 요약: framework={analysis_result['framework']}, contracts={len(analysis_result['contracts'])}") # 로그 간결화

        return {"repo_analysis": analysis_result, "error": "; ".join(analysis_errors) if analysis_errors else None}

    except Exception as e:
        # 분석/컴파일 프로세스 자체의 치명적 오류 처리
        err_msg = f"리포지토리 분석/컴파일 중 치명적 오류: {e}"
        print(f"  ! {err_msg}")
        # 치명적 오류 시 반환되는 구조 업데이트
        default_analysis = {
            "compile_status": "fatal_error",
            "framework": None,
            "artifacts_path": None,
            "contracts": [],
            "compiler_versions": [],
            "num_compilation_units": 0,
            "source_files": [],
            "dependencies": [],
            "project_target": state.get("local_repo_path"), # 오류 시 repo_path 사용 시도
            "working_directory": str(Path.cwd()), # 오류 시 현재 작업 디렉토리
            "is_bytecode_only": False,
            "linked_libraries": None,
        }
        return {"repo_analysis": default_analysis, "error": err_msg} 