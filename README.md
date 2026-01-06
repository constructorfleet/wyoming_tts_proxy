# Wyoming TTS Proxy

This project acts as a transparent proxy for Text To Speech services using the Wyoming protocol. The purpose of this is to sanitize LLM output before being spoken to the user via Home-Assistant Assist Satellites.

Many times, LLMs will include emoji or markdown in their response. This proxy allows you to normalize the text using a combination of built-in flags and custom regex replacements.

### Features

- **Markdown Normalization**: Automatically removes common markdown markers (bold, italic, headers, links, backticks).
- **Emoji Removal**: Strips all emoji characters from the text.
- **Custom Regex Replacements**: Define your own search and replace patterns.
- **Development Tools**: Built-in scripts for linting, formatting, and high test coverage.

### Configuration

You can provide a YAML configuration file using the `--config` CLI argument. The configuration is validated using Pydantic, ensuring that regex patterns are valid and types are correct.

```yaml
# Example config.yaml
normalize_markdown: true  # Remove markdown formatting
remove_emoji: true        # Remove all emojis
remove_asterisks: true    # Remove asterisks (default)
replacements:            # Custom regex replacements
  - regex: "LLM"
    replace: "Large Language Model"
  - regex: "\\d+"
    replace: "NUMBER"
```

### Run

You can run the proxy using CLI arguments or environment variables.

#### CLI Arguments

```bash
python3 -m wyoming_tts_proxy \
  --uri tcp://0.0.0.0:10201 \
  --upstream-tts-uri tcp://127.0.0.1:10200 \
  --config config.yaml \
  --log-level DEBUG
```

- `--uri`: URI where this proxy server will listen (default: `tcp://0.0.0.0:10201`)
- `--upstream-tts-uri`: URI of the upstream Wyoming TTS service
- `--config`: Path to YAML configuration file
- `--log-level`: Logging level (`DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`; default: `INFO`)
- `--debug`: Shortcut for `--log-level DEBUG`

#### Environment Variables

- `LISTEN_URI`: URI where this proxy server will listen (default: `tcp://0.0.0.0:10201`)
- `UPSTREAM_TTS_URI`: URI of the upstream Wyoming TTS service (**required**)
- `CONFIG_FILE_PATH`: Path to the YAML configuration file
- `LOG_LEVEL`: Logging level (default: `INFO`)

Example:
```bash
UPSTREAM_TTS_URI=tcp://127.0.0.1:10200 python3 -m wyoming_tts_proxy
```

### Docker

You can also run the proxy using Docker.

#### Build the image

```bash
docker build -t wyoming-tts-proxy .
```

#### Run the container

```bash
docker run -it --rm \
  -p 10201:10201 \
  -e UPSTREAM_TTS_URI=tcp://192.168.1.100:10200 \
  wyoming-tts-proxy
```

If you need to provide a custom configuration file:

```bash
docker run -it --rm \
  -p 10201:10201 \
  -e UPSTREAM_TTS_URI=tcp://192.168.1.100:10200 \
  -e CONFIG_FILE_PATH=/config/config.yaml \
  -v $(pwd)/config.yaml:/config/config.yaml \
  wyoming-tts-proxy
```

If you change the TTS engine, you might need to reload the Home Assistant integration to update the data.

### Development

This project uses `uv` for dependency management.

```bash
# Register venv and install dependencies
uv sync

# Run the master check (format, lint, and test with coverage)
./scripts/check

# Individual scripts
./scripts/format  # Reformat code with ruff
./scripts/lint    # Check linting with ruff
./scripts/test    # Run tests and report coverage (requires 85%+)
```

All text manipulations are performed in [wyoming_tts_proxy/normalizer.py](wyoming_tts_proxy/normalizer.py).

Inspired by [Wyoming RapidFuzz Proxy](https://github.com/Cheerpipe/wyoming_rapidfuzz_proxy).
