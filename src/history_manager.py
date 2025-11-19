"""Command history management for iTerm2 AI Command Generator."""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from models import CommandHistory


class HistoryManager:
    """Manages command history storage and retrieval."""

    def __init__(self, storage_path: Optional[str] = None, max_items: int = 50):
        """
        Initialize HistoryManager.

        Args:
            storage_path: Path to history file. Defaults to ~/.config/iterm2-ai-generator/history.json
            max_items: Maximum number of history items to keep.
        """
        if storage_path is None:
            config_dir = Path.home() / ".config" / "iterm2-ai-generator"
            config_dir.mkdir(parents=True, exist_ok=True)
            storage_path = str(config_dir / "history.json")

        self.storage_path = storage_path
        self.max_items = max_items
        self._history: List[CommandHistory] = self._load_history()

    def _load_history(self) -> List[CommandHistory]:
        """Load history from file."""
        if not os.path.exists(self.storage_path):
            return []

        try:
            with open(self.storage_path, 'r') as f:
                data = json.load(f)
                commands = data.get("commands", [])
                return [CommandHistory.from_dict(cmd) for cmd in commands]
        except (json.JSONDecodeError, IOError, KeyError):
            return []

    def _save_history(self) -> None:
        """Save history to file."""
        data = {
            "version": "1.0",
            "commands": [cmd.to_dict() for cmd in self._history]
        }
        with open(self.storage_path, 'w') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def add(
        self,
        prompt: str,
        command: str,
        alias: Optional[str] = None
    ) -> CommandHistory:
        """
        Add a new command to history.

        Args:
            prompt: Original natural language request.
            command: Generated command.
            alias: Optional alias for the command.

        Returns:
            The saved CommandHistory entry.

        Note:
            If the same command exists, updates use_count instead of adding duplicate.
            Enforces max_items limit by removing least used old items.
        """
        # Check if command already exists
        existing = self._find_by_command(command)
        if existing:
            existing.use_count += 1
            existing.last_used = datetime.now()
            if alias and not existing.alias:
                existing.alias = alias
            self._save_history()
            return existing

        # Create new entry
        entry = CommandHistory(
            prompt=prompt,
            command=command,
            alias=alias
        )

        self._history.append(entry)

        # Enforce max items limit
        if len(self._history) > self.max_items:
            self._remove_least_used()

        self._save_history()
        return entry

    def _find_by_command(self, command: str) -> Optional[CommandHistory]:
        """Find history entry by command string."""
        for entry in self._history:
            if entry.command == command:
                return entry
        return None

    def _remove_least_used(self) -> None:
        """Remove least used old items to maintain max_items limit."""
        # Sort by use_count (ascending) then by last_used (ascending)
        self._history.sort(key=lambda x: (x.use_count, x.last_used))
        # Remove excess items from the beginning (least used/oldest)
        while len(self._history) > self.max_items:
            self._history.pop(0)

    def get_all(self) -> List[CommandHistory]:
        """
        Get all history entries.

        Returns:
            List of CommandHistory sorted by last_used (most recent first).
        """
        return sorted(
            self._history,
            key=lambda x: x.last_used,
            reverse=True
        )

    def get_by_alias(self, alias: str) -> Optional[CommandHistory]:
        """
        Get history entry by alias.

        Args:
            alias: Alias to search for.

        Returns:
            CommandHistory or None if not found.
        """
        for entry in self._history:
            if entry.alias == alias:
                return entry
        return None

    def search(self, query: str) -> List[CommandHistory]:
        """
        Search history by prompt or command.

        Args:
            query: Search query string.

        Returns:
            List of matching CommandHistory entries.
        """
        query_lower = query.lower()
        results = []

        for entry in self._history:
            if (query_lower in entry.prompt.lower() or
                query_lower in entry.command.lower() or
                (entry.alias and query_lower in entry.alias.lower())):
                results.append(entry)

        return sorted(results, key=lambda x: x.last_used, reverse=True)

    def delete(self, id: str) -> bool:
        """
        Delete history entry by ID.

        Args:
            id: Entry ID to delete.

        Returns:
            True if entry was found and deleted.
        """
        for i, entry in enumerate(self._history):
            if entry.id == id:
                self._history.pop(i)
                self._save_history()
                return True
        return False

    def clear(self) -> None:
        """Clear all history entries."""
        self._history = []
        self._save_history()

    def get_count(self) -> int:
        """Get total number of history entries."""
        return len(self._history)
