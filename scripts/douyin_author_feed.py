#!/usr/bin/env python3
"""抖音作者视频列表抓取与按天过滤。"""

from __future__ import annotations

import re
from http.cookies import SimpleCookie
import os
from contextlib import contextmanager
from datetime import date, datetime
from typing import Any, Iterator
from urllib.parse import urlparse
from zoneinfo import ZoneInfo


SHANGHAI_TZ = ZoneInfo("Asia/Shanghai")
PUBLISH_TIME_PATTERN = re.compile(r"发布时间[:：]\s*(\d{4}-\d{2}-\d{2})\s+(\d{2}:\d{2})")
TITLE_DATE_PATTERN = re.compile(r"(20\d{6})(?!\d)")


def extract_author_id(author_url: str) -> str:
    """从抖音作者 URL 提取作者 ID。"""
    parsed = urlparse(author_url)
    path_segments = [segment for segment in parsed.path.split("/") if segment]
    if len(path_segments) < 2 or path_segments[0] != "user":
        raise ValueError(f"invalid douyin author url: {author_url}")
    return path_segments[1]


def normalize_author_url(author_url: str) -> str:
    """规范化作者主页 URL。"""
    author_id = extract_author_id(author_url)
    return f"https://www.douyin.com/user/{author_id}"


def parse_publish_time(value: Any) -> datetime | None:
    """解析发布时间。

    输入支持 epoch 秒/毫秒整数，或仅包含数字的字符串。
    规则是绝对值大于等于 10^12 视为毫秒，否则视为秒。
    返回上海时区的 `datetime`；无法解析时返回 `None`。
    """
    if value is None:
        return None

    if isinstance(value, str):
        normalized = value.strip()
        if not normalized:
            return None
        if normalized[0] in "+-":
            digits = normalized[1:]
        else:
            digits = normalized
        if not digits.isdigit():
            return None
        value = int(normalized)
    elif isinstance(value, bool) or not isinstance(value, int):
        return None

    timestamp = value / 1000 if abs(value) >= 10**12 else value
    return datetime.fromtimestamp(timestamp, tz=SHANGHAI_TZ)


def parse_publish_time_text(value: str) -> datetime | None:
    """从抖音页面文案中提取发布时间。"""
    match = PUBLISH_TIME_PATTERN.search(value)
    if match is None:
        return None
    return datetime.fromisoformat(f"{match.group(1)}T{match.group(2)}:00+08:00")


def extract_title_date(value: str) -> date | None:
    """从标题尾部的 YYYYMMDD 解析日期。"""
    match = TITLE_DATE_PATTERN.search(value)
    if match is None:
        return None
    try:
        return datetime.strptime(match.group(1), "%Y%m%d").date()
    except ValueError:
        return None


def filter_today_videos(videos: list[dict[str, Any]], target_day: date | None = None) -> list[dict[str, Any]]:
    """过滤目标日期的视频。

    输入是视频字典列表，每项从 `published_at_raw` 读取原始发布时间。
    只返回目标日期的视频，并新增 ISO 8601 字符串字段 `published_at`。
    """
    if target_day is None:
        target_day = datetime.now(SHANGHAI_TZ).date()

    filtered: list[dict[str, Any]] = []
    for video in videos:
        published_at = parse_publish_time(video.get("published_at_raw"))
        if published_at is None or published_at.date() != target_day:
            continue

        filtered.append({**video, "published_at": published_at.isoformat()})

    return filtered


