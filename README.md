# Wyoming TTS Proxy

This project acts as a transparent proxy for Text To Speech services using the Wyoming protocol. The purpose of this is to sanitize LLM output before being spoken to the user via Home-Assistant Assist Satellites.

Many times, LLMs will include emoji or markdown in their response. This proxy allows you to normalize the text using a combination of built-in flags and custom regex replacements.

### Features

- **Streaming TTS Support**: Automatically detect streaming input and stream to upstream, or force streaming mode with `--stream-tts` flag.
- **Upstream Failover**: Support multiple upstream TTS servers for high availability.
- **Audio Caching**: Disk-based caching of synthesized audio with LRU pruning and size limits.
- **Prometheus Metrics & Health**: Built-in exporter for metrics and a `/health` endpoint for Docker/Kubernetes.
- **Structured Logging**: Optional JSON-formatted logs for better observability.
- **SSML Support**: Wrap normalized text in an SSML template before sending to upstream.
- **Markdown Normalization**: Automatically removes common markdown markers (bold, italic, headers, links, backticks).
- **Emoji Removal**: Strips all emoji characters from the text.
- **URL Removal**: Strip `http://` and `https://` links to prevent TTS from reading out long URLs.
- **Code Block Cleaning**: Remove triple-backtick code blocks (` ``` `).
- **Whitespace Collapsing**: Collapse multiple spaces and newlines into a single space for smoother TTS flow.
- **Character Limiting**: Truncate long responses to a maximum length to prevent runaway TTS.
- **Custom Regex Replacements**: Define your own search and replace patterns.
- **Development Tools**: Built-in scripts for linting, formatting, and high test coverage.

### Configuration

You can provide a YAML configuration file using the `--config` CLI argument. The configuration is validated using Pydantic, ensuring that regex patterns are valid and types are correct.

```yaml
# Example config.yaml
normalize_markdown: true   # Remove markdown formatting
remove_emoji: true         # Remove all emojis
remove_asterisks: true     # Remove asterisks (default)
remove_urls: true          # Strip http/https links
collapse_whitespace: true  # (default: true) Smooth pauses
remove_code_blocks: true   # Strip ``` blocks
max_text_length: 500       # Truncate to 500 chars (0 = disable)
replace_newlines: " "      # Replace newlines (default: " ")

# Advanced Features
upstream_uris:             # Multiple upstreams for failover
  - tcp://127.0.0.1:10200
  - tcp://127.0.0.1:10201
cache_enabled: true        # Enable disk caching
cache_dir: /tmp/tts_cache  # Directory for cached audio
max_cache_size_mb: 512     # Prune oldest files when limit reached
structured_logging: true   # Output JSON logs
ssml_template: "<speak>{{text}}</speak>" # Wrap text in SSML
stream_tts: true           # Force streaming TTS output

replacements:              # Custom regex replacements
  - regex: "LLM"
    replace: "Large Language Model"
```

### Run

You can run the proxy using CLI arguments or environment variables.

#### CLI Arguments

```bash
python3 -m wyoming_tts_proxy \
  --uri tcp://0.0.0.0:10201 \
  --upstream-tts-uri tcp://127.0.0.1:10200 \
  --upstream-tts-uri tcp://127.0.0.1:10201 \
  --cache-dir ./cache \
  --max-cache-size-mb 512 \
  --metrics-port 8000 \
  --structured-logging \
  --ssml-template "<speak>{{text}}</speak>" \
  --stream-tts \
  --config config.yaml \
  --log-level DEBUG
```

- `--uri`: URI where this proxy server will listen (default: `tcp://0.0.0.0:10201`)
- `--upstream-tts-uri`: URI of the upstream Wyoming TTS service (can be specified multiple times for failover)
- `--cache-dir`: Directory to store synthesized audio files
- `--max-cache-size-mb`: Maximum size of cache directory in MB (default: 512)
- `--disable-cache`: Disable audio caching
- `--metrics-port`: Port to export Prometheus metrics and health check (0 = disabled)
- `--structured-logging`: Use JSON formatted logs
- `--ssml-template`: Template to wrap normalized text in before synthesis
- `--stream-tts`: Force streaming TTS output even for non-streaming input (env: `STREAM_TTS`)
- `--config`: Path to YAML configuration file
- `--log-level`: Logging level (`DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`; default: `INFO`)
- `--debug`: Shortcut for `--log-level DEBUG`

#### Environment Variables

- `LISTEN_URI`: URI where this proxy server will listen (default: `tcp://0.0.0.0:10201`)
- `UPSTREAM_TTS_URI`: URI(s) of the upstream Wyoming TTS service (comma-separated; **required**)
- `CACHE_ENABLED`: Set to `false` to disable caching
- `CACHE_DIR`: Directory for audio cache
- `MAX_CACHE_SIZE_MB`: Limit cache size (default: 512)
- `METRICS_PORT`: Port for Prometheus metrics and health check
- `STRUCTURED_LOGGING`: Set to `true` for JSON logs
- `SSML_TEMPLATE`: Template for SSML wrapping
- `STREAM_TTS`: Set to `true` to force streaming TTS output
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

This project uses `uv` for dependency management. GitHub Actions are configured to run linting, formatting, and tests on every Pull Request. Pull Request coverage is reported as a comment.

On push to the `main` branch, the project is automatically checked, and a Docker image is built and published to the GitHub Container Registry (GHCR).

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
