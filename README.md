# Wyoming TTS Proxy

This project acts as a transparent proxy for Text To Speech services using the Wyoming protocol. The purpose of this is to sanitize LLM output before being spoken to the user via Home-Assistant Assist Satellites.

Many times, LLMs will include emoji or markdown in their response. This proxy allows you to normalize the text using a combination of built-in flags and custom regex replacements.

### Features

- **Markdown Normalization**: Automatically removes common markdown markers (bold, italic, headers, links, backticks).
- **Emoji Removal**: Strips all emoji characters from the text.
- **Custom Regex Replacements**: Define your own search and replace patterns.

### Configuration

You can provide a YAML configuration file using the `--config` CLI argument. The configuration is validated using Pydantic, ensuring that regex patterns are valid and types are correct.

```yaml
# Example config.yaml
normalize_markdown: true  # Remove markdown formatting
remove_emoji: true        # Remove all emojis
replacements:            # Custom regex replacements
  - regex: "LLM"
    replace: "Large Language Model"
  - regex: "\\d+"
    replace: "NUMBER"
```

### Run

```bash
python3 -m wyoming_tts_proxy \
  --uri tcp://0.0.0.0:10201 \
  --upstream-tts-uri tcp://127.0.0.1:10200 \
  --config config.yaml
```

If you change the TTS engine, you might need to reload the Home Assistant integration to update the data.

All text manipulations are performed in [wyoming_tts_proxy/normalizer.py](wyoming_tts_proxy/normalizer.py).

Inspired by [Wyoming RapidFuzz Proxy](https://github.com/Cheerpipe/wyoming_rapidfuzz_proxy).
