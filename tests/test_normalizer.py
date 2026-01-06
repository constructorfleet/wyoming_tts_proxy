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


def test_remove_urls():
    config = ProxyConfig(remove_urls=True)
    normalizer = TextNormalizer(config=config)
    assert (
        normalizer.normalize("Check this out: https://example.com/test?a=1")
        == "Check this out:"
    )


def test_collapse_whitespace():
    # By default it's false now (actually I should check what the default in config is)
    config = ProxyConfig(collapse_whitespace=True)
    normalizer = TextNormalizer(config=config)
    assert (
        normalizer.normalize("Line 1\n\nLine 2    with spaces")
        == "Line 1 Line 2 with spaces"
    )

    config_no_collapse = ProxyConfig(collapse_whitespace=False)
    normalizer_no_collapse = TextNormalizer(config=config_no_collapse)
    assert normalizer_no_collapse.normalize("Line 1\n\nLine 2") == "Line 1\n\nLine 2"


def test_remove_code_blocks():
    config = ProxyConfig(remove_code_blocks=True, collapse_whitespace=False)
    normalizer = TextNormalizer(config=config)
    text = "Here is some code:\n```python\nprint('hello')\n```\nAnd more text."
    assert normalizer.normalize(text) == "Here is some code:\n\nAnd more text."


def test_max_text_length():
    config = ProxyConfig(max_text_length=10)
    normalizer = TextNormalizer(config=config)
    assert normalizer.normalize("This is too long") == "This is to"


def test_multiple_newlines_stipping():
    # Even without collapse_whitespace, we call strip()
    normalizer = TextNormalizer()
    assert normalizer.normalize("\n\nHello\n\n") == "Hello"
