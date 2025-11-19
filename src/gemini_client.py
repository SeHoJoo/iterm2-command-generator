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
        self.model_name = 'gemini-2.5-flash-lite'
        self.model = genai.GenerativeModel(self.model_name)
        self.risk_detector = RiskDetector()

    def set_model(self, model_name: str) -> None:
        """
        Change the Gemini model.

        Args:
            model_name: Name of the model to use.
        """
        self.model_name = model_name
        self.model = genai.GenerativeModel(model_name)

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
- Operating System: Linux
- Shell: {shell_type}
- Current Directory: {working_directory}

User Request: {user_input}

Rules:
1. Return ONLY the shell command, nothing else
2. No explanations, no markdown, no code blocks
3. Command must be valid for Linux {shell_type}
4. If the request is unclear, generate the most likely intended command
5. Prefer common, well-known commands over obscure ones

Command:"""

    async def generate_script(
        self,
        user_input: str,
        working_directory: str,
        shell_type: str
    ) -> str:
        """
        Generate a bash script from natural language.

        Args:
            user_input: Natural language description of the script.
            working_directory: Current working directory.
            shell_type: Type of shell (bash, zsh, etc.)

        Returns:
            Generated bash script as string.
        """
        if not user_input or len(user_input) > 1000:
            raise ValueError("user_input must be 1-1000 characters")

        prompt = f"""You are a bash script expert. Generate a complete bash script based on the user's request.

Context:
- Operating System: Linux
- Shell: {shell_type}
- Current Directory: {working_directory}

User Request: {user_input}

Rules:
1. Return ONLY the bash script, nothing else
2. Include proper shebang (#!/bin/bash)
3. Add comments to explain each section
4. Include error handling where appropriate
5. Script must be valid for Linux {shell_type}
6. No markdown code blocks, just the raw script

Script:"""

        try:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.model.generate_content(prompt)
            )
            return self._parse_script_response(response.text)

        except Exception as e:
            error_msg = str(e).lower()
            if "quota" in error_msg or "rate" in error_msg or "limit" in error_msg:
                raise RateLimitError(f"API rate limit exceeded: {e}")
            raise APIError(f"Failed to generate script: {e}")

    def _parse_script_response(self, response_text: str) -> str:
        """Parse and clean the script response."""
        script = response_text.strip()
        # Remove markdown code blocks if present
        if script.startswith("```"):
            lines = script.split("\n")
            # Remove first line (```bash) and last line (```)
            if lines[-1].strip() == "```":
                lines = lines[1:-1]
            else:
                lines = lines[1:]
            script = "\n".join(lines)
        return script.strip()

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
