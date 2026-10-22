#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""每日热点简报：抓取 60s 新闻 -> DeepSeek 加工成国内/国外两板块 -> 写入 reports/YYYY-MM-DD.md。

运行前设置环境变量 DEEPSEEK_API_KEY：

    set DEEPSEEK_API_KEY=sk-xxxx
    python main.py
"""

from __future__ import annotations

import json
import os
import sys
import urllib.request
from datetime import date
from pathlib import Path

NEWS_API = "https://60s.viki.moe/v2/60s"
DEEPSEEK_API = "https://api.deepseek.com/chat/completions"
MODEL = "deepseek-flash"
SOURCE_URL = NEWS_API
REPORTS_DIR = Path(__file__).resolve().parent / "reports"

TIMEOUT = 30  # 单次请求超时（秒）
RETRIES = 3  # 新闻接口失败重试次数
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0 Safari/537.36"
    ),
    "Accept": "application/json",
}

PROMPT = """从以下新闻中选出5条最值得关注的，将它们分为（国内）和（国外）两个模块。国内新闻放在（##国内）下，国外新闻放在（##国外）下，每个模块内每条新闻用一句话说明为什么值得看。如果某条新闻难以判断归属，归入（国内）。输出Markdown格式，不要输出其他内容。"""


def fetch_news() -> tuple[str, list[str]]:
    """抓取新闻，返回（新闻日期, 新闻文本列表）。"""
    last_error: Exception | None = None
    for attempt in range(1, RETRIES + 1):
        request = urllib.request.Request(NEWS_API, headers=HEADERS)
        try:
            with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
                payload = json.loads(response.read().decode("utf-8"))
            break
        except Exception as exc:  # 网络抖动时重试
            last_error = exc
            print(f"抓取新闻失败（{exc}），第 {attempt}/{RETRIES} 次", file=sys.stderr)
    else:
        raise RuntimeError(f"连续 {RETRIES} 次抓取失败：{last_error}")

    data = payload.get("data") or {}
    news = [item if isinstance(item, str) else str(item.get("title", "")) for item in data.get("news") or []]
    news = [text for text in news if text]

    news_date = str(data.get("date") or "")
    if len(news_date) != 10 or news_date[4] != "-" or news_date[7] != "-":
        news_date = date.today().isoformat()

    return news_date, news


def summarize(news: list[str]) -> str:
    """调用 DeepSeek 生成简报正文。"""
    joined = "\n".join(f"{index}. {text}" for index, text in enumerate(news, 1))
    payload = {
        "model": MODEL,
        "messages": [{"role": "user", "content": f"{PROMPT}\n\n{joined}"}],
        "temperature": 0.3,
        "stream": False,
    }
    request = urllib.request.Request(
        DEEPSEEK_API,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {os.environ['DEEPSEEK_API_KEY']}",
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=120) as response:
        result = json.loads(response.read().decode("utf-8"))
    return result["choices"][0]["message"]["content"]


def strip_code_fence(text: str) -> str:
    """去掉模型可能包在外层的 ```markdown / ``` 代码块标记。"""
    text = text.strip()
    if not text.startswith("```"):
        return text

    lines = text.splitlines()
    lines = lines[1:]  # 开头的 ```markdown
    if lines and lines[-1].strip() == "```":
        lines = lines[:-1]
    return "\n".join(lines).strip()


def render_report(news_date: str, body: str) -> str:
    """拼出最终文件内容：标题 + 来源 + 简报正文，不加任何多余内容。"""
    return (
        f"# 每日热点简报（{news_date}）\n"
        f"\n"
        f"数据来源：[60s API]({SOURCE_URL})\n"
        f"\n"
        f"{body}\n"
    )


def write_report(news_date: str, content: str) -> Path:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    path = REPORTS_DIR / f"{news_date}.md"
    path.write_text(content, encoding="utf-8")
    return path


def main() -> int:
    news_date, news = fetch_news()
    if not news:
        raise RuntimeError("接口没有返回任何新闻")

    body = strip_code_fence(summarize(news))
    path = write_report(news_date, render_report(news_date, body))

    if hasattr(sys.stdout, "reconfigure") and not sys.stdout.isatty():
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    print(f"已写入 {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
