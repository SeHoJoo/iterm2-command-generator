"""Google Gemini API client for iTerm2 AI Command Generator."""

import asyncio
import google.generativeai as genai

from exceptions import APIError, RateLimitError
from models import GeneratedCommand, RiskLevel
from risk_detector import RiskDetector


class GeminiClient:
    """Client for Google Gemini API."""

    def __init__(self, api_key: str):
        """
        Initialize GeminiClient.

        Args:
            api_key: Google Gemini API key.

        Raises:
            ValueError: If API key is empty.
        """
        if not api_key:
            raise ValueError("API key cannot be empty")

        self.api_key = api_key
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-2.5-flash')
        self.risk_detector = RiskDetector()

    async def generate_command(
        self,
        user_input: str,
        working_directory: str,
        shell_type: str
    ) -> GeneratedCommand:
        """
        Generate shell command from natural language input.

        Args:
            user_input: User's natural language description (1-500 chars).
            working_directory: Current working directory.
            shell_type: Shell type (bash/zsh/sh/fish).

        Returns:
            GeneratedCommand with the generated command.

        Raises:
            ValueError: If input is invalid.
            APIError: If API call fails.
            RateLimitError: If API rate limit exceeded.
        """
        if not user_input or len(user_input) > 500:
            raise ValueError("user_input must be 1-500 characters")

        prompt = self._build_generation_prompt(user_input, working_directory, shell_type)

        try:
            # Run synchronous API call in thread executor to avoid blocking event loop
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.model.generate_content(prompt)
            )
            command = self._parse_command_response(response.text)

            # Analyze risk
            risk_result = self.risk_detector.analyze(command)

            return GeneratedCommand(
                command=command,
                request_id="",  # Will be set by caller
                risk_level=risk_result.level,
                risk_reasons=risk_result.reasons
            )

        except Exception as e:
            error_msg = str(e).lower()
            if "quota" in error_msg or "rate" in error_msg or "limit" in error_msg:
                raise RateLimitError(f"API rate limit exceeded: {e}")
            raise APIError(f"Failed to generate command: {e}")

    def _build_generation_prompt(
        self,
        user_input: str,
        working_directory: str,
        shell_type: str
    ) -> str:
        """Build the prompt for command generation."""
        return f"""You are a shell command expert. Generate a single shell command based on the user's request.

Context:
- Operating System: macOS
- Shell: {shell_type}
- Current Directory: {working_directory}

User Request: {user_input}

Rules:
1. Return ONLY the shell command, nothing else
2. No explanations, no markdown, no code blocks
3. Command must be valid for macOS {shell_type}
4. If the request is unclear, generate the most likely intended command
5. Prefer common, well-known commands over obscure ones

Command:"""

    def _parse_command_response(self, response_text: str) -> str:
        """Parse and clean the API response."""
        # Remove any markdown code blocks
        command = response_text.strip()
        if command.startswith("```"):
            lines = command.split("\n")
            # Remove first and last lines (```bash and ```)
            command = "\n".join(lines[1:-1] if len(lines) > 2 else lines)

        # Remove backticks
        command = command.strip("`").strip()

        # Take only the first line if multiple lines
        if "\n" in command:
            command = command.split("\n")[0].strip()

        return command

    async def explain_command(self, command: str) -> str:
        """
        Generate detailed explanation for a command.

        Args:
            command: Shell command to explain.

        Returns:
            Detailed explanation string.

        Raises:
            APIError: If API call fails.
        """
        prompt = f"""Explain this shell command in detail:

Command: {command}

Provide:
1. Overall purpose of the command
2. Explanation of each flag/option
3. Expected output or behavior
4. Any warnings or considerations

Keep the explanation concise but informative. Use simple language."""

        try:
            # Run synchronous API call in thread executor to avoid blocking event loop
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.model.generate_content(prompt)
            )
            return response.text.strip()
        except Exception as e:
            raise APIError(f"Failed to explain command: {e}")
