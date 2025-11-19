"""iTerm2 AI Command Generator package."""

import logging
import os
from pathlib import Path

# Setup logging
log_dir = Path.home() / ".config" / "iterm2-ai-generator"
log_dir.mkdir(parents=True, exist_ok=True)
log_file = log_dir / "debug.log"

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("iterm2-ai-generator")
