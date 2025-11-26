#!/bin/bash
# iTerm2 AI Command Generator - Installation Script

set -e

SCRIPT_NAME="ai_command_generator.py"
# iTerm2 uses ~/.config/iterm2/AppSupport for scripts
PLUGIN_DIR="$HOME/.config/iterm2/AppSupport/Scripts/AutoLaunch"
ITERM2_ENV_DIR="$HOME/.config/iterm2/AppSupport/iterm2env"

echo "iTerm2 AI Command Generator 설치를 시작합니다..."

# Check if iTerm2 is installed
if [ ! -d "/Applications/iTerm.app" ]; then
    echo "오류: iTerm2가 설치되어 있지 않습니다."
    echo "https://iterm2.com 에서 iTerm2를 먼저 설치해주세요."
    exit 1
fi

# Check if iTerm2 Python Runtime is installed
if [ ! -d "$ITERM2_ENV_DIR" ]; then
    echo ""
    echo "오류: iTerm2 Python Runtime이 설치되어 있지 않습니다."
    echo ""
    echo "다음 단계를 따라 설치해주세요:"
    echo "  1. iTerm2 실행"
    echo "  2. Scripts > Manage > Install Python Runtime"
    echo "  3. 설치 완료 후 이 스크립트를 다시 실행"
    echo ""
    exit 1
fi

# Find iTerm2 pip
ITERM2_PIP=$(find "$ITERM2_ENV_DIR" -name "pip3" -type f 2>/dev/null | head -1)

if [ -z "$ITERM2_PIP" ]; then
    echo "오류: iTerm2 Python Runtime의 pip를 찾을 수 없습니다."
    exit 1
fi

echo "iTerm2 Python Runtime을 찾았습니다: $ITERM2_PIP"

# Create AutoLaunch directory if it doesn't exist
if [ ! -d "$PLUGIN_DIR" ]; then
    echo "AutoLaunch 디렉토리를 생성합니다..."
    mkdir -p "$PLUGIN_DIR"
fi

# Install Python dependencies using iTerm2's pip
echo "Python 의존성을 설치합니다..."
"$ITERM2_PIP" install -r requirements.txt

# Copy script to AutoLaunch folder
echo "플러그인을 설치합니다..."

# Remove old installation if exists
rm -rf "$PLUGIN_DIR/ai_command_generator"
rm -rf "$PLUGIN_DIR/ai_command_generator.py"

# Create plugin directory (folder with .py extension for iTerm2)
PLUGIN_SCRIPT_DIR="$PLUGIN_DIR/ai_command_generator.py"
mkdir -p "$PLUGIN_SCRIPT_DIR"

# Copy all source files
cp src/models.py "$PLUGIN_SCRIPT_DIR/"
cp src/exceptions.py "$PLUGIN_SCRIPT_DIR/"
cp src/config.py "$PLUGIN_SCRIPT_DIR/"
cp src/risk_detector.py "$PLUGIN_SCRIPT_DIR/"
cp src/gemini_client.py "$PLUGIN_SCRIPT_DIR/"
cp src/history_manager.py "$PLUGIN_SCRIPT_DIR/"

# Create main entry point as __main__.py (required for folder-based scripts)
cat > "$PLUGIN_SCRIPT_DIR/__main__.py" << 'EOF'
#!/usr/bin/env python3
"""iTerm2 AI Command Generator - Main Script."""

import asyncio
import logging
import signal
import sys
import os
from typing import Optional
from pathlib import Path

import iterm2

# Handle termination signals for clean shutdown
def signal_handler(signum, frame):
    sys.exit(0)

signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)

# Create PID file to prevent duplicate instances
pid_file = Path.home() / ".config" / "iterm2-ai-generator" / "pid"
pid_file.parent.mkdir(parents=True, exist_ok=True)

# Check if another instance is running
if pid_file.exists():
    try:
        old_pid = int(pid_file.read_text().strip())
        # Check if process is still running
        os.kill(old_pid, 0)
        # Process exists, kill it
        os.kill(old_pid, signal.SIGTERM)
    except (ProcessLookupError, ValueError, PermissionError):
        pass  # Process doesn't exist or can't be killed

# Write current PID
pid_file.write_text(str(os.getpid()))

# Setup logging
log_dir = Path.home() / ".config" / "iterm2-ai-generator"
log_dir.mkdir(parents=True, exist_ok=True)
log_file = log_dir / "debug.log"

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
    ]
)
logger = logging.getLogger("iterm2-ai-generator")

