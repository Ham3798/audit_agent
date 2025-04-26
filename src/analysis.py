import os
import re # 정규 표현식 모듈 임포트
from typing import Optional, List, Set, Dict, Any
from pathlib import Path
from crytic_compile import CryticCompile, InvalidCompilation
from crytic_compile.utils.naming import Filename # Filename 타입 임포트
from crytic_compile.compilation_unit import CompilationUnit # CompilationUnit 타입 명시적 임포트
from crytic_compile.platform.abstract_platform import AbstractPlatform # 플랫폼 타입 참조용
# CompilerVersion 클래스를 임포트 시도, 실패 시 대비
try:
    from crytic_compile.compiler.compiler import CompilerVersion
except ImportError:
    CompilerVersion = None # 임포트 실패 시 None으로 설정

from .state import AuditState

# --- Helper Functions for Information Extraction --- #

def _extract_platform_info(compile_instance: CryticCompile) -> Dict[str, Any]:
    """CryticCompile 인스턴스에서 플랫폼 이름과 타입을 추출합니다."""
    info = {"name": None, "type": None}
    try:
        platform_obj = None
        if hasattr(compile_instance, 'platform') and compile_instance.platform:
            platform_obj = compile_instance.platform
        elif compile_instance.compilation_units:
            # 여러 유닛 중 첫 번째 유닛의 플랫폼 사용 (일관성 가정)
            first_unit = list(compile_instance.compilation_units.values())[0]
            if hasattr(first_unit, 'platform') and first_unit.platform:
                platform_obj = first_unit.platform

        if platform_obj and isinstance(platform_obj, AbstractPlatform):
            info["name"] = platform_obj.NAME
            if hasattr(platform_obj, 'TYPE') and platform_obj.TYPE:
                 info["type"] = platform_obj.TYPE.name # Enum의 이름으로 저장
                 # info["type_value"] = platform_obj.TYPE.value # 필요시 값도 저장
        else:
            print("  ! 플랫폼 정보 객체를 찾을 수 없습니다.")

    except Exception as e:
        print(f"  ! 플랫폼 정보 추출 중 오류: {e}")
    return info

def _determine_artifacts_path(repo_path: str, platform_name: Optional[str]) -> Optional[str]:
    """감지된 플랫폼 이름을 기반으로 아티팩트 경로를 결정합니다."""
    if not platform_name:
        return None
    # 프레임워크 이름을 소문자로 비교
    framework_lower = platform_name.lower()
    paths = {
        'foundry': os.path.join(repo_path, 'out'),
        'hardhat': os.path.join(repo_path, 'artifacts'),
        'truffle': os.path.join(repo_path, 'build', 'contracts'), # Truffle 예시 추가
        'brownie': os.path.join(repo_path, 'build', 'contracts'), # Brownie 예시 추가
        # TODO: 다른 프레임워크 경로 추가 (Dapptools, Waffle 등)
    }
    # 기본 경로 외에 일반적인 build/contracts 경로도 확인
    default_build_path = os.path.join(repo_path, 'build', 'contracts')
    if framework_lower in paths:
        return paths[framework_lower]
    elif os.path.exists(default_build_path):
         print(f"  ? 알려지지 않은 프레임워크 '{platform_name}' 이지만, 일반적인 'build/contracts' 경로 발견.")
         return default_build_path
    else:
         # 'out' 또는 'artifacts'가 존재하는지 확인 (Foundry/Hardhat 기본)
         out_path = os.path.join(repo_path, 'out')
         artifacts_path_alt = os.path.join(repo_path, 'artifacts')
         if os.path.exists(out_path):
             print(f"  ? 알려지지 않은 프레임워크 '{platform_name}' 이지만, 'out' 디렉토리 발견.")
             return out_path
         elif os.path.exists(artifacts_path_alt):
              print(f"  ? 알려지지 않은 프레임워크 '{platform_name}' 이지만, 'artifacts' 디렉토리 발견.")
              return artifacts_path_alt

    print(f"  ! 프레임워크 '{platform_name}'에 대한 아티팩트 경로를 결정할 수 없음.")
    return None

