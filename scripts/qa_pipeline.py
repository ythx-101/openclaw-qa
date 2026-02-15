#!/usr/bin/env python3
"""
OpenClaw QA Pipeline
====================
Fetches tweet replies, filters technical questions (MiniMax),
generates answers (Gemini), outputs JSON for static site.

Usage:
    python3 qa_pipeline.py --urls tweets.txt --output qa_data.json
    python3 qa_pipeline.py --url "https://x.com/YuLin807/status/123" --output qa_data.json
"""

import json
import sys
import os
import subprocess
import argparse
import re
import time
from pathlib import Path
from datetime import datetime


# Paths
TWEET_FETCHER = "/root/github-repos/x-tweet-fetcher/scripts/fetch_tweet.py"
MONITOR_SCRIPT = "/tmp/x-monitor/scripts/monitor.py"
OUTPUT_DIR = Path("/root/openclaw-qa/data")


def run_cmd(cmd, timeout=60):
    """Run a shell command and return stdout."""
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=timeout
        )
        return result.stdout.strip(), result.returncode
    except subprocess.TimeoutExpired:
        return "", 1


def fetch_tweet(url):
    """Fetch tweet content via x-tweet-fetcher."""
    out, rc = run_cmd(f'python3 {TWEET_FETCHER} --url "{url}"')
    if rc == 0 and out:
        return json.loads(out)
    return None


def fetch_replies(url):
    """Fetch tweet replies via x-monitor."""
    out, rc = run_cmd(
        f'python3 {MONITOR_SCRIPT} --url "{url}"', timeout=30
    )
    if rc == 0 and out:
        return json.loads(out)
    return None


def classify_questions_minimax(replies):
    """Use MiniMax M2.5 to classify which replies are real technical questions.

    Input: list of reply dicts with 'text' field
    Output: list of reply dicts that are technical questions, with 'category' added
    """
    if not replies:
        return []

    # Pre-filter with heuristic
    candidates = [r for r in replies if r.get("is_question", False)]
    if not candidates:
        return []

    # Build prompt for MiniMax batch classification
    texts = []
    for i, r in enumerate(candidates):
        texts.append(f"{i+1}. @{r['author']}: {r['text']}")

    prompt = f"""你是一个技术问题分类助手。以下是社交媒体评论中的回复，请判断哪些是真正的技术问题（关于编程、AI、工具使用、部署、配置等），哪些不是（闲聊、求私信、赞美等）。

回复列表：
{chr(10).join(texts)}

请用JSON数组格式回复，每个元素包含：
- "id": 序号（对应上面的编号）
- "is_tech": true/false（是否为技术问题）
- "category": 分类（如 "开发工具", "AI配置", "部署", "API使用", "安全", "其他"）
- "summary": 一句话概括问题（如果是技术问题）

只返回JSON数组，不要其他文字。"""

    # Write prompt to temp file to avoid shell escaping issues
    import tempfile
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as tmp:
        tmp.write(prompt)
        prompt_file = tmp.name

    out, rc = run_cmd(
        f"bash -l -c 'opencode run -m minimax-coding-plan/MiniMax-M2.5 \"$(cat {prompt_file})\" 2>/dev/null'",
        timeout=60,
    )
    os.unlink(prompt_file)

    if rc != 0 or not out:
        # Fallback: return all candidates with heuristic classification
        for r in candidates:
            r["category"] = "general"
            r["summary"] = r["text"][:50]
        return candidates

    # Parse MiniMax response
    try:
        # Extract JSON from response (may have markdown fences)
        json_match = re.search(r'\[[\s\S]*\]', out)
        if json_match:
            classifications = json.loads(json_match.group())
        else:
            classifications = json.loads(out)

        tech_questions = []
        for cls in classifications:
            idx = cls.get("id", 0) - 1
            if cls.get("is_tech") and 0 <= idx < len(candidates):
                reply = candidates[idx].copy()
                reply["category"] = cls.get("category", "general")
                reply["summary"] = cls.get("summary", reply["text"][:50])
                tech_questions.append(reply)
        return tech_questions

    except (json.JSONDecodeError, KeyError):
        # Fallback
        for r in candidates:
            r["category"] = "general"
            r["summary"] = r["text"][:50]
        return candidates