from config import ConfigManager
from exceptions import APIError, KeychainError, RateLimitError
from gemini_client import GeminiClient
from history_manager import HistoryManager
from models import GeneratedCommand, RiskLevel




class AICommandGenerator:
    """Main iTerm2 AI Command Generator application."""

    def __init__(
        self,
        connection: iterm2.Connection,
        config_manager: ConfigManager,
        gemini_client: GeminiClient
    ):
        self.connection = connection
        self.config_manager = config_manager
        self.gemini_client = gemini_client
        self.history_manager = HistoryManager(max_items=config_manager.get_max_history())
        self.app = None

    async def run(self) -> None:
        """Start the main event loop."""
        logger.info("AI Command Generator started")
        self.app = await iterm2.async_get_app(self.connection)

        # Ensure API key is configured
        if not await self._ensure_api_key():
            logger.error("API key setup failed")
            return

        logger.info("API key verified, starting keyboard monitoring")
        # Set up keyboard monitoring
        await self._setup_keyboard_monitoring()

    async def _ensure_api_key(self) -> bool:
        """Ensure API key is configured, prompt if not."""
        api_key = self.config_manager.get_api_key()

        if not api_key:
            # Show first-run setup dialog
            api_key = await self._show_api_key_setup()

            if not api_key:
                return False

            try:
                self.config_manager.set_api_key(api_key)
                # Reinitialize Gemini client with new key
                self.gemini_client = GeminiClient(api_key)
            except KeychainError as e:
                await self._show_error(f"Failed to save API key: {e}")
                return False

        return True

    async def _show_api_key_setup(self) -> Optional[str]:
        """Show API key setup dialog using native macOS dialog."""
        apple_script = '''
display dialog "Enter your Google Gemini API key.\\n(Get one at https://aistudio.google.com/apikey)" default answer "" with title "Gemini API Key Setup" buttons {"Cancel", "OK"} default button "OK" cancel button "Cancel"
'''
        proc = await asyncio.create_subprocess_exec(
            "osascript", "-e", apple_script,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()

        if proc.returncode != 0:
            return None

        output = stdout.decode("utf-8").strip()
        if "text returned:" in output:
            return output.split("text returned:", 1)[1].strip()
        return None

    async def _setup_keyboard_monitoring(self) -> None:
        """Set up keyboard shortcut monitoring."""
        async with iterm2.KeystrokeMonitor(self.connection) as mon:
            while True:
                keystroke = await mon.async_get()

                # Check for Ctrl+Cmd+A (AI command generation)
                if (keystroke.keycode == iterm2.Keycode.ANSI_A and
                    iterm2.Modifier.CONTROL in keystroke.modifiers and
                    iterm2.Modifier.COMMAND in keystroke.modifiers):

                    try:
                        session = self.app.current_terminal_window.current_tab.current_session
                        # Run as concurrent task to allow multiple requests
                        asyncio.create_task(self.handle_shortcut(session))
                    except Exception as e:
                        await self._show_error(f"Error: {e}")

                # Check for Ctrl+Cmd+H (History)
                elif (keystroke.keycode == iterm2.Keycode.ANSI_H and
                      iterm2.Modifier.CONTROL in keystroke.modifiers and
                      iterm2.Modifier.COMMAND in keystroke.modifiers):

                    try:
                        session = self.app.current_terminal_window.current_tab.current_session
                        asyncio.create_task(self.show_history_dialog(session))
                    except Exception as e:
                        await self._show_error(f"Error: {e}")

                # Check for Ctrl+Cmd+M (Model selection)
                elif (keystroke.keycode == iterm2.Keycode.ANSI_M and
                      iterm2.Modifier.CONTROL in keystroke.modifiers and
                      iterm2.Modifier.COMMAND in keystroke.modifiers):

                    try:
                        asyncio.create_task(self.show_model_selection())
                    except Exception as e:
                        await self._show_error(f"Error: {e}")

                # Check for Ctrl+Cmd+S (Script generation)
                elif (keystroke.keycode == iterm2.Keycode.ANSI_S and
                      iterm2.Modifier.CONTROL in keystroke.modifiers and
                      iterm2.Modifier.COMMAND in keystroke.modifiers):

                    try:
                        session = self.app.current_terminal_window.current_tab.current_session
                        asyncio.create_task(self.handle_script_shortcut(session))
                    except Exception as e:
                        await self._show_error(f"Error: {e}")

                # Check for Ctrl+Cmd+I (Instructions)
                elif (keystroke.keycode == iterm2.Keycode.ANSI_I and
                      iterm2.Modifier.CONTROL in keystroke.modifiers and
                      iterm2.Modifier.COMMAND in keystroke.modifiers):

                    try:
                        asyncio.create_task(self.show_instructions_dialog())
                    except Exception as e:
                        await self._show_error(f"Error: {e}")

    async def handle_shortcut(self, session: iterm2.Session) -> None:
        """Handle the activation shortcut."""
        # Get window ID for dialogs
        window = self.app.current_terminal_window
        window_id = window.window_id if window else None

        # Show input dialog
        user_input = await self.show_input_dialog(window_id)
        if not user_input:
            logger.debug("User cancelled input")
            return

        logger.info(f"Command generation request: {user_input[:50]}...")

        # Get context
        working_directory = await session.async_get_variable("path") or "~"
        shell_type = await session.async_get_variable("shell") or "bash"

        # Extract shell name from path
        if "/" in shell_type:
            shell_type = shell_type.split("/")[-1]

        # Spinner animation task
        spinner_running = True
        async def run_spinner():
            spinner_chars = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
            idx = 0
            while spinner_running:
                char = spinner_chars[idx % len(spinner_chars)]
                # Clear line and show spinner
                await session.async_send_text("\x15" + char)
                idx += 1
                await asyncio.sleep(0.1)

        # Start spinner
        spinner_task = asyncio.create_task(run_spinner())

        # Get custom instructions
        custom_instructions = self.config_manager.get_custom_instructions()

        # Generate command with timeout
        try:
            command = await asyncio.wait_for(
                self.gemini_client.generate_command(
                    user_input,
                    working_directory,
                    shell_type,
                    custom_instructions
                ),
                timeout=30.0  # 30 second timeout
            )
            logger.info(f"Command generated: {command.command}")

            # Stop spinner and clear line
            spinner_running = False
            spinner_task.cancel()
            try:
                await spinner_task
            except asyncio.CancelledError:
                pass
            await session.async_send_text("\x15")
        except asyncio.TimeoutError:
            # Stop spinner and clear line
            spinner_running = False
            spinner_task.cancel()
            try:
                await spinner_task
            except asyncio.CancelledError:
                pass
            await session.async_send_text("\x15")
            logger.error("API timeout")
            await self._show_error("Command generation timed out.\\n\\nTry switching to a faster model with Ctrl+Cmd+M.")
            return
        except RateLimitError as e:
            # Stop spinner and clear line
            spinner_running = False
            spinner_task.cancel()
            try:
                await spinner_task
            except asyncio.CancelledError:
                pass
            await session.async_send_text("\x15")
            logger.error(f"API rate limit: {e}")
            await self._show_error(f"API rate limit exceeded: {e}\nPlease try again later.")
            return
        except APIError as e:
            # Stop spinner and clear line
            spinner_running = False
            spinner_task.cancel()
            try:
                await spinner_task
            except asyncio.CancelledError:
                pass
            await session.async_send_text("\x15")
            logger.error(f"API error: {e}")
            await self._show_error(f"Command generation failed: {e}")
            return
        except Exception as e:
            # Stop spinner and clear line
            spinner_running = False
            spinner_task.cancel()
            try:
                await spinner_task
            except asyncio.CancelledError:
                pass
            await session.async_send_text("\x15")
            logger.exception(f"Unexpected error: {e}")
            await self._show_error(f"Error: {e}")
            return

        # Check for dangerous commands - show warning only for dangerous ones
        if command.risk_level == RiskLevel.DANGEROUS:
            if not await self._show_dangerous_warning(window_id, command):
                return
        elif command.risk_level == RiskLevel.WARNING:
            if not await self._show_warning(window_id, command):
                return

        # Save to history and send to terminal directly (no confirmation popup)
        self.history_manager.add(user_input, command.command)
        await self.send_to_terminal(session, command.command)

    async def handle_script_shortcut(self, session: iterm2.Session) -> None:
        """Handle the script generation shortcut."""
        window = self.app.current_terminal_window
        window_id = window.window_id if window else None

        # Show input dialog for script description
        apple_script = '''
display dialog "Describe the script you want to generate.\\nEx: Directory backup script" default answer "" with title "AI Script Generator" buttons {"Cancel", "OK"} default button "OK" cancel button "Cancel"
'''
        proc = await asyncio.create_subprocess_exec(
            "osascript", "-e", apple_script,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()

        if proc.returncode != 0:
            return

        output = stdout.decode("utf-8").strip()
        user_input = None
        if "text returned:" in output:
            user_input = output.split("text returned:", 1)[1].strip()

        if not user_input:
            return

        logger.info(f"Script generation request: {user_input[:50]}...")

        # Get context
        working_directory = await session.async_get_variable("path") or "~"
        shell_type = await session.async_get_variable("shell") or "bash"

        if "/" in shell_type:
            shell_type = shell_type.split("/")[-1]

        # Spinner animation
        spinner_running = True
        async def run_spinner():
            spinner_chars = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
            idx = 0
            while spinner_running:
                char = spinner_chars[idx % len(spinner_chars)]
                await session.async_send_text("\x15" + char)
                idx += 1
                await asyncio.sleep(0.1)

        spinner_task = asyncio.create_task(run_spinner())

        # Get custom instructions
        custom_instructions = self.config_manager.get_custom_instructions()

        try:
            script = await asyncio.wait_for(
                self.gemini_client.generate_script(
                    user_input,
                    working_directory,
                    shell_type,
                    custom_instructions
                ),
                timeout=60.0  # 60 second timeout for scripts
            )
            logger.info("Script generated")

            # Stop spinner
            spinner_running = False
            spinner_task.cancel()
            try:
                await spinner_task
            except asyncio.CancelledError:
                pass
            await session.async_send_text("\x15")

        except asyncio.TimeoutError:
            spinner_running = False
            spinner_task.cancel()
            try:
                await spinner_task
            except asyncio.CancelledError:
                pass
            await session.async_send_text("\x15")
            await self._show_error("Script generation timed out.\\n\\nTry switching to a faster model with Ctrl+Cmd+M.")
            return
        except Exception as e:
            spinner_running = False
            spinner_task.cancel()
            try:
                await spinner_task
            except asyncio.CancelledError:
                pass
            await session.async_send_text("\x15")
            await self._show_error(f"Script generation failed: {e}")
            return

        # Ask user how to save the script
        apple_script = '''
tell application "iTerm"
    activate
    display dialog "Script generated.\\n\\nChoose how to save:" with title "Save Script" buttons {"Cancel", "Copy to Clipboard", "Save to File"} default button "Save to File" cancel button "Cancel"
end tell
'''
        proc = await asyncio.create_subprocess_exec(
            "osascript", "-e", apple_script,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()

        if proc.returncode != 0:
            return

        result = stdout.decode("utf-8").strip()

        if "Copy to Clipboard" in result:
            # Copy script to clipboard
            import subprocess
            proc = subprocess.Popen(
                ['pbcopy'],
                stdin=subprocess.PIPE,
                env={'LANG': 'en_US.UTF-8'}
            )
            proc.communicate(script.encode('utf-8'))

        elif "Save to File" in result:
            # Ask for filename
            apple_script = '''
tell application "iTerm"
    activate
    display dialog "Enter filename to save:" default answer "script.sh" with title "Save Script" buttons {"Cancel", "Save"} default button "Save" cancel button "Cancel"
end tell
'''
            proc = await asyncio.create_subprocess_exec(
                "osascript", "-e", apple_script,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()

            if proc.returncode != 0:
                return

            output = stdout.decode("utf-8").strip()
            if "text returned:" not in output:
                return

            filename = output.split("text returned:", 1)[1].strip()
            if not filename:
                filename = "script.sh"

            # Encode script to base64 and send to terminal
            import base64
            encoded = base64.b64encode(script.encode('utf-8')).decode('ascii')
            save_cmd = f"echo '{encoded}' | base64 -d > {filename} && chmod +x {filename}"
            await session.async_send_text(save_cmd)

    async def show_input_dialog(self, window_id: Optional[str]) -> Optional[str]:
        """Show natural language input dialog using native macOS dialog."""
        apple_script = '''
display dialog "Describe what you want to do in natural language.\\nEx: Find files modified in the last 7 days" default answer "" with title "AI Command Generator" buttons {"Cancel", "OK"} default button "OK" cancel button "Cancel"
'''
        proc = await asyncio.create_subprocess_exec(
            "osascript", "-e", apple_script,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()

        if proc.returncode != 0:
            return None

        output = stdout.decode("utf-8").strip()
        if "text returned:" in output:
            return output.split("text returned:", 1)[1].strip()
        return None

    async def _show_warning(
        self,
        window_id: Optional[str],
        command: GeneratedCommand
    ) -> bool:
        """Show warning dialog for potentially dangerous commands."""
        cmd_escaped = command.command.replace('"', '\\"')
        reasons = ', '.join(command.risk_reasons)
        apple_script = f'''
display dialog "⚠️ This command requires caution:\\n\\n{cmd_escaped}\\n\\nReason: {reasons}\\n\\nInsert into terminal?" with title "Warning" buttons {{"Cancel", "Insert"}} default button "Insert" cancel button "Cancel"
'''
        proc = await asyncio.create_subprocess_exec(
            "osascript", "-e", apple_script,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        return proc.returncode == 0

    async def _show_dangerous_warning(
        self,
        window_id: Optional[str],
        command: GeneratedCommand
    ) -> bool:
        """Show strong warning dialog for dangerous commands."""
        cmd_escaped = command.command.replace('"', '\\"')
        reasons = ', '.join(command.risk_reasons)
        apple_script = f'''
display dialog "🚨 This command is very dangerous:\\n\\n{cmd_escaped}\\n\\nReason: {reasons}\\n\\nInsert into terminal?" with title "Danger" buttons {{"Cancel", "Insert"}} default button "Cancel" cancel button "Cancel"
'''
        proc = await asyncio.create_subprocess_exec(
            "osascript", "-e", apple_script,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        return proc.returncode == 0

    async def send_to_terminal(self, session: iterm2.Session, command: str) -> None:
        """Send command to terminal without executing."""
        await session.async_send_text(command)

    async def _show_alias_input(self, window_id: Optional[str]) -> Optional[str]:
        """Show alias input dialog for saving command."""
        apple_script = '''
display dialog "Set an alias for this command (optional).\\nAliases help you find commands quickly in history." default answer "" with title "Set Alias" buttons {"Cancel", "OK"} default button "OK" cancel button "Cancel"
'''
        proc = await asyncio.create_subprocess_exec(
            "osascript", "-e", apple_script,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()

        if proc.returncode != 0:
            return None

        output = stdout.decode("utf-8").strip()
        if "text returned:" in output:
            result = output.split("text returned:", 1)[1].strip()
            return result if result else None
        return None

    async def _show_info(self, window_id: Optional[str], message: str) -> None:
        """Show info message dialog."""
        message_escaped = message.replace('"', '\\"').replace('\n', '\\n')
        apple_script = f'''
display dialog "{message_escaped}" with title "Info" buttons {{"OK"}} default button "OK"
'''
        proc = await asyncio.create_subprocess_exec(
            "osascript", "-e", apple_script,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        await proc.communicate()

    async def _show_error(self, message: str) -> None:
        """Show error message dialog."""
        message_escaped = message.replace('"', '\\"').replace('\n', '\\n')
        apple_script = f'''
display dialog "{message_escaped}" with title "Error" buttons {{"OK"}} default button "OK" with icon stop
'''
        proc = await asyncio.create_subprocess_exec(
            "osascript", "-e", apple_script,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        await proc.communicate()

    async def show_history_dialog(self, session: iterm2.Session) -> None:
        """Show history selection dialog using osascript choose from list."""
        try:
            window = self.app.current_terminal_window
            window_id = window.window_id if window else None

            history = self.history_manager.get_all()

            if not history:
                await self._show_info(window_id, "No history saved.")
                return

            # Build list items for choose from list
            list_items = []
            for i, item in enumerate(history, 1):
                alias_text = f" [{item.alias}]" if item.alias else ""
                # Escape quotes and special characters for AppleScript
                cmd_escaped = item.command.replace('\\', '\\\\').replace('"', '\\"').replace('\n', ' ')
                # Truncate long commands
                if len(cmd_escaped) > 80:
                    cmd_escaped = cmd_escaped[:77] + "..."
                list_items.append(f'{i}. {cmd_escaped}{alias_text}')

            # Create AppleScript list string
            items_str = '", "'.join(list_items)

            # Use choose from list for better UI with scrolling
            apple_script = f'''
tell application "iTerm"
    activate
    set historyItems to {{"{items_str}"}}
    set selectedItem to choose from list historyItems with title "Command History" with prompt "Select a command to use:" default items {{item 1 of historyItems}}
    if selectedItem is false then
        return ""
    else
        return item 1 of selectedItem
    end if
end tell
'''
            proc = await asyncio.create_subprocess_exec(
                "osascript", "-e", apple_script,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()

            if proc.returncode != 0:
                logger.error(f"History dialog error: {stderr.decode('utf-8')}")
                return

            result = stdout.decode("utf-8").strip()
            if not result:
                return

            # Extract index from result (e.g., "1. ls -la" -> 1)
            index = int(result.split(".")[0]) - 1
            if 0 <= index < len(history):
                selected = history[index]
                # Update usage count
                self.history_manager.add(selected.prompt, selected.command, selected.alias)
                await self.send_to_terminal(session, selected.command)
        except Exception as e:
            logger.exception(f"History dialog exception: {e}")
            await self._show_error(f"History error: {e}")

    async def show_model_selection(self) -> None:
        """Show model selection dialog."""
        models = [
            "gemini-2.5-flash-lite",
            "gemini-2.5-flash",
            "gemini-2.5-pro",
            "gemini-2.0-flash",
            "gemini-2.0-flash-lite"
        ]

        # Get current model
        current_model = self.gemini_client.model_name if self.gemini_client else "gemini-2.5-flash"

        # Build list with current marker
        list_items = []
        for model in models:
            marker = " (current)" if model == current_model else ""
            list_items.append(f"{model}{marker}")

        items_str = '", "'.join(list_items)

        apple_script = f'''
tell application "iTerm"
    activate
    set modelItems to {{"{items_str}"}}
    set selectedItem to choose from list modelItems with title "Select Model" with prompt "Choose a Gemini model to use:" default items {{item 1 of modelItems}}
    if selectedItem is false then
        return ""
    else
        return item 1 of selectedItem
    end if
end tell
'''
        proc = await asyncio.create_subprocess_exec(
            "osascript", "-e", apple_script,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()

        if proc.returncode != 0:
            return

        result = stdout.decode("utf-8").strip()
        if not result:
            return

        # Extract model name (remove " (current)" suffix if present)
        selected_model = result.replace(" (current)", "").strip()

        if selected_model and selected_model != current_model:
            # Update model in GeminiClient
            if self.gemini_client:
                self.gemini_client.set_model(selected_model)

    async def show_instructions_dialog(self) -> None:
        """Show custom instructions dialog using TextEdit."""
        # Get instructions file path
        instructions_file = Path.home() / ".config" / "iterm2-ai-generator" / "instructions.txt"
        instructions_file.parent.mkdir(parents=True, exist_ok=True)

        # Create file if not exists
        if not instructions_file.exists():
            instructions_file.write_text("# Enter custom instructions for the AI\\n# Example: Always use sudo, use specific paths, etc.\\n", encoding='utf-8')

        # Open with TextEdit
        apple_script = f'''
tell application "TextEdit"
    activate
    open POSIX file "{instructions_file}"
end tell
'''
        await asyncio.create_subprocess_exec(
            "osascript", "-e", apple_script,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )


async def main(connection: iterm2.Connection) -> None:
    """Main entry point."""
    config_manager = ConfigManager()

    # Initialize Gemini client (may have empty API key initially)
    api_key = config_manager.get_api_key() or ""
    gemini_client = GeminiClient(api_key) if api_key else None

    # Create and run the generator
    generator = AICommandGenerator(
        connection,
        config_manager,
        gemini_client
    )
    await generator.run()


iterm2.run_forever(main)
EOF

echo ""
echo "설치가 완료되었습니다!"
echo ""
echo "사용 방법:"
echo "  1. iTerm2를 재시작하세요"
echo "  2. Ctrl+Cmd+A: AI 명령어 생성"
echo "  3. Ctrl+Cmd+S: AI 스크립트 생성"
echo "  4. Ctrl+Cmd+H: 히스토리 보기"
echo "  5. Ctrl+Cmd+M: 모델 변경"
echo ""
echo "처음 실행 시 Google Gemini API 키가 필요합니다."
echo "API 키는 https://aistudio.google.com/apikey 에서 발급받을 수 있습니다."