def _extract_contract_names(compile_instance: CryticCompile) -> List[str]:
    """CryticCompile 인스턴스의 모든 컴파일 유닛에서 컨트랙트 이름을 추출하고 정렬합니다."""
    all_contract_names: Set[str] = set()
    try:
        if compile_instance and compile_instance.compilation_units:
            for unit in compile_instance.compilation_units.values():
                # 1. contracts_by_source_unit 속성 확인 (최신 crytic-compile 방식 추정)
                if hasattr(unit, 'contracts_by_source_unit'):
                    for contracts_in_source in unit.contracts_by_source_unit.values():
                         all_contract_names.update(contracts_in_source)
                # 2. source_units 속성 확인 (기존 방식)
                elif hasattr(unit, 'source_units') and unit.source_units:
                    for source_unit in unit.source_units.values():
                        if hasattr(source_unit, 'contracts_names'):
                            all_contract_names.update(source_unit.contracts_names)
                        elif hasattr(source_unit, 'contracts'): # Fallback
                            all_contract_names.update(source_unit.contracts.keys())
                # 3. 최후의 수단: contracts 속성 확인 (덜 구조적)
                elif hasattr(unit, 'contracts'):
                     all_contract_names.update(unit.contracts.keys())

    except Exception as e:
        print(f"  ! 컨트랙트 이름 추출 중 오류: {e}")
        traceback.print_exc()
    return sorted(list(all_contract_names))

def _extract_compilation_unit_details(compile_instance: CryticCompile) -> Dict[str, Any]:
    """컴파일 단위별 상세 정보 (버전, args, remaps, hashes 등)를 추출합니다."""
    details = {"num_units": 0, "units": [], "all_compiler_versions": set()}
    if not hasattr(compile_instance, 'compilation_units') or not compile_instance.compilation_units:
        print("  ! 컴파일 단위 정보 없음.")
        return details

    try:
        details["num_units"] = len(compile_instance.compilation_units)
        print(f"  > 총 {details['num_units']}개의 컴파일 단위 발견.")

        for unit_id, unit in compile_instance.compilation_units.items():
            unit_info = {"id": unit_id, "compiler_version": None, "compiler_type": "unknown"}
            raw_version_info = None

            # 버전 정보 추출 (이전 로직 활용 및 개선)
            if hasattr(unit, 'compiler_version') and unit.compiler_version:
                raw_version_info = unit.compiler_version
                if CompilerVersion and isinstance(raw_version_info, CompilerVersion):
                    if hasattr(raw_version_info, 'version') and raw_version_info.version:
                        unit_info["compiler_version"] = str(raw_version_info.version)
                        unit_info["compiler_type"] = 'vyper' if 'vyper' in str(raw_version_info).lower() else ('solc' if re.match(r'^\d+\.\d+\.\d+', unit_info["compiler_version"]) else 'unknown')
                    else: unit_info["compiler_version"] = str(raw_version_info) # Fallback
                elif isinstance(raw_version_info, str):
                    unit_info["compiler_version"] = raw_version_info
                    unit_info["compiler_type"] = 'vyper' if 'vyper' in unit_info["compiler_version"].lower() else ('solc' if re.match(r'^\d+\.\d+\.\d+', unit_info["compiler_version"]) else 'unknown')
                else: unit_info["compiler_version"] = str(raw_version_info) # Fallback
            elif hasattr(unit, 'solc_version') and unit.solc_version:
                unit_info["compiler_version"] = str(unit.solc_version); unit_info["compiler_type"] = 'solc'
            elif hasattr(unit, 'vyper_version') and unit.vyper_version:
                unit_info["compiler_version"] = str(unit.vyper_version); unit_info["compiler_type"] = 'vyper'
            elif hasattr(unit, 'compiler') and isinstance(unit.compiler, str):
                 match = re.search(r'(\d+\.\d+\.\d+)', unit.compiler)
                 if match:
                     unit_info["compiler_version"] = match.group(1)
                     unit_info["compiler_type"] = 'vyper' if 'vyper' in unit.compiler.lower() else 'solc'

            # 버전 문자열 정리 및 전체 목록에 추가
            if unit_info["compiler_version"]:
                 clean_version_str = re.sub(r'<.*?>', '', str(unit_info["compiler_version"])).strip()
                 if clean_version_str and clean_version_str != 'None':
                     unit_info["compiler_version"] = clean_version_str # 정리된 버전 저장
                     full_version_str = f"{unit_info['compiler_type']}-{clean_version_str}"
                     print(f"    - 컴파일 단위 '{unit_id}': 버전 '{full_version_str}'")
                     details["all_compiler_versions"].add(full_version_str)
                 else:
                     print(f"  ! 컴파일 단위 '{unit_id}'에서 유효한 버전 문자열 추출 실패.")
                     unit_info["compiler_version"] = None # 유효하지 않으면 None으로 설정
            else:
                 print(f"  ! 컴파일 단위 '{unit_id}'에서 버전 감지 불가.")

            # 다른 정보 추출 (solc_args, solc_remaps, hashes) - JSON 직렬화 가능하도록 처리
            unit_info["solc_args"] = getattr(unit, 'solc_args', None)
            unit_info["solc_remaps"] = getattr(unit, 'solc_remaps', None)
            # hashes는 딕셔너리일 수 있으므로 그대로 저장 시도
            unit_info["source_hashes"] = getattr(unit, 'hashes', None)

            details["units"].append(unit_info)

    except Exception as e:
        print(f"  ! 컴파일 단위 상세 정보 추출 중 예외 발생: {e}")
        traceback.print_exc()

    details["all_compiler_versions"] = sorted(list(details["all_compiler_versions"]))
    if not details["all_compiler_versions"]:
         print("  ! 경고: 최종적으로 추출된 컴파일러 버전 정보가 없습니다.")
    return details

