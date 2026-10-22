#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""每日热点简报：把 fetch_news.py 拿到的新闻交给 DeepSeek，生成 Markdown 简报并打印。

运行前设置环境变量 DEEPSEEK_API_KEY：

    set DEEPSEEK_API_KEY=sk-xxxx
    python summarize.py
"""

from __future__ import annotations

import json
import os
import sys
import urllib.request

from fetch_news import extract_news, fetch_payload

API_URL = "https://api.deepseek.com/chat/completions"
MODEL = "deepseek-flash"

PROMPT = """从以下新闻中选出5条最值得关注的，将它们分为（国内）和（国外）两个模块。国内新闻放在（##国内）下，国外新闻放在（##国外）下，每个模块内每条新闻用一句话说明为什么值得看。如果某条新闻难以判断归属，归入（国内）。输出Markdown格式，不要输出其他内容。"""


def build_messages(news: list[str]) -> list[dict]:
    """把简报要求和编号新闻列表拼成一条用户消息。"""
    joined = "\n".join(f"{index}. {text}" for index, text in enumerate(news, 1))
    return [{"role": "user", "content": f"{PROMPT}\n\n{joined}"}]


def main() -> int:
    news = extract_news(fetch_payload())

    payload = {
        "model": MODEL,
        "messages": build_messages(news),
        "temperature": 0.3,
        "stream": False,
    }
    request = urllib.request.Request(
        API_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {os.environ['DEEPSEEK_API_KEY']}",
        },
        method="POST",
    )

    with urllib.request.urlopen(request, timeout=120) as response:
        result = json.loads(response.read().decode("utf-8"))

    markdown = result["choices"][0]["message"]["content"].strip()

    # 管道/重定向时统一按 UTF-8 输出，避免中文乱码；真实控制台保持系统默认行为。
    if hasattr(sys.stdout, "reconfigure") and not sys.stdout.isatty():
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    print(markdown)
    return 0


if __name__ == "__main__":
    sys.exit(main())