def generate_answer_gemini(question_text, tweet_context=""):
    """Use Gemini CLI to generate a technical answer."""
    context_part = ""
    if tweet_context:
        context_part = f"原始推文内容：{tweet_context}\\n\\n"

    prompt = f"""{context_part}用户在评论区提出了这个技术问题：

{question_text}

请用中文给出简洁、实用的技术回答。要求：
1. 直接回答问题，不要废话
2. 如果涉及代码，给出关键示例
3. 如果涉及安全问题，说明防护措施
4. 保持在200字以内"""

    # Write prompt to temp file to avoid shell escaping
    import tempfile
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as tmp:
        tmp.write(prompt)
        prompt_file = tmp.name

    out, rc = run_cmd(
        f'bash -l -c \'gemini -p "$(cat {prompt_file})"\'',
        timeout=45,
    )
    os.unlink(prompt_file)

    if rc == 0 and out:
        # Clean up Gemini output (remove hook registry line etc)
        lines = out.split("\n")
        cleaned = [l for l in lines if not l.startswith("Hook registry")]
        return "\n".join(cleaned).strip()

    return "抱歉，暂时无法生成回答。请稍后再试。"


def process_tweet(url):
    """Full pipeline for one tweet."""
    print(f"[*] Processing: {url}", file=sys.stderr)

    # Step 1: Fetch tweet content
    print("  [1/4] Fetching tweet...", file=sys.stderr)
    tweet_data = fetch_tweet(url)
    tweet_text = ""
    if tweet_data and "tweet" in tweet_data:
        t = tweet_data["tweet"]
        tweet_text = t.get("text", "")
        if t.get("is_article") and t.get("article", {}).get("full_text"):
            tweet_text = t["article"]["full_text"][:500]

    # Step 2: Fetch replies
    print("  [2/4] Fetching replies...", file=sys.stderr)
    monitor_data = fetch_replies(url)
    if not monitor_data or monitor_data.get("error"):
        print(f"  [!] No replies or error: {monitor_data}", file=sys.stderr)
        return None

    replies = monitor_data.get("replies", [])
    if not replies:
        print("  [!] No replies found", file=sys.stderr)
        return None

    # Step 3: Classify with MiniMax
    print(f"  [3/4] Classifying {len(replies)} replies with MiniMax...", file=sys.stderr)
    tech_questions = classify_questions_minimax(replies)
    if not tech_questions:
        print("  [!] No technical questions found", file=sys.stderr)
        return None

    print(f"  [->] Found {len(tech_questions)} technical questions", file=sys.stderr)

    # Step 4: Generate answers with Gemini
    print(f"  [4/4] Generating answers with Gemini...", file=sys.stderr)
    qa_pairs = []
    for q in tech_questions:
        print(f"    Answering: {q['text'][:40]}...", file=sys.stderr)
        answer = generate_answer_gemini(q["text"], tweet_text)
        qa_pairs.append({
            "question": {
                "author": q["author"],
                "author_name": q.get("author_name", q["author"]),
                "text": q["text"],
                "category": q.get("category", "general"),
                "summary": q.get("summary", ""),
                "likes": q.get("likes", 0),
                "views": q.get("views", 0),
            },
            "answer": answer,
        })
        time.sleep(1)  # Rate limit courtesy

    return {
        "tweet_url": url,
        "tweet_text": tweet_text[:200],
        "tweet_author": tweet_data["tweet"]["screen_name"] if tweet_data and "tweet" in tweet_data else "",
        "total_replies": len(replies),
        "qa_count": len(qa_pairs),
        "qa_pairs": qa_pairs,
        "generated_at": datetime.utcnow().isoformat(),
    }


def main():
    parser = argparse.ArgumentParser(description="OpenClaw QA Pipeline")
    parser.add_argument("--url", help="Single tweet URL to process")
    parser.add_argument("--urls", help="File with tweet URLs (one per line)")
    parser.add_argument("--output", "-o", default="qa_data.json", help="Output JSON file")

    args = parser.parse_args()

    urls = []
    if args.url:
        urls.append(args.url)
    elif args.urls:
        with open(args.urls) as f:
            urls = [line.strip() for line in f if line.strip() and not line.startswith("#")]
    else:
        parser.error("Provide --url or --urls")

    all_results = []
    for url in urls:
        result = process_tweet(url)
        if result:
            all_results.append(result)

    output_data = {
        "generated_at": datetime.utcnow().isoformat(),
        "total_tweets": len(urls),
        "total_qa": sum(r["qa_count"] for r in all_results),
        "tweets": all_results,
    }

    # Write output
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)

    print(f"\n[OK] Generated {output_data['total_qa']} Q&A pairs from {len(all_results)} tweets", file=sys.stderr)
    print(f"[OK] Output: {output_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
