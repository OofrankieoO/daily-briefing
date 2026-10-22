#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""每日热点简报：从 60s 接口拉取当天新闻列表并打印。

只依赖 Python 标准库，直接运行：

    python fetch_news.py
"""

from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.request

API_URL = "https://60s.viki.moe/v2/60s"
TIMEOUT = 30  # 单次请求超时（秒）
RETRIES = 3  # 失败重试次数
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0 Safari/537.36"
    ),
    "Accept": "application/json",
}


def fetch_payload(url: str = API_URL) -> dict:
    """请求接口并返回解析后的 JSON，失败时抛出 RuntimeError。"""
    last_error: Exception | None = None
    for attempt in range(1, RETRIES + 1):
        request = urllib.request.Request(url, headers=HEADERS)
        try:
            with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
                raw = response.read()
            return json.loads(raw.decode("utf-8"))
        except urllib.error.HTTPError as exc:
            last_error = exc
            print(f"请求失败（HTTP {exc.code}），第 {attempt}/{RETRIES} 次", file=sys.stderr)
        except (urllib.error.URLError, TimeoutError) as exc:
            last_error = exc
            print(f"请求失败（网络异常：{exc}），第 {attempt}/{RETRIES} 次", file=sys.stderr)
        except json.JSONDecodeError as exc:
            last_error = exc
            print(f"响应不是合法 JSON：{exc}", file=sys.stderr)

        if attempt < RETRIES:
            time.sleep(attempt * 2)  # 2s、4s 退避重试

    raise RuntimeError(f"连续 {RETRIES} 次请求失败：{last_error}")


def extract_news(payload: dict) -> list[str]:
    """从返回结构中取出新闻文本列表，兼容字符串和带 title 字段的对象。"""
    data = payload.get("data") or {}
    items = data.get("news") or []
    news: list[str] = []
    for item in items:
        if isinstance(item, str):
            news.append(item)
        elif isinstance(item, dict):
            news.append(str(item.get("title") or item.get("content") or ""))
        if news and not news[-1]:
            news.pop()
    return news


def main() -> int:
    try:
        payload = fetch_payload()
    except RuntimeError as exc:
        print(exc, file=sys.stderr)
        return 1

    code = payload.get("code")
    if code != 200:
        print(f"接口返回异常：code={code}，message={payload.get('message')}", file=sys.stderr)
        return 1

    data = payload.get("data") or {}
    news = extract_news(payload)
    if not news:
        print("接口未返回任何新闻。", file=sys.stderr)
        return 1

    # 管道/重定向时统一按 UTF-8 输出，避免中文乱码；真实控制台保持系统默认行为。
    if hasattr(sys.stdout, "reconfigure") and not sys.stdout.isatty():
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    header = " · ".join(
        part
        for part in (data.get("date"), data.get("day_of_week"), data.get("lunar_date"))
        if part
    )
    if header:
        print(header)
    print(f"共 {len(news)} 条\n")

    width = len(str(len(news)))
    for index, text in enumerate(news, start=1):
        print(f"{index:>{width}}. {text}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
