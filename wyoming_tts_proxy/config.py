from typing import List, Pattern
from pydantic import BaseModel, Field, ConfigDict


class ReplacementConfig(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    regex: Pattern = Field(..., description="Regex pattern to search for")
    replace: str = Field("", description="String to replace the pattern with")


class ProxyConfig(BaseModel):
    upstream_uris: List[str] = Field(
        default_factory=list, description="List of upstream Wyoming TTS service URIs"
    )
    normalize_markdown: bool = Field(
        default=False, description="Whether to remove markdown formatting"
    )
    remove_emoji: bool = Field(
        default=False, description="Whether to remove all emoji characters"
    )
    remove_asterisks: bool = Field(
        default=True,
        description="Whether to remove asterisks (default: true for backward compatibility)",
    )
    remove_urls: bool = Field(
        default=False, description="Whether to remove or replace URLs"
    )
    collapse_whitespace: bool = Field(
        default=True, description="Whether to collapse multiple spaces/newlines"
    )
    remove_code_blocks: bool = Field(
        default=False, description="Whether to remove triple-backtick code blocks"
    )
    max_text_length: int = Field(
        default=0,
        description="Maximum number of characters to send to TTS (0 = unlimited)",
    )
    ssml_template: str = Field(
        default="",
        description="Optional SSML template. Use {{text}} as placeholder. E.g. '<speak>{{text}}</speak>'",
    )
    cache_enabled: bool = Field(default=False, description="Enable audio caching")
    cache_dir: str = Field(
        default="/tmp/wyoming_tts_cache", description="Cache directory"
    )
    max_cache_size_mb: int = Field(default=512, description="Maximum cache size in MB")
    metrics_port: int = Field(
        default=0, description="Prometheus metrics port (0 = disabled)"
    )
    structured_logging: bool = Field(
        default=False, description="Use JSON structured logging"
    )
    replacements: List[ReplacementConfig] = Field(
        default_factory=list, description="List of custom regex replacements"
    )