def _parse_douyin_cookie_header(cookie_header: str) -> list[dict[str, Any]]:
    normalized_header = cookie_header.strip()
    if normalized_header.lower().startswith("cookie:"):
        normalized_header = normalized_header.split(":", 1)[1].strip()

    cookie = SimpleCookie()
    cookie.load(normalized_header)

    parsed_cookies: list[dict[str, Any]] = []
    for morsel in cookie.values():
        parsed_cookies.append(
            {
                "name": morsel.key,
                "value": morsel.value,
                "domain": ".douyin.com",
                "path": "/",
                "secure": True,
            }
        )

    if parsed_cookies:
        return parsed_cookies

    fallback_cookies: list[dict[str, Any]] = []
    for fragment in re.split(r"[;\n]+", normalized_header):
        piece = fragment.strip()
        if not piece or "=" not in piece:
            continue
        name, value = piece.split("=", 1)
        name = name.strip()
        value = value.strip()
        if not name:
            continue
        fallback_cookies.append(
            {
                "name": name,
                "value": value,
                "domain": ".douyin.com",
                "path": "/",
                "secure": True,
            }
        )
    return fallback_cookies


@contextmanager
def _playwright_browser() -> Iterator[Any]:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise RuntimeError("playwright is not installed") from exc

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled"],
        )
        try:
            yield browser
        finally:
            browser.close()


def _new_douyin_context(browser: Any) -> Any:
    context = browser.new_context(
        locale="zh-CN",
        timezone_id="Asia/Shanghai",
        user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/137.0.0.0 Safari/537.36"
        ),
        viewport={"width": 1440, "height": 1200},
    )

    cookie_header = os.getenv("DOUYIN_COOKIE", "").strip()
    if cookie_header:
        cookies = _parse_douyin_cookie_header(cookie_header)
        print(f"[douyin] cookie header detected, parsed cookies: {len(cookies)}")
        if not cookies:
            raise RuntimeError("DOUYIN_COOKIE is set but no valid cookies were parsed")
        context.add_cookies(cookies)
    else:
        print("[douyin] DOUYIN_COOKIE is empty")

    return context


def _collect_author_page_debug(page: Any) -> dict[str, Any]:
    return page.evaluate(
        """
        () => {
          const bodyText = document.body ? (document.body.innerText || "") : "";
          const panelCandidates = Array.from(document.querySelectorAll('[role="tabpanel"]'));
          const worksPanel = panelCandidates.find((panel) => {
            const text = (panel.innerText || panel.textContent || "").replace(/\\s+/g, " ").trim();
            if (text.includes("搜索 Ta 的作品")) return true;
            return Boolean(panel.querySelector('input[placeholder*="搜索"], input[placeholder*="作品"]'));
          });
          const panelVideoAnchors = worksPanel
            ? Array.from(worksPanel.querySelectorAll('a[href*="/video/"]')).length
            : 0;
          const docVideoAnchors = Array.from(document.querySelectorAll('a[href*="/video/"]')).length;
          return {
            title: document.title || "",
            has_login_modal: bodyText.includes("登录后免费畅享高清视频"),
            has_service_error: bodyText.includes("服务异常"),
            has_search_box: bodyText.includes("搜索 Ta 的作品"),
            works_panel_found: Boolean(worksPanel),
            works_panel_video_anchors: panelVideoAnchors,
            document_video_anchors: docVideoAnchors,
          };
        }
        """
    )


def _extract_video_cards_from_dom(page: Any) -> list[dict[str, str]]:
    cards = page.evaluate(
        """
        () => {
          const collectAnchorItems = (root) => {
            const anchors = Array.from(root.querySelectorAll('a[href*="/video/"]'));
            const seen = new Set();
            const items = [];

            for (const anchor of anchors) {
              const href = anchor.getAttribute("href") || anchor.href || "";
              const match = href.match(/\\/video\\/(\\d+)/);
              if (!match) continue;

              const videoId = match[1];
              if (seen.has(videoId)) continue;
              seen.add(videoId);

              const text = (anchor.textContent || "").replace(/\\s+/g, " ").trim();
              items.push({
                video_id: videoId,
                video_url: `https://www.douyin.com/video/${videoId}`,
                title: text,
                raw_href: href,
              });
            }

            return items;
          };

          const panelCandidates = Array.from(document.querySelectorAll('[role="tabpanel"]'));
          const worksPanel = panelCandidates.find((panel) => {
            const text = (panel.innerText || panel.textContent || "").replace(/\\s+/g, " ").trim();
            if (text.includes("搜索 Ta 的作品")) return true;
            const searchInput = panel.querySelector('input[placeholder*="搜索"], input[placeholder*="作品"]');
            return Boolean(searchInput);
          });

          const root = worksPanel || document;
          const anchors = collectAnchorItems(root);
          if (anchors.length > 0) {
            return anchors;
          }

          const allAnchors = collectAnchorItems(document);
          if (allAnchors.length > 0) {
            return allAnchors;
          }

          return [];
        }
        """
    )

    if not isinstance(cards, list):
        raise RuntimeError("unexpected author page payload")

    return _filter_author_video_cards(cards, author_name=_extract_author_name(page))