def _extract_file_info(compile_instance: CryticCompile) -> Dict[str, Any]:
    """소스 파일, 의존성 파일, 소스 컨텐츠 보유 파일 목록을 추출합니다."""
    info = {"source_files": [], "dependencies": [], "source_content_files": []}
    try:
        all_filename_objects = list(compile_instance.filenames) # Filename 객체 리스트
        all_abs_paths = [f.absolute for f in all_filename_objects]

        # is_dependency 확인 시 Filename 객체 또는 절대 경로 문자열 사용 가능 여부 확인 필요
        # 여기서는 안전하게 절대 경로 문자열로 비교
        dependencies = [f_abs for f_abs in all_abs_paths if compile_instance.is_dependency(f_abs)]
        source_files = [f_abs for f_abs in all_abs_paths if f_abs not in dependencies]

        info["source_files"] = sorted(source_files)
        info["dependencies"] = sorted(dependencies)

        # src_content 딕셔너리의 키 (절대 경로) 목록 추출
        if hasattr(compile_instance, 'src_content') and isinstance(compile_instance.src_content, dict):
            info["source_content_files"] = sorted(list(compile_instance.src_content.keys()))

    except Exception as e:
        print(f"  ! 파일 정보 추출 중 오류: {e}")
        traceback.print_exc()
    return info

def _extract_project_properties(compile_instance: CryticCompile) -> Dict[str, Any]:
    """프로젝트 속성 (target, working_dir, bytecode_only, libraries, package_name)을 추출합니다."""
    properties = {
        "target": None,
        "working_dir": None,
        "bytecode_only": False,
        "linked_libraries": None,
        "package_name": None
    }
    try:
        properties["target"] = getattr(compile_instance, 'target', None)
        # working_dir은 Path 객체일 수 있으므로 문자열로 변환
        wd = getattr(compile_instance, 'working_dir', None)
        properties["working_dir"] = str(wd) if wd else None
        properties["bytecode_only"] = getattr(compile_instance, 'bytecode_only', False)
        properties["linked_libraries"] = getattr(compile_instance, 'libraries', None)
        properties["package_name"] = getattr(compile_instance, 'package_name', None) # package_name 추출 추가
    except Exception as e:
        print(f"  ! 프로젝트 속성 추출 중 오류: {e}")
        traceback.print_exc()
    return properties

# --- Main Analysis Function --- #

