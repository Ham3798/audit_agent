import argparse
import json
import traceback

from .state import AuditState
from .workflow import build_workflow

def main():
    parser = argparse.ArgumentParser(description="스마트 컨트랙트 감사 에이전트")
    parser.add_argument(
        "github_url",
        nargs='?', # URL을 선택적 인자로 만듦
        default="https://github.com/Uniswap/v4-core.git",
        help="감사할 GitHub 리포지토리 URL (기본값: Uniswap v4-core)"
    )
    args = parser.parse_args()

    initial_state = AuditState(github_url=args.github_url)
    app = build_workflow()

    print("initial_state: ", initial_state)
    print("\n--- audit_agent start ---")

    final_state = None
    try:
        # invoke 대신 stream 사용 (중간 상태 확인 가능)
        for event in app.stream(initial_state):
            event_type = list(event.keys())[0] # 이벤트 타입 (노드 이름 또는 '__end__')
            event_data = event[event_type]
            print(f"\n[Event: {event_type}]")
            # 데이터가 딕셔너리 형태일 때만 상세 출력 (StateGraph 업데이트)
            if isinstance(event_data, dict):
                 # 순환 참조나 직렬화 불가능한 객체를 피하기 위해 안전하게 필터링
                 serializable_data = {}
                 for k, v in event_data.items():
                     try:
                         json.dumps({k: v}) # 직렬화 가능 여부 테스트
                         serializable_data[k] = v
                     except (TypeError, OverflowError):
                         serializable_data[k] = f"<not serializable: {type(v).__name__}>"

                 print("  Updated State:", json.dumps(serializable_data, indent=2, ensure_ascii=False))
            else:
                 print("  Data:", event_data)

            # 마지막 상태 저장 ('__end__' 키 확인)
            if event_type == '__end__':
                 final_state = event_data # 최종 상태 전체를 저장
                 break

    except Exception as e:
        print(f"\n워크플로우 실행 중 예상치 못한 오류 발생: {e}")
        traceback.print_exc()

    finally:
        print("\n--- 감사 에이전트 실행 완료 ---")

        if final_state:
            print("\nFinal State:")
            print(f"  GitHub URL: {final_state.get('github_url')}")
            print(f"  Local Path: {final_state.get('local_repo_path')}")

            # Repo Analysis 출력
            repo_analysis = final_state.get('repo_analysis')
            if repo_analysis:
                 print("  Repo Analysis:")
                 print(f"    Compile Status: {repo_analysis.get('compile_status')}")
                 print(f"    Framework: {repo_analysis.get('framework')}")
                 print(f"    Artifacts Path: {repo_analysis.get('artifacts_path')}")
                 contracts = repo_analysis.get('contracts', [])
                 print(f"    Compiled Contracts ({len(contracts)}): {contracts[:10]}{'...' if len(contracts) > 10 else ''}")
                 # 다른 repo_analysis 정보 필요 시 추가
                 print(f"    Compiler Versions: {repo_analysis.get('compiler_versions')}")
                 print(f"    Source Files: {len(repo_analysis.get('source_files', []))} files")
                 print(f"    Dependencies: {len(repo_analysis.get('dependencies', []))} files")

            # Slither Analysis 출력 (요약)
            slither_results = final_state.get('slither_results')
            if slither_results is not None:
                print("  Slither Analysis:")
                num_findings = len(slither_results)
                print(f"    Total Findings: {num_findings}")
                if num_findings > 0:
                    # 영향도(Impact)별 카운트
                    impact_counts = {"High": 0, "Medium": 0, "Low": 0, "Informational": 0, "Optimization": 0, "N/A": 0}
                    for finding in slither_results:
                        impact = finding.get("impact", "N/A")
                        if impact in impact_counts:
                            impact_counts[impact] += 1
                        else:
                            impact_counts["N/A"] += 1 # 예상치 못한 impact 값 처리
                    print(f"    Findings by Impact: {impact_counts}")
                    # 필요 시 첫 몇 개의 finding 상세 정보 출력 (예시)
                    # print("    First 3 Findings:")
                    # for i, finding in enumerate(slither_results[:3]):
                    #     print(f"      {i+1}. [{finding.get('impact')}] {finding.get('check')}: {finding.get('description')[:100]}...")
            else:
                print("  Slither Analysis: Not performed or failed.")

            # 최종 에러 출력
            if final_state.get("error"):
                print(f"\n  Error during workflow: {final_state['error']}")
        else:
            print("최종 상태를 가져올 수 없습니다.")

if __name__ == "__main__":
    main() 