def _extract_author_name(page: Any) -> str:
    author_name = page.evaluate(
        """
        () => {
          const candidates = [
            document.querySelector('h1'),
            document.querySelector('[data-e2e="user-title"]'),
            document.querySelector('[data-e2e="user-name"]'),
            ...Array.from(document.querySelectorAll('[role="heading"]')),
          ];

          for (const candidate of candidates) {
            if (!candidate) continue;
            const text = (candidate.textContent || "").replace(/\\s+/g, " ").trim();
            if (text && !text.includes("抖音")) {
              return text;
            }
          }

          return "";
        }
        """
    )
    if not isinstance(author_name, str):
        return ""
    return author_name.strip()


def _filter_author_video_cards(cards: list[dict[str, Any]], author_name: str = "") -> list[dict[str, str]]:
    normalized_author_name = re.sub(r"\s+", "", author_name)
    normalized_cards: list[dict[str, str]] = []
    author_named_cards: list[dict[str, str]] = []

    for card in cards:
        if not isinstance(card, dict):
            continue

        video_id = str(card.get("video_id", "")).strip()
        video_url = str(card.get("video_url", "")).strip()
        title = str(card.get("title", "")).strip()
        raw_href = str(card.get("raw_href", "")).strip().lower()
        if not video_id or not video_url:
            continue
        if "source=baiduspider" in raw_href:
            continue
        normalized_card = {
            "video_id": video_id,
            "video_url": video_url,
            "title": title,
        }
        normalized_cards.append(normalized_card)
        if normalized_author_name:
            normalized_title = re.sub(r"\s+", "", title)
            if normalized_author_name in normalized_title:
                author_named_cards.append(normalized_card)

    if author_named_cards:
        return author_named_cards

    return normalized_cards


def _looks_like_challenge_page(page: Any) -> bool:
    page_html = page.content()
    return "__ac_signature" in page_html or "window.byted_acrawler" in page_html


def _try_recover_author_page(page: Any) -> bool:
    result = page.evaluate(
        """
        () => {
          const bodyText = document.body ? (document.body.innerText || "") : "";
          const clickByText = (candidates) => {
            const elements = Array.from(document.querySelectorAll("button, div, span, a"));
            for (const candidate of candidates) {
              const element = elements.find((node) => {
                const text = (node.innerText || node.textContent || "").replace(/\\s+/g, " ").trim();
                return text === candidate || text.includes(candidate);
              });
              if (element) {
                element.click();
                return candidate;
              }
            }
            return "";
          };

          if (bodyText.includes("服务异常")) {
            return clickByText(["刷新", "重试", "重新加载", "重新刷新拉取数据"]);
          }

          if (bodyText.includes("登录") || bodyText.includes("注册")) {
            return clickByText(["暂不登录", "以后再说", "稍后再说", "关闭", "取消"]);
          }

          return "";
        }
        """
    )
    if isinstance(result, str) and result:
        page.wait_for_timeout(1200)
        return True
    return False


