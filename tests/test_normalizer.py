import pytest
from pydantic import ValidationError
from wyoming_tts_proxy.normalizer import TextNormalizer
from wyoming_tts_proxy.config import ProxyConfig, ReplacementConfig


def test_default_normalization():
    # Default behavior: remove asterisks
    normalizer = TextNormalizer()
    assert normalizer.normalize("Hello *world*!") == "Hello world!"


def test_no_normalization():
    # If remove_asterisks is False, we should keep them
    config = ProxyConfig(remove_asterisks=False)
    normalizer = TextNormalizer(config=config)
    assert normalizer.normalize("Hello world!") == "Hello world!"
    assert normalizer.normalize("Hello *world*!") == "Hello *world*!"


def test_remove_asterisk_default():
    # Default is still to remove asterisks
    normalizer = TextNormalizer()
    assert normalizer.normalize("Hello *world*!") == "Hello world!"


def test_remove_emoji():
    config = ProxyConfig(remove_emoji=True)
    normalizer = TextNormalizer(config=config)
    assert normalizer.normalize("Hello 👋 world! 🌍") == "Hello world!"


def test_keep_emoji_by_default():
    normalizer = TextNormalizer()
    assert normalizer.normalize("Hello 👋 world!") == "Hello 👋 world!"


def test_markdown_normalization():
    config = ProxyConfig(normalize_markdown=True)
    normalizer = TextNormalizer(config=config)
    assert (
        normalizer.normalize("## Header\n**Bold** and *italic* and `code`.")
        == "Header Bold and italic and code."
    )
    assert normalizer.normalize("[Link](http://example.com)") == "Link"


def test_regex_replacements():
    config = ProxyConfig(
        replacements=[
            ReplacementConfig(regex=r"LLM", replace="Large Language Model"),
            ReplacementConfig(regex=r"\d+", replace="NUMBER"),
        ]
    )
    normalizer = TextNormalizer(config=config)
    assert (
        normalizer.normalize("The LLM has 123 parameters.")
        == "The Large Language Model has NUMBER parameters."
    )


def test_normalize_empty_text():
    normalizer = TextNormalizer()
    assert normalizer.normalize("") == ""
    assert normalizer.normalize(None) == ""


def test_combined_normalization():
    config = ProxyConfig(
        normalize_markdown=True,
        remove_emoji=True,
        replacements=[ReplacementConfig(regex=r"proxy", replace="gatekeeper")],
    )
    normalizer = TextNormalizer(config=config)
    assert (
        normalizer.normalize("**Hello** proxy! 👋 [test](url)")
        == "Hello gatekeeper! test"
    )


def test_invalid_regex_validation():
    with pytest.raises(ValidationError):
        ReplacementConfig(regex=r"[", replace="error")


def test_empty_string_input():
    normalizer = TextNormalizer()
    assert normalizer.normalize("") == ""


def test_whitespace_only_input():
    normalizer = TextNormalizer()
    assert normalizer.normalize("   \n\t   ") == ""
