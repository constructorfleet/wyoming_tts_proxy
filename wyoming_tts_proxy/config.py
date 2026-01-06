from typing import List, Pattern
from pydantic import BaseModel, Field, ConfigDict


class ReplacementConfig(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    regex: Pattern = Field(..., description="Regex pattern to search for")
    replace: str = Field("", description="String to replace the pattern with")


class ProxyConfig(BaseModel):
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
    replacements: List[ReplacementConfig] = Field(
        default_factory=list, description="List of custom regex replacements"
    )
