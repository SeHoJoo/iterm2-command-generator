"""Dangerous command detection for iTerm2 AI Command Generator."""

import re
from typing import List, Tuple

from models import RiskLevel, RiskResult


class RiskDetector:
    """Detects potentially dangerous shell commands."""

    def __init__(self):
        """Initialize RiskDetector with default patterns."""
        # List of (pattern, risk_level, reason)
        self._patterns: List[Tuple[str, RiskLevel, str]] = []
        self._add_default_patterns()

    def _add_default_patterns(self) -> None:
        """Add default dangerous command patterns."""
        # DANGEROUS patterns - can cause severe damage
        dangerous_patterns = [
            (r'rm\s+(-[rf]+\s+)*/', "루트 디렉토리 삭제 시도"),
            (r'rm\s+(-[rf]+\s+)*~', "홈 디렉토리 삭제 시도"),
            (r'rm\s+-[rf]*\s+-[rf]*\s+/', "루트 디렉토리 삭제 시도"),
            (r'mkfs\.', "파일시스템 포맷 시도"),
            (r'>\s*/dev/sd[a-z]', "디스크 직접 덮어쓰기"),
            (r'>\s*/dev/nvme', "NVMe 디스크 직접 덮어쓰기"),
            (r':\(\)\s*\{\s*:\|:\s*&\s*\}\s*;:', "Fork bomb 감지"),
            (r'echo\s+.*>\s*/dev/sd[a-z]', "디스크에 데이터 직접 쓰기"),
        ]

        for pattern, reason in dangerous_patterns:
            self._patterns.append((pattern, RiskLevel.DANGEROUS, reason))

        # WARNING patterns - potentially risky
        warning_patterns = [
            (r'chmod\s+777', "과도한 권한 부여 (777)"),
            (r'chmod\s+-R', "재귀적 권한 변경"),
            (r'chown\s+-R', "재귀적 소유자 변경"),
            (r'dd\s+if=', "디스크 이미지 직접 쓰기"),
            (r'sudo\s+', "관리자 권한으로 실행"),
            (r'curl\s+.*\|\s*sh', "원격 스크립트 직접 실행"),
            (r'curl\s+.*\|\s*bash', "원격 스크립트 직접 실행"),
            (r'wget\s+.*\|\s*sh', "원격 스크립트 직접 실행"),
            (r'wget\s+.*\|\s*bash', "원격 스크립트 직접 실행"),
            (r'>\s*/etc/', "/etc 디렉토리 파일 덮어쓰기"),
            (r'rm\s+-[rf]', "강제/재귀 삭제"),
            (r'pkill\s+-9', "프로세스 강제 종료"),
            (r'kill\s+-9', "프로세스 강제 종료"),
            (r'shutdown', "시스템 종료 명령"),
            (r'reboot', "시스템 재시작 명령"),
            (r'init\s+[06]', "시스템 종료/재시작"),
            (r'systemctl\s+(stop|disable|mask)', "서비스 중지/비활성화"),
            (r'launchctl\s+unload', "서비스 언로드"),
            (r'>\s*/dev/null\s+2>&1\s*&', "백그라운드로 출력 숨김"),
            (r'history\s+-c', "명령어 히스토리 삭제"),
            (r'shred\s+', "파일 영구 삭제"),
        ]

        for pattern, reason in warning_patterns:
            self._patterns.append((pattern, RiskLevel.WARNING, reason))

    def analyze(self, command: str) -> RiskResult:
        """
        Analyze command for potential risks.

        Args:
            command: Shell command to analyze.

        Returns:
            RiskResult with level and reasons.
        """
        reasons: List[str] = []
        highest_level = RiskLevel.SAFE

        for pattern, level, reason in self._patterns:
            if re.search(pattern, command, re.IGNORECASE):
                reasons.append(reason)
                # Keep track of highest risk level
                if level == RiskLevel.DANGEROUS:
                    highest_level = RiskLevel.DANGEROUS
                elif level == RiskLevel.WARNING and highest_level != RiskLevel.DANGEROUS:
                    highest_level = RiskLevel.WARNING

        return RiskResult(level=highest_level, reasons=reasons)

    def add_pattern(self, pattern: str, level: RiskLevel, reason: str) -> None:
        """
        Add a custom risk pattern.

        Args:
            pattern: Regex pattern to match.
            level: Risk level for this pattern.
            reason: Warning message to display.
        """
        self._patterns.append((pattern, level, reason))

    def remove_pattern(self, pattern: str) -> bool:
        """
        Remove a pattern by its regex string.

        Args:
            pattern: The pattern string to remove.

        Returns:
            True if pattern was found and removed.
        """
        original_length = len(self._patterns)
        self._patterns = [p for p in self._patterns if p[0] != pattern]
        return len(self._patterns) < original_length

    def get_patterns(self) -> List[Tuple[str, RiskLevel, str]]:
        """Get all registered patterns."""
        return self._patterns.copy()
