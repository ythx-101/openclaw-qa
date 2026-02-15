#!/bin/bash
# OpenClaw QA - Full pipeline: fetch → classify → answer → generate → deploy
# Usage: ./run_qa.sh [tweet_url ...]
# If no URLs given, reads from data/tweets.txt

set -e
cd "$(dirname "$0")/.."

SCRIPT_DIR="scripts"
DATA_DIR="data"
TWEETS_FILE="$DATA_DIR/tweets.txt"

# Collect URLs
if [ $# -gt 0 ]; then
    URLS="$@"
    URL_ARGS=""
    for url in $URLS; do
        URL_ARGS="$URL_ARGS --url $url"
    done
    # Single URL mode
    python3 "$SCRIPT_DIR/qa_pipeline.py" --url "$1" --output "$DATA_DIR/qa_data.json"
else
    if [ ! -f "$TWEETS_FILE" ]; then
        echo "No tweet URLs provided and $TWEETS_FILE not found"
        exit 1
    fi
    python3 "$SCRIPT_DIR/qa_pipeline.py" --urls "$TWEETS_FILE" --output "$DATA_DIR/qa_data.json"
fi

# Generate HTML
python3 "$SCRIPT_DIR/generate_site.py" "$DATA_DIR/qa_data.json" .

# Git commit and push
git add index.html data/qa_data.json
if git diff --cached --quiet; then
    echo "[*] No changes to commit"
else
    git commit -m "Update Q&A $(date +%Y-%m-%d)"
    git push origin main
    echo "[OK] Deployed to GitHub Pages"
fi
