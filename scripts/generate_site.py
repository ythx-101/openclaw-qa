#!/usr/bin/env python3
"""
Generate static HTML site from QA pipeline JSON output.
"""

import json
import sys
import re
from pathlib import Path
from datetime import datetime


HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>OpenClaw Q&A - 评论区技术问答</title>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    background: #0d1117;
    color: #c9d1d9;
    line-height: 1.6;
}
.container { max-width: 800px; margin: 0 auto; padding: 20px; }
header {
    text-align: center;
    padding: 40px 0 30px;
    border-bottom: 1px solid #21262d;
    margin-bottom: 30px;
}
header h1 {
    font-size: 28px;
    color: #58a6ff;
    margin-bottom: 8px;
}
header p { color: #8b949e; font-size: 14px; }
.stats {
    display: flex;
    justify-content: center;
    gap: 24px;
    margin-top: 16px;
}
.stat {
    text-align: center;
}
.stat-num {
    font-size: 24px;
    font-weight: 700;
    color: #f0f6fc;
}
.stat-label {
    font-size: 12px;
    color: #8b949e;
    text-transform: uppercase;
}
.tweet-section {
    margin-bottom: 40px;
}
.tweet-header {
    background: #161b22;
    border: 1px solid #21262d;
    border-radius: 8px 8px 0 0;
    padding: 16px;
}
.tweet-header a {
    color: #58a6ff;
    text-decoration: none;
    font-size: 13px;
}
.tweet-header a:hover { text-decoration: underline; }
.tweet-text {
    color: #c9d1d9;
    margin-top: 8px;
    font-size: 14px;
}
.qa-list {
    border-left: 1px solid #21262d;
    border-right: 1px solid #21262d;
    border-bottom: 1px solid #21262d;
    border-radius: 0 0 8px 8px;
}
.qa-item {
    padding: 20px;
    border-bottom: 1px solid #21262d;
}
.qa-item:last-child { border-bottom: none; }
.question {
    margin-bottom: 12px;
}
.q-header {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 6px;
}
.q-author {
    font-weight: 600;
    color: #58a6ff;
    font-size: 13px;
}
.q-category {
    background: #1f6feb33;
    color: #58a6ff;
    padding: 2px 8px;
    border-radius: 12px;
    font-size: 11px;
}
.q-stats {
    color: #484f58;
    font-size: 11px;
    margin-left: auto;
}
.q-text {
    color: #f0f6fc;
    font-size: 15px;
    font-weight: 500;
}
.answer {
    background: #161b22;
    border-radius: 8px;
    padding: 14px 16px;
    margin-top: 8px;
}
.answer-label {
    color: #3fb950;
    font-size: 12px;
    font-weight: 600;
    margin-bottom: 6px;
    display: flex;
    align-items: center;
    gap: 4px;
}
.answer-text {
    color: #c9d1d9;
    font-size: 14px;
    white-space: pre-wrap;
}
.answer-text code {
    background: #0d1117;
    padding: 2px 6px;
    border-radius: 4px;
    font-family: "SF Mono", "Fira Code", monospace;
    font-size: 13px;
    color: #79c0ff;
}
.answer-text pre {
    background: #0d1117;
    padding: 12px;
    border-radius: 6px;
    overflow-x: auto;
    margin: 8px 0;
    font-family: "SF Mono", "Fira Code", monospace;
    font-size: 13px;
    line-height: 1.5;
}
footer {
    text-align: center;
    padding: 30px 0;
    border-top: 1px solid #21262d;
    margin-top: 40px;
    color: #484f58;
    font-size: 12px;
}
footer a { color: #58a6ff; text-decoration: none; }
.empty { text-align: center; padding: 60px 20px; color: #484f58; }
@media (max-width: 600px) {
    .container { padding: 12px; }
    header h1 { font-size: 22px; }
    .q-stats { display: none; }
}
</style>
</head>
<body>
<div class="container">
<header>
    <h1>OpenClaw Q&A</h1>
    <p>@YuLin807 评论区技术问答 &middot; AI 驱动自动回答</p>
    <div class="stats">
        <div class="stat">
            <div class="stat-num">{total_qa}</div>
            <div class="stat-label">问答对</div>
        </div>
        <div class="stat">
            <div class="stat-num">{total_tweets}</div>
            <div class="stat-label">推文</div>
        </div>
        <div class="stat">
            <div class="stat-num">{last_updated}</div>
            <div class="stat-label">更新</div>
        </div>
    </div>
</header>
{content}
<footer>
    Powered by <a href="https://github.com/ythx-101/x-tweet-fetcher">x-tweet-fetcher</a>
    + <a href="https://github.com/ythx-101/x-monitor">x-monitor</a>
    &middot; MiniMax M2.5 + Gemini
    &middot; <a href="https://github.com/ythx-101/openclaw-qa">Source</a>
</footer>
</div>
</body>
</html>"""


def escape_html(text):
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def format_answer(text):
    """Format answer text with basic markdown-like rendering."""
    text = escape_html(text)
    # Code blocks
    text = re.sub(
        r'```(\w*)\n(.*?)\n```',
        r'<pre>\2</pre>',
        text,
        flags=re.DOTALL,
    )
    # Inline code
    text = re.sub(r'`([^`]+)`', r'<code>\1</code>', text)
    # Bold
    text = re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', text)
    return text


def generate_html(data):
    """Generate HTML from QA data."""
    content_parts = []

    for tweet in data.get("tweets", []):
        qa_items = []
        for pair in tweet.get("qa_pairs", []):
            q = pair["question"]
            stats = ""
            if q.get("likes") or q.get("views"):
                parts = []
                if q.get("likes"):
                    parts.append(f'{q["likes"]} likes')
                if q.get("views"):
                    parts.append(f'{q["views"]} views')
                stats = " &middot; ".join(parts)

            qa_items.append(f"""<div class="qa-item">
    <div class="question">
        <div class="q-header">
            <span class="q-author">{escape_html(q.get('author_name', q['author']))}</span>
            <span class="q-category">{escape_html(q.get('category', ''))}</span>
            <span class="q-stats">{stats}</span>
        </div>
        <div class="q-text">{escape_html(q['text'])}</div>
    </div>
    <div class="answer">
        <div class="answer-label">AI Answer</div>
        <div class="answer-text">{format_answer(pair['answer'])}</div>
    </div>
</div>""")

        tweet_url = tweet.get("tweet_url", "")
        tweet_text = tweet.get("tweet_text", "")[:150]

        content_parts.append(f"""<div class="tweet-section">
    <div class="tweet-header">
        <a href="{escape_html(tweet_url)}" target="_blank">View original tweet</a>
        <div class="tweet-text">{escape_html(tweet_text)}{'...' if len(tweet.get('tweet_text', '')) > 150 else ''}</div>
    </div>
    <div class="qa-list">
        {''.join(qa_items)}
    </div>
</div>""")

    if not content_parts:
        content_parts.append('<div class="empty">暂无问答内容</div>')

    now = datetime.utcnow()
    html = HTML_TEMPLATE
    html = html.replace("{total_qa}", str(data.get("total_qa", 0)))
    html = html.replace("{total_tweets}", str(data.get("total_tweets", 0)))
    html = html.replace("{last_updated}", now.strftime("%m/%d"))
    html = html.replace("{content}", "\n".join(content_parts))
    return html


def main():
    if len(sys.argv) < 2:
        print("Usage: generate_site.py <qa_data.json> [output_dir]", file=sys.stderr)
        sys.exit(1)

    data_file = Path(sys.argv[1])
    output_dir = Path(sys.argv[2]) if len(sys.argv) > 2 else Path(".")

    with open(data_file, encoding="utf-8") as f:
        data = json.load(f)

    html = generate_html(data)

    output_dir.mkdir(parents=True, exist_ok=True)
    index_path = output_dir / "index.html"
    with open(index_path, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"[OK] Generated: {index_path}", file=sys.stderr)
    print(f"[OK] {data.get('total_qa', 0)} Q&A pairs", file=sys.stderr)


if __name__ == "__main__":
    main()
