# --- START OF FILE normalizer.py ---
import logging
import re
import emoji
from typing import Optional
from .config import ProxyConfig

_LOGGER = logging.getLogger(__name__)


class TextNormalizer:
    def __init__(self, config: Optional[ProxyConfig] = None):
        self.config = config or ProxyConfig()
        _LOGGER.info(f"TextNormalizer initialized with config: {self.config}")

    def normalize(self, text: str) -> str:
        if not text:
            return ""

        processed_text = text

        # 1. Triple-backtick code blocks
        if self.config.remove_code_blocks:
            processed_text = re.sub(r"```.*?```", "", processed_text, flags=re.DOTALL)

        # 2. Regex replacements from config
        for replacement in self.config.replacements:
            pattern = replacement.regex
            repl = replacement.replace
            if pattern:
                try:
                    processed_text = re.sub(pattern, repl, processed_text)
                except re.error as e:
                    _LOGGER.error(f"Invalid regex pattern '{pattern}': {e}")

        # 3. URL removal
        if self.config.remove_urls:
            # Simple URL regex
            processed_text = re.sub(r"https?://\S+", "", processed_text)

        # 4. Markdown normalization
        if self.config.normalize_markdown:
            # Simple markdown removal
            # Remove bold/italic markers
            processed_text = re.sub(r"(\*\*|__)(.*?)\1", r"\2", processed_text)
            processed_text = re.sub(r"(\*|_)(.*?)\1", r"\2", processed_text)
            # Remove headers
            processed_text = re.sub(r"^#+\s+", "", processed_text, flags=re.MULTILINE)
            # Remove links [text](url) -> text
            processed_text = re.sub(r"\[(.*?)\]\(.*?\)", r"\1", processed_text)
            # Remove backticks
            processed_text = processed_text.replace("`", "")
        elif self.config.remove_asterisks:
            # Default behavior if not markdown normalized: just remove asterisks as before
            processed_text = processed_text.replace("*", "")

        # 5. Emoji removal
        if self.config.remove_emoji:
            processed_text = emoji.replace_emoji(processed_text, replace="")

        # 6. Character limiting
        if (
            self.config.max_text_length > 0
            and len(processed_text) > self.config.max_text_length
        ):
            _LOGGER.info(f"Truncating text to {self.config.max_text_length} characters")
            processed_text = processed_text[: self.config.max_text_length]

        # 7. Clean up whitespace
        if self.config.collapse_whitespace:
            processed_text = re.sub(r"\s+", " ", processed_text).strip()
        else:
            # Still strip, but don't collapse all to one line if not requested
            processed_text = processed_text.strip()

        _LOGGER.debug(
            f"Original text: '{text[:50]}...' -> Normalized: '{processed_text[:50]}...'"
        )
        return processed_text


# --- END OF FILE normalizer.py ---