def _extract_author_video_cards(page: Any, author_url: str) -> list[dict[str, str]]:
    normalized_url = normalize_author_url(author_url)

    for _attempt in range(3):
        page.goto(normalized_url, wait_until="domcontentloaded", timeout=60000)

        stable_rounds = 0
        previous_count = -1
        for _poll in range(12):
            page.wait_for_timeout(1500)
            cards = _extract_video_cards_from_dom(page)
            if cards:
                current_count = len(cards)
                if current_count == previous_count:
                    stable_rounds += 1
                else:
                    stable_rounds = 0
                    previous_count = current_count
                if stable_rounds >= 2:
                    return cards
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                continue
            if _try_recover_author_page(page):
                continue
            if not _looks_like_challenge_page(page):
                break

        debug_state = _collect_author_page_debug(page)
        print(f"[douyin] author page debug: {debug_state}")
        page.reload(wait_until="domcontentloaded", timeout=60000)

    return []


def get_author_video_urls(author_url: str) -> list[str]:
    """抓取作者主页作品 URL，按页面顺序返回。"""
    with _playwright_browser() as browser:
        context = _new_douyin_context(browser)
        author_page = context.new_page()
        try:
            cards = _extract_author_video_cards(author_page, author_url)
            if not cards:
                raise RuntimeError(f"no douyin videos found for {normalize_author_url(author_url)}")
            return [card["video_url"] for card in cards]
        finally:
            context.close()


def _extract_video_publish_time(page: Any, video_url: str) -> datetime | None:
    page.goto(video_url, wait_until="domcontentloaded", timeout=30000)
    page.wait_for_timeout(1500)

    page_text = page.locator("body").inner_text(timeout=10000)
    published_at = parse_publish_time_text(page_text)
    if published_at is not None:
        return published_at

    snapshot_text = page.locator("html").text_content(timeout=10000) or ""
    return parse_publish_time_text(snapshot_text)


def _build_video_record(card: dict[str, str], published_at: datetime | None) -> dict[str, Any]:
    published_at_raw: int | None = None
    if published_at is not None:
        published_at_raw = int(published_at.timestamp() * 1000)
    else:
        title_date = extract_title_date(card.get("title", ""))
        if title_date is not None:
            fallback_dt = datetime(
                title_date.year,
                title_date.month,
                title_date.day,
                tzinfo=SHANGHAI_TZ,
            )
            published_at_raw = int(fallback_dt.timestamp() * 1000)

    return {
        "video_id": card["video_id"],
        "video_url": card["video_url"],
        "title": card.get("title", ""),
        "published_at_raw": published_at_raw,
    }


def get_author_videos(
    author_url: str,
    max_detail_pages: int = 12,
    consecutive_old_limit: int = 3,
    target_day: date | None = None,
) -> list[dict[str, Any]]:
    """用浏览器抓取作者视频列表，并补充发布时间。"""
    if target_day is None:
        target_day = datetime.now(SHANGHAI_TZ).date()

    with _playwright_browser() as browser:
        context = _new_douyin_context(browser)
        author_page = context.new_page()
        detail_page = context.new_page()
        try:
            cards = _extract_author_video_cards(author_page, author_url)
            if not cards:
                raise RuntimeError(f"no douyin videos found for {normalize_author_url(author_url)}")

            videos: list[dict[str, Any]] = []
            consecutive_old_count = 0

            for card in cards:
                published_at = _extract_video_publish_time(detail_page, card["video_url"])
                video_record = _build_video_record(card, published_at)
                videos.append(video_record)

                record_day = None
                if published_at is not None:
                    record_day = published_at.date()
                else:
                    record_day = extract_title_date(card.get("title", ""))

                if record_day is not None and record_day < target_day:
                    consecutive_old_count += 1
                else:
                    consecutive_old_count = 0
                if len(videos) >= max_detail_pages and consecutive_old_count >= consecutive_old_limit:
                    break

            return videos
        finally:
            context.close()
