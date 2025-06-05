"""
Code analysis and diff utilities

코드 분석, diff 생성, 코드 비교 등의 유틸리티 함수들을 제공합니다.
"""

import difflib
from typing import List, Tuple, Dict, Any

from config.logging_config import get_logger

logger = get_logger("utils.code")


class CodeUtils:
    """
    코드 분석 및 비교 관련 유틸리티 클래스
    
    주요 기능:
    - diff 생성
    - 코드 변경 감지
    - 코드 분석
    - 패치 생성
    """
    
    @staticmethod
    def generate_unified_diff(old_content: str, new_content: str, 
                              old_filename: str = "old", new_filename: str = "new") -> str:
        """
        Unified diff 생성
        
        Args:
            old_content: 이전 파일 내용
            new_content: 새로운 파일 내용
            old_filename: 이전 파일명
            new_filename: 새로운 파일명
            
        Returns:
            str: unified diff 문자열
        """
        try:
            diff = difflib.unified_diff(
                old_content.splitlines(keepends=True),
                new_content.splitlines(keepends=True),
                fromfile=old_filename,
                tofile=new_filename,
                lineterm=""
            )
            diff_text = "".join(diff)
            logger.debug(f"diff 생성 완료: {old_filename} -> {new_filename}")
            return diff_text
        except Exception as e:
            logger.error(f"diff 생성 실패: {str(e)}")
            return ""
    
    @staticmethod
    def generate_side_by_side_diff(old_content: str, new_content: str) -> List[str]:
        """
        Side-by-side diff 생성
        
        Args:
            old_content: 이전 파일 내용
            new_content: 새로운 파일 내용
            
        Returns:
            List[str]: side-by-side diff 라인들
        """
        try:
            differ = difflib.HtmlDiff()
            diff_lines = differ.make_file(
                old_content.splitlines(),
                new_content.splitlines(),
                "Old Version",
                "New Version"
            ).splitlines()
            return diff_lines
        except Exception as e:
            logger.error(f"side-by-side diff 생성 실패: {str(e)}")
            return []
    
    @staticmethod
    def has_changes(old_content: str, new_content: str) -> bool:
        """
        코드 변경 여부 확인
        
        Args:
            old_content: 이전 파일 내용
            new_content: 새로운 파일 내용
            
        Returns:
            bool: 변경 사항이 있으면 True
        """
        return old_content.strip() != new_content.strip()
    
    @staticmethod
    def get_change_statistics(old_content: str, new_content: str) -> Dict[str, int]:
        """
        변경 통계 계산
        
        Args:
            old_content: 이전 파일 내용
            new_content: 새로운 파일 내용
            
        Returns:
            Dict[str, int]: 변경 통계 (추가/삭제/변경된 라인 수)
        """
        old_lines = old_content.splitlines()
        new_lines = new_content.splitlines()
        
        matcher = difflib.SequenceMatcher(None, old_lines, new_lines)
        
        added = 0
        deleted = 0
        changed = 0
        
        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == 'insert':
                added += j2 - j1
            elif tag == 'delete':
                deleted += i2 - i1
            elif tag == 'replace':
                deleted += i2 - i1
                added += j2 - j1
                changed += 1
        
        return {
            "added_lines": added,
            "deleted_lines": deleted,
            "changed_blocks": changed,
            "total_changes": added + deleted
        }
    
    @staticmethod
    def extract_changed_functions(old_content: str, new_content: str) -> List[str]:
        """
        변경된 함수 목록 추출 (Solidity 코드용)
        
        Args:
            old_content: 이전 파일 내용
            new_content: 새로운 파일 내용
            
        Returns:
            List[str]: 변경된 함수 이름 목록
        """
        from .string_utils import StringUtils
        
        old_functions = set(StringUtils.extract_function_names(old_content))
        new_functions = set(StringUtils.extract_function_names(new_content))
        
        # 추가되거나 제거된 함수들을 찾음
        changed_functions = []
        
        # 새로 추가된 함수
        added_functions = new_functions - old_functions
        changed_functions.extend(f"+ {func}" for func in added_functions)
        
        # 제거된 함수
        removed_functions = old_functions - new_functions
        changed_functions.extend(f"- {func}" for func in removed_functions)
        
        # 내용이 변경된 함수 (간단한 휴리스틱)
        common_functions = old_functions & new_functions
        for func in common_functions:
            if func in old_content and func in new_content:
                # 함수가 diff에 포함되어 있는지 확인
                diff = CodeUtils.generate_unified_diff(old_content, new_content)
                if func in diff:
                    changed_functions.append(f"~ {func}")
        
        return changed_functions
    
    @staticmethod
    def create_patch_info(author: str, reason: str, old_content: str, new_content: str,
                          filename: str = "unknown") -> Dict[str, Any]:
        """
        패치 정보 생성
        
        Args:
            author: 패치 작성자
            reason: 패치 이유
            old_content: 이전 파일 내용
            new_content: 새로운 파일 내용
            filename: 파일명
            
        Returns:
            Dict[str, Any]: 패치 정보
        """
        import datetime
        
        diff_text = CodeUtils.generate_unified_diff(old_content, new_content, filename, filename)
        stats = CodeUtils.get_change_statistics(old_content, new_content)
        changed_functions = CodeUtils.extract_changed_functions(old_content, new_content)
        
        return {
            "author": author,
            "reason": reason,
            "timestamp": datetime.datetime.now().isoformat(),
            "filename": filename,
            "diff": diff_text,
            "statistics": stats,
            "changed_functions": changed_functions,
            "has_changes": CodeUtils.has_changes(old_content, new_content)
        }
    
    @staticmethod
    def format_diff_summary(stats: Dict[str, int]) -> str:
        """
        diff 요약 포맷팅
        
        Args:
            stats: 변경 통계
            
        Returns:
            str: 포맷팅된 요약
        """
        if stats["total_changes"] == 0:
            return "변경 사항 없음"
        
        parts = []
        if stats["added_lines"] > 0:
            parts.append(f"+{stats['added_lines']}줄")
        if stats["deleted_lines"] > 0:
            parts.append(f"-{stats['deleted_lines']}줄")
        if stats["changed_blocks"] > 0:
            parts.append(f"{stats['changed_blocks']}블록 변경")
        
        return " ".join(parts)
    
    @staticmethod
    def is_significant_change(old_content: str, new_content: str, 
                              min_lines: int = 3) -> bool:
        """
        중요한 변경사항인지 확인
        
        Args:
            old_content: 이전 파일 내용
            new_content: 새로운 파일 내용
            min_lines: 중요한 변경으로 간주할 최소 라인 수
            
        Returns:
            bool: 중요한 변경사항이면 True
        """
        stats = CodeUtils.get_change_statistics(old_content, new_content)
        return stats["total_changes"] >= min_lines
    
    @staticmethod
    def extract_code_blocks(content: str, block_type: str = "function") -> List[Dict[str, Any]]:
        """
        코드에서 특정 블록 추출 (함수, 컨트랙트 등)
        
        Args:
            content: 코드 내용
            block_type: 블록 타입 ("function", "contract" 등)
            
        Returns:
            List[Dict[str, Any]]: 추출된 코드 블록 정보
        """
        import re
        
        blocks = []
        lines = content.splitlines()
        
        if block_type == "function":
            pattern = r'function\s+([a-zA-Z_][a-zA-Z0-9_]*)'
        elif block_type == "contract":
            pattern = r'contract\s+([a-zA-Z_][a-zA-Z0-9_]*)'
        else:
            return blocks
        
        for i, line in enumerate(lines):
            match = re.search(pattern, line)
            if match:
                name = match.group(1)
                blocks.append({
                    "name": name,
                    "line_number": i + 1,
                    "line_content": line.strip(),
                    "type": block_type
                })
        
        return blocks 