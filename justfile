# Kids' Own Stories — Deterministic Task Runner (`just`)

default: test

# Run deterministic completeness & asset verification on all stories in stories.yaml
test:
    uv run --with pyyaml --with pillow python3 bin/test_stories.py

# Run Playwright bounding-box text auto-fit test across all books (sardegna 16p + petit-prince 26p) × 3 tiers × 3 languages
test-fit:
    uv run --with playwright python3 bin/test_kids_text_fit.py

# Run strict acoustic unit test verifying 100% clickable word-audio coverage (non-silent, >= -35dB) across all books
test-words:
    python3 bin/test_word_audio_coverage.py

# Run Playwright E2E & <=12-word chunker test for Layer-1 First Reader Mode (Primi Passi 0.9x)
test-first-reader:
    uv run --with playwright python3 bin/test_first_reader.py

# Alias for test
check: test

# Start local HTTP server with HTTP 206 Partial Content (Range requests) on port 8088
serve port="8088":
    python3 bin/serve_local.py {{port}}

# Run tests and push to origin/main
autopush: test
    git push origin main

