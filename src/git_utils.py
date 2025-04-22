import os
import shutil
from git import Repo

from .state import AuditState

def clone_repository(state: AuditState) -> dict:
    """GitHub 리포지토리를 지정된 로컬 디렉토리('./audit_repo')에 클론하거나, 이미 존재하면 스킵/정리합니다."""
    target_dir = "./audit_repo"
    print(f"--- 리포지토리 확인/클론 시작: {state['github_url']} -> {target_dir} ---")

    if os.path.exists(target_dir):
        print(f"디렉토리 '{target_dir}'가 이미 존재합니다.")
        try:
             repo = Repo(target_dir)
             # 원격 URL 비교 (origin이 존재하고 URL이 하나 이상일 때)
             if repo.remotes and hasattr(repo.remotes, 'origin') and repo.remotes.origin.urls:
                 origin_urls = list(repo.remotes.origin.urls)
                 if state['github_url'] not in origin_urls:
                     raise ValueError(f"기존 디렉토리의 remote URL ({origin_urls})이 요청된 URL ({state['github_url']})과 다릅니다.")
                 print("  > 기존 리포지토리 URL 일치 확인.")
                 # 선택적: git pull 등 추가 작업 가능
                 return {"local_repo_path": target_dir, "error": None}
             else:
                  print("  ! 경고: 기존 디렉토리에 유효한 'origin' remote가 없습니다. 디렉토리를 삭제하고 다시 클론합니다.")
                  raise ValueError("Invalid git repository in existing directory")

        except Exception as e:
             print(f"  ! 기존 리포지토리 검증/사용 중 오류: {e}")
             print("  > 기존 디렉토리를 삭제하고 새로 클론합니다.")
             try:
                 shutil.rmtree(target_dir)
             except Exception as rm_e:
                 print(f"  ! 기존 디렉토리 삭제 중 오류: {rm_e}")
                 return {"local_repo_path": None, "error": f"Failed to clean up existing directory: {rm_e}"}
             # 클론 로직으로 진행

    print(f"디렉토리 '{target_dir}' 생성 및 클론 시작...")
    try:
        Repo.clone_from(state['github_url'], target_dir)
        print(f"리포지토리가 '{target_dir}'에 성공적으로 클론되었습니다.")
        return {"local_repo_path": target_dir, "error": None}
    except Exception as e:
        print(f"  ! 리포지토리 클론 중 오류 발생: {e}")
        if os.path.exists(target_dir):
             try:
                 shutil.rmtree(target_dir)
                 print(f"  > 클론 실패 후 디렉토리 '{target_dir}' 정리 완료.")
             except Exception as rm_e:
                 print(f"  ! 클론 실패 후 디렉토리 정리 중 오류: {rm_e}")
        return {"local_repo_path": None, "error": f"Failed to clone repository: {e}"} 