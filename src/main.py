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
            repo_analysis = final_state.get('repo_analysis')
            if repo_analysis:
                 print("  Repo Analysis:")
                 print(f"    Framework: {repo_analysis.get('framework')}")
                 print(f"    Compile Status: {repo_analysis.get('compile_status')}")
                 print(f"    Artifacts Path: {repo_analysis.get('artifacts_path')}")
                 # 컴파일 성공 시 컨트랙트 목록 출력
                 if repo_analysis.get('compile_status') == 'success' and 'contracts' in repo_analysis:
                     contracts = repo_analysis['contracts']
                     print(f"    Compiled Contracts ({len(contracts)}): {contracts[:10]}{'...' if len(contracts) > 10 else ''}") # 최대 10개와 ... 출력
            if final_state.get("error"):
                print(f"  Error: {final_state['error']}")
        else:
            print("최종 상태를 가져올 수 없습니다.")

if __name__ == "__main__":
    main() 