# Kids' Own Stories — Deterministic Task Runner (`just`)

default: test

# Run deterministic completeness & asset verification on all stories in stories.yaml
test:
    python3 bin/test_stories.py

# Alias for test
check: test

# Start local HTTP server with HTTP 206 Partial Content (Range requests) on port 8088
serve port="8088":
    python3 bin/serve_local.py {{port}}
