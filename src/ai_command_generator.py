#!/usr/bin/env python3
"""iTerm2 AI Command Generator - Main Script."""

import asyncio
import logging
from typing import Optional

import iterm2

from . import logger
from .config import ConfigManager
from .exceptions import APIError, KeychainError, RateLimitError
from .gemini_client import GeminiClient
from .history_manager import HistoryManager
from .models import GeneratedCommand, RiskLevel


class AICommandGenerator:
    """Main iTerm2 AI Command Generator application."""

    def __init__(
        self,
        connection: iterm2.Connection,
        config_manager: ConfigManager,
        gemini_client: Optional[GeminiClient] = None
    ):
        """
        Initialize AICommandGenerator.

        Args:
            connection: iTerm2 connection.
            config_manager: Configuration manager.
            gemini_client: Optional Gemini client (created if not provided).
        """
        self.connection = connection
        self.config_manager = config_manager
        self.gemini_client = gemini_client
        self.history_manager = HistoryManager(max_items=config_manager.get_max_history())
        self.app = None

    async def run(self) -> None:
        """Start the main event loop."""
        logger.info("AI Command Generator 시작")
        self.app = await iterm2.async_get_app(self.connection)

        # Ensure API key is configured
        if not await self._ensure_api_key():
            logger.error("API 키 설정 실패")
            return

        logger.info("API 키 확인 완료, 키보드 모니터링 시작")
        # Set up keyboard monitoring
        await self._setup_keyboard_monitoring()

    async def _ensure_api_key(self) -> bool:
        """Ensure API key is configured, prompt if not."""
        api_key = self.config_manager.get_api_key()

        if not api_key:
            # Show first-run setup dialog
            api_key = await self._show_api_key_setup()
            if not api_key:
                await self._show_error("API 키가 설정되지 않았습니다. 플러그인을 사용하려면 API 키가 필요합니다.")
                return False

            try:
                self.config_manager.set_api_key(api_key)
            except KeychainError as e:
                await self._show_error(f"API 키 저장 실패: {e}")
                return False

        # Initialize Gemini client
        try:
            self.gemini_client = GeminiClient(api_key)
        except Exception as e:
            await self._show_error(f"Gemini 클라이언트 초기화 실패: {e}")
            return False

        return True

    async def _show_api_key_setup(self) -> Optional[str]:
        """Show API key setup dialog."""
        alert = iterm2.TextInputAlert(
            "Gemini API 키 설정",
            "Google Gemini API 키를 입력하세요.\n(https://aistudio.google.com/apikey 에서 발급)",
            "API 키",
            ""
        )
        return await alert.async_run(self.connection)

    async def _setup_keyboard_monitoring(self) -> None:
        """Set up keyboard shortcut monitoring."""
        async with iterm2.KeystrokeMonitor(self.connection) as mon:
            while True:
                keystroke = await mon.async_get()

                # Check for Ctrl+Shift+A (AI command generation)
                if (keystroke.keycode == iterm2.Keycode.ANSI_A and
                    iterm2.Modifier.CONTROL in keystroke.modifiers and
                    iterm2.Modifier.SHIFT in keystroke.modifiers):

                    try:
                        session = self.app.current_terminal_window.current_tab.current_session
                        await self.handle_shortcut(session)
                    except Exception as e:
                        await self._show_error(f"오류 발생: {e}")

                # Check for Ctrl+Shift+H (History)
                elif (keystroke.keycode == iterm2.Keycode.ANSI_H and
                      iterm2.Modifier.CONTROL in keystroke.modifiers and
                      iterm2.Modifier.SHIFT in keystroke.modifiers):

                    try:
                        session = self.app.current_terminal_window.current_tab.current_session
                        await self.show_history_dialog(session)
                    except Exception as e:
                        await self._show_error(f"오류 발생: {e}")

    async def handle_shortcut(self, session: iterm2.Session) -> None:
        """
        Handle the activation shortcut.

        Args:
            session: Current iTerm2 session.
        """
        # Get window ID for dialogs
        window = self.app.current_terminal_window
        window_id = window.window_id if window else None

        # Show input dialog
        user_input = await self.show_input_dialog(window_id)
        if not user_input:
            logger.debug("사용자가 입력을 취소함")
            return

        logger.info(f"명령어 생성 요청: {user_input[:50]}...")

        # Get context
        working_directory = await session.async_get_variable("path") or "~"
        shell_type = await session.async_get_variable("shell") or "bash"
        # Extract shell name from path (e.g., /bin/zsh -> zsh)
        if "/" in shell_type:
            shell_type = shell_type.split("/")[-1]

        # Generate command
        try:
            command = await self.gemini_client.generate_command(
                user_input,
                working_directory,
                shell_type
            )
            logger.info(f"명령어 생성 완료: {command.command}")
        except RateLimitError as e:
            logger.error(f"API 한도 초과: {e}")
            await self._show_error(f"API 한도 초과: {e}\n잠시 후 다시 시도해주세요.")
            return
        except APIError as e:
            logger.error(f"API 오류: {e}")
            await self._show_error(f"명령어 생성 실패: {e}")
            return
        except Exception as e:
            logger.exception(f"예상치 못한 오류: {e}")
            await self._show_error(f"오류 발생: {e}")
            return

        # Show command dialog with risk handling
        result = await self.show_command_dialog(window_id, command)

        if result == "confirm":
            # Check risk level and show appropriate warnings
            if command.risk_level == RiskLevel.DANGEROUS:
                if not await self._show_dangerous_warning(window_id, command):
                    return
            elif command.risk_level == RiskLevel.WARNING:
                if not await self._show_warning(window_id, command):
                    return

            # Save to history and send to terminal
            self.history_manager.add(user_input, command.command)
            await self.send_to_terminal(session, command.command)

        elif result == "explain":
            try:
                explanation = await self.gemini_client.explain_command(command.command)
                await self.show_explanation_dialog(window_id, command.command, explanation)
            except APIError as e:
                await self._show_error(f"설명 생성 실패: {e}")

        elif result == "save":
            # Save to history with optional alias
            alias = await self._show_alias_input(window_id)
            self.history_manager.add(user_input, command.command, alias)
            await self._show_info(window_id, "명령어가 히스토리에 저장되었습니다.")

    async def show_input_dialog(self, window_id: Optional[str]) -> Optional[str]:
        """
        Show natural language input dialog.

        Args:
            window_id: Target window ID.

        Returns:
            User input or None if cancelled.
        """
        alert = iterm2.TextInputAlert(
            "AI Command Generator",
            "Describe what you want to do in natural language.",
            "Ex: Find files modified in the last 7 days",
            "",
            window_id
        )
        return await alert.async_run(self.connection)

    async def show_command_dialog(
        self,
        window_id: Optional[str],
        command: GeneratedCommand
    ) -> str:
        """
        Show generated command confirmation dialog.

        Args:
            window_id: Target window ID.
            command: Generated command.

        Returns:
            User choice: "confirm", "cancel", "explain", or "save".
        """
        # Build subtitle with risk indicator
        risk_indicator = ""
        if command.risk_level == RiskLevel.WARNING:
            risk_indicator = "⚠️ 주의: "
        elif command.risk_level == RiskLevel.DANGEROUS:
            risk_indicator = "🚨 위험: "

        subtitle = f"{risk_indicator}생성된 명령어:\n\n{command.command}"

        if command.risk_reasons:
            subtitle += f"\n\n경고: {', '.join(command.risk_reasons)}"

        alert = iterm2.Alert("명령어 확인", subtitle, window_id)
        alert.add_button("실행")
        alert.add_button("설명")
        alert.add_button("저장")
        alert.add_button("취소")

        result = await alert.async_run(self.connection)

        # Button indices: 1000=실행, 1001=설명, 1002=저장, 1003=취소
        if result == 1000:
            return "confirm"
        elif result == 1001:
            return "explain"
        elif result == 1002:
            return "save"
        else:
            return "cancel"

    async def show_explanation_dialog(
        self,
        window_id: Optional[str],
        command: str,
        explanation: str
    ) -> None:
        """
        Show command explanation dialog.

        Args:
            window_id: Target window ID.
            command: The command being explained.
            explanation: Detailed explanation.
        """
        alert = iterm2.Alert(
            f"명령어 설명: {command}",
            explanation,
            window_id
        )
        alert.add_button("확인")
        await alert.async_run(self.connection)

    async def _show_warning(
        self,
        window_id: Optional[str],
        command: GeneratedCommand
    ) -> bool:
        """Show warning dialog for risky commands."""
        subtitle = f"이 명령어는 주의가 필요합니다:\n\n{command.command}\n\n"
        subtitle += f"경고 사유:\n• " + "\n• ".join(command.risk_reasons)
        subtitle += "\n\n정말 실행하시겠습니까?"

        alert = iterm2.Alert("⚠️ 주의", subtitle, window_id)
        alert.add_button("실행")
        alert.add_button("취소")

        result = await alert.async_run(self.connection)
        return result == 1000

    async def _show_dangerous_warning(
        self,
        window_id: Optional[str],
        command: GeneratedCommand
    ) -> bool:
        """Show double confirmation for dangerous commands."""
        subtitle = f"🚨 위험한 명령어입니다!\n\n{command.command}\n\n"
        subtitle += f"위험 사유:\n• " + "\n• ".join(command.risk_reasons)
        subtitle += "\n\n이 명령어는 시스템에 심각한 영향을 줄 수 있습니다."

        # First confirmation
        alert = iterm2.Alert("🚨 위험 경고", subtitle, window_id)
        alert.add_button("계속")
        alert.add_button("취소")

        result = await alert.async_run(self.connection)
        if result != 1000:
            return False

        # Second confirmation - require typing CONFIRM
        confirm_input = await iterm2.TextInputAlert(
            "최종 확인",
            "정말 이 위험한 명령어를 실행하시려면 'CONFIRM'을 입력하세요.",
            "CONFIRM",
            "",
            window_id
        ).async_run(self.connection)

        return confirm_input == "CONFIRM"

    async def send_to_terminal(self, session: iterm2.Session, command: str) -> None:
        """
        Send command to terminal.

        Args:
            session: Target session.
            command: Command to send.

        Note:
            Does not include Enter key - user must confirm execution.
        """
        await session.async_send_text(command)

    async def _show_alias_input(self, window_id: Optional[str]) -> Optional[str]:
        """Show alias input dialog for saving command."""
        alert = iterm2.TextInputAlert(
            "별칭 지정",
            "명령어에 별칭을 지정하세요 (선택사항).\n별칭으로 히스토리에서 빠르게 찾을 수 있습니다.",
            "예: 로그정리",
            "",
            window_id
        )
        result = await alert.async_run(self.connection)
        return result if result else None

    async def _show_info(self, window_id: Optional[str], message: str) -> None:
        """Show info message dialog."""
        alert = iterm2.Alert("알림", message, window_id)
        alert.add_button("확인")
        await alert.async_run(self.connection)

    async def _show_error(self, message: str) -> None:
        """Show error message dialog."""
        window = self.app.current_terminal_window if self.app else None
        window_id = window.window_id if window else None

        alert = iterm2.Alert("오류", message, window_id)
        alert.add_button("확인")
        await alert.async_run(self.connection)

    async def show_history_dialog(self, session: iterm2.Session) -> None:
        """
        Show history selection dialog.

        Args:
            session: Current iTerm2 session.
        """
        window = self.app.current_terminal_window
        window_id = window.window_id if window else None

        history = self.history_manager.get_all()

        if not history:
            await self._show_info(window_id, "저장된 히스토리가 없습니다.")
            return

        # Build history list for display (max 10 items)
        display_items = history[:10]
        history_text = "최근 사용한 명령어:\n\n"
        for i, item in enumerate(display_items, 1):
            alias_text = f" [{item.alias}]" if item.alias else ""
            history_text += f"{i}. {item.command}{alias_text}\n"

        history_text += "\n실행할 명령어 번호를 입력하세요 (1-{}).".format(len(display_items))

        # Show selection dialog
        alert = iterm2.TextInputAlert(
            "명령어 히스토리",
            history_text,
            "번호 (1-{})".format(len(display_items)),
            "",
            window_id
        )
        result = await alert.async_run(self.connection)

        if not result:
            return

        try:
            index = int(result) - 1
            if 0 <= index < len(display_items):
                selected = display_items[index]
                # Update usage count
                self.history_manager.add(selected.prompt, selected.command, selected.alias)
                await self.send_to_terminal(session, selected.command)
            else:
                await self._show_error("잘못된 번호입니다.")
        except ValueError:
            await self._show_error("숫자를 입력해주세요.")


async def main(connection: iterm2.Connection) -> None:
    """Main entry point."""
    config_manager = ConfigManager()
    generator = AICommandGenerator(connection, config_manager)
    await generator.run()


# Run the script
iterm2.run_forever(main)
