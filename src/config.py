"""Configuration management for iTerm2 AI Command Generator."""

import json
import os
from pathlib import Path
from typing import Optional

import keyring

from exceptions import ConfigError, KeychainError
from models import AppConfig


class ConfigManager:
    """Application configuration manager."""

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize ConfigManager.

        Args:
            config_path: Path to config file. Defaults to ~/.config/iterm2-ai-generator/config.json
        """
        if config_path is None:
            config_dir = Path.home() / ".config" / "iterm2-ai-generator"
            config_dir.mkdir(parents=True, exist_ok=True)
            config_path = str(config_dir / "config.json")

        self.config_path = config_path
        self.config = self._load_config()

    def _load_config(self) -> AppConfig:
        """Load configuration from file or create default."""
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r') as f:
                    data = json.load(f)
                return AppConfig(
                    api_key_service=data.get("api_key_service", "iterm2-ai-generator"),
                    api_key_account=data.get("api_key_account", "gemini-api-key"),
                    shortcut_key=data.get("shortcut_key", "Ctrl+Shift+A"),
                    max_history=data.get("max_history", 50),
                    max_input_length=data.get("max_input_length", 500)
                )
            except (json.JSONDecodeError, IOError) as e:
                raise ConfigError(f"Failed to load config: {e}")
        return AppConfig()

    def _save_config(self) -> None:
        """Save configuration to file."""
        try:
            data = {
                "version": "1.0",
                "api_key_service": self.config.api_key_service,
                "api_key_account": self.config.api_key_account,
                "shortcut_key": self.config.shortcut_key,
                "max_history": self.config.max_history,
                "max_input_length": self.config.max_input_length
            }
            with open(self.config_path, 'w') as f:
                json.dump(data, f, indent=2)
        except IOError as e:
            raise ConfigError(f"Failed to save config: {e}")

    def get_api_key(self) -> Optional[str]:
        """
        Get API key from macOS Keychain.

        Returns:
            API key string or None if not found.
        """
        try:
            return keyring.get_password(
                self.config.api_key_service,
                self.config.api_key_account
            )
        except Exception as e:
            raise KeychainError(f"Failed to get API key from Keychain: {e}")

    def set_api_key(self, api_key: str) -> None:
        """
        Save API key to macOS Keychain.

        Args:
            api_key: The API key to store.

        Raises:
            KeychainError: If Keychain access fails.
        """
        if not api_key:
            raise ValueError("API key cannot be empty")

        try:
            keyring.set_password(
                self.config.api_key_service,
                self.config.api_key_account,
                api_key
            )
        except Exception as e:
            raise KeychainError(f"Failed to save API key to Keychain: {e}")

    def get_shortcut(self) -> str:
        """
        Get activation shortcut key.

        Returns:
            Shortcut key string (e.g., "Ctrl+Shift+A").
        """
        return self.config.shortcut_key

    def set_shortcut(self, shortcut: str) -> None:
        """
        Set activation shortcut key.

        Args:
            shortcut: New shortcut key string.

        Raises:
            ValueError: If shortcut format is invalid.
        """
        # Basic validation
        valid_modifiers = {"Ctrl", "Shift", "Alt", "Cmd", "Command", "Option"}
        parts = shortcut.replace("+", " ").split()

        if len(parts) < 2:
            raise ValueError("Shortcut must include at least one modifier and a key")

        # Check modifiers
        for part in parts[:-1]:
            if part not in valid_modifiers:
                raise ValueError(f"Invalid modifier: {part}")

        self.config.shortcut_key = shortcut
        self._save_config()

    def get_max_history(self) -> int:
        """Get maximum history items."""
        return self.config.max_history

    def get_max_input_length(self) -> int:
        """Get maximum input length."""
        return self.config.max_input_length