def analyze_repo_structure(state: AuditState) -> dict:
    """crytic-compile 라이브러리를 사용하여 리포지토리를 분석하고 컴파일합니다.
    자동 감지 및 컴파일 시도 후, 성공 시 CryticCompile 객체에서 다양한 정보를 추출합니다.
    """
    print("--- 리포지토리 분석 및 컴파일 시작 (crytic-compile 자동 감지) ---")
    repo_path = state.get("local_repo_path")
    if not repo_path or not os.path.isdir(repo_path):
        return {"error": "Repository path not valid or not found.", "compile_instance": None, "repo_analysis": None}

    analysis_errors: List[str] = []
    compile_status: str = "pending"
    compile_instance: Optional[CryticCompile] = None
    # 추출된 정보를 저장할 딕셔너리 초기화
    analysis_result: Dict[str, Any] = {
        "compile_status": compile_status,
        "platform_name": None,
        "platform_type": None,
        "artifacts_path": None,
        "contracts": [],
        "num_compilation_units": 0,
        "compiler_versions": [], # 집계된 버전 목록
        "compilation_unit_details": [], # 상세 단위 정보
        "source_files": [],
        "dependencies": [],
        "source_content_files": [],
        "project_target": repo_path, # 기본값 설정
        "working_directory": None,
        "is_bytecode_only": False,
        "linked_libraries": None,
        "package_name": None
    }

    try:
        # 1. crytic-compile 실행
        print(f"  > crytic-compile 실행 (대상: {repo_path})...")
        try:
            compile_instance = CryticCompile(target=repo_path)
            compile_status = "success"
            analysis_result["compile_status"] = compile_status # 상태 업데이트
            print(f"\n  > crytic-compile 자동 감지 및 컴파일 성공.")

            # 2. 성공 시 정보 추출
            print("  > 컴파일 성공, 상세 정보 추출 시작...")
            try:
                # 플랫폼 정보
                platform_info = _extract_platform_info(compile_instance)
                analysis_result["platform_name"] = platform_info["name"]
                analysis_result["platform_type"] = platform_info["type"]
                print(f"    - 플랫폼: {platform_info['name']} (Type: {platform_info['type']})")

                # 아티팩트 경로
                analysis_result["artifacts_path"] = _determine_artifacts_path(repo_path, platform_info["name"])
                print(f"    - 아티팩트 경로: {analysis_result['artifacts_path'] if analysis_result['artifacts_path'] else '결정 불가'}")

                # 컨트랙트 이름
                analysis_result["contracts"] = _extract_contract_names(compile_instance)
                print(f"    - 컴파일된 총 컨트랙트 수: {len(analysis_result['contracts'])}")

                # 컴파일 단위 상세 정보
                compilation_details = _extract_compilation_unit_details(compile_instance)
                analysis_result["num_compilation_units"] = compilation_details["num_units"]
                analysis_result["compiler_versions"] = compilation_details["all_compiler_versions"]
                analysis_result["compilation_unit_details"] = compilation_details["units"]
                print(f"    - 컴파일 단위 수: {analysis_result['num_compilation_units']}")
                print(f"    - 사용된 컴파일러 버전 (종합): {analysis_result['compiler_versions']}")

                # 파일 정보
                file_info = _extract_file_info(compile_instance)
                analysis_result["source_files"] = file_info["source_files"]
                analysis_result["dependencies"] = file_info["dependencies"]
                analysis_result["source_content_files"] = file_info["source_content_files"]
                print(f"    - 소스 파일 수: {len(analysis_result['source_files'])}")
                print(f"    - 의존성 파일 수: {len(analysis_result['dependencies'])}")
                print(f"    - 로드된 소스 컨텐츠 파일 수: {len(analysis_result['source_content_files'])}")

                # 프로젝트 속성
                project_properties = _extract_project_properties(compile_instance)
                analysis_result["project_target"] = project_properties["target"]
                analysis_result["working_directory"] = project_properties["working_dir"]
                analysis_result["is_bytecode_only"] = project_properties["bytecode_only"]
                analysis_result["linked_libraries"] = project_properties["linked_libraries"]
                analysis_result["package_name"] = project_properties["package_name"]
                print(f"    - 프로젝트 타겟: {analysis_result['project_target']}")
                print(f"    - 작업 디렉토리: {analysis_result['working_directory']}")
                print(f"    - 바이트코드만 존재: {analysis_result['is_bytecode_only']}")
                print(f"    - 링크된 라이브러리: {analysis_result['linked_libraries']}")
                print(f"    - 패키지 이름: {analysis_result['package_name']}")

                # 유틸리티 예시 (선택적)
                # ... (기존 유틸리티 예시 코드 유지 가능, 필요시 여기에 추가) ...

            except Exception as info_e:
                 err_msg = f"컴파일 성공 후 정보 추출 중 오류: {info_e}"
                 print(f"  ! {err_msg}")
                 analysis_errors.append(err_msg)
                 compile_status = "success_info_error"
                 analysis_result["compile_status"] = compile_status # 상태 업데이트
                 traceback.print_exc()

        except InvalidCompilation as e:
            err_msg = f"CryticCompile 실패 (자동 감지): {e}"
            print(f"  ! {err_msg}")
            analysis_errors.append(err_msg)
            compile_status = "compile_failed"
            analysis_result["compile_status"] = compile_status
            compile_instance = None
        except Exception as e_other:
             err_msg = f"CryticCompile 실행 중 예기치 않은 예외 발생: {e_other}"
             print(f"  ! {err_msg}")
             analysis_errors.append(err_msg)
             compile_status = "compile_exception"
             analysis_result["compile_status"] = compile_status
             compile_instance = None
             traceback.print_exc()

        print(f"\n분석 및 컴파일 시도 완료: 최종 상태 = {compile_status}")

        return {
            "repo_analysis": analysis_result,
            "compile_instance": compile_instance,
            "error": "; ".join(analysis_errors) if analysis_errors else None
        }

    except Exception as e:
        # 전체 분석 프로세스 중 치명적 오류
        err_msg = f"리포지토리 분석/컴파일 중 치명적 오류: {e}"
        print(f"  ! {err_msg}")
        traceback.print_exc()
        # 오류 발생 시에도 analysis_result의 기본 구조 유지
        analysis_result["compile_status"] = "fatal_error"
        return {"repo_analysis": analysis_result, "compile_instance": None, "error": err_msg} 