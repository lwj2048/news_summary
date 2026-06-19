#!/usr/bin/env python3
"""抖音作者视频列表的时间解析与按天过滤。"""

from __future__ import annotations

import json
import subprocess
from datetime import date, datetime
from typing import Any
from urllib.parse import urlparse
from zoneinfo import ZoneInfo


SHANGHAI_TZ = ZoneInfo("Asia/Shanghai")


def _looks_like_http_url(value: Any) -> bool:
    if value is None:
        return False
    normalized = str(value).strip().lower()
    return normalized.startswith("http://") or normalized.startswith("https://")


def extract_author_id(author_url: str) -> str:
    """从抖音作者 URL 提取作者 ID。"""
    parsed = urlparse(author_url)
    path_segments = [segment for segment in parsed.path.split("/") if segment]
    if len(path_segments) < 2 or path_segments[0] != "user":
        raise ValueError(f"invalid douyin author url: {author_url}")
    return path_segments[1]


def build_author_candidate_urls(author_url: str) -> list[str]:
    """为作者页抓取生成一组候选 URL。"""
    author_id = extract_author_id(author_url)
    candidates = [
        author_url,
        f"https://www.douyin.com/user/{author_id}",
        f"https://www.douyin.com/user/{author_id}?showTab=post",
        f"https://www.iesdouyin.com/share/user/{author_id}",
    ]

    unique_candidates: list[str] = []
    for candidate in candidates:
        normalized = candidate.strip()
        if normalized and normalized not in unique_candidates:
            unique_candidates.append(normalized)
    return unique_candidates


def extract_video_entries(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """把 yt-dlp 平铺列表 payload 映射为统一视频结构。"""
    videos: list[dict[str, Any]] = []
    for entry in payload.get("entries", []):
        if not isinstance(entry, dict):
            continue

        raw_video_id = entry.get("id")
        if raw_video_id is None:
            continue

        video_id = str(raw_video_id).strip()
        if not video_id:
            continue

        raw_webpage_url = entry.get("webpage_url")
        raw_video_url = entry.get("url")
        if _looks_like_http_url(raw_webpage_url):
            video_url = str(raw_webpage_url).strip()
        elif _looks_like_http_url(raw_video_url):
            video_url = str(raw_video_url).strip()
        else:
            video_url = f"https://www.douyin.com/video/{video_id}"

        title = entry.get("title")
        published_at_raw = entry.get("timestamp")
        if published_at_raw is None:
            published_at_raw = entry.get("create_time")

        videos.append(
            {
                "video_id": video_id,
                "video_url": video_url,
                "title": "" if title is None else str(title),
                "published_at_raw": published_at_raw,
            }
        )

    return videos


def get_author_videos(
    author_url: str,
    yt_dlp_bin: str = "yt-dlp",
    timeout: int = 60,
) -> list[dict[str, Any]]:
    """用 yt-dlp 抓取作者视频列表。"""
    candidate_urls = build_author_candidate_urls(author_url)
    failures: list[str] = []

    for candidate_url in candidate_urls:
        try:
            result = subprocess.run(
                [yt_dlp_bin, "--flat-playlist", "--dump-single-json", candidate_url],
                capture_output=True,
                check=False,
                text=True,
                timeout=timeout,
            )
        except FileNotFoundError as exc:
            raise RuntimeError(f"yt-dlp not found: {yt_dlp_bin}") from exc
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError(f"yt-dlp timed out after {timeout}s for {candidate_url}") from exc

        if result.returncode != 0:
            stderr = result.stderr.strip() or result.stdout.strip() or f"exit code {result.returncode}"
            failures.append(f"{candidate_url} -> {stderr}")
            continue

        try:
            payload = json.loads(result.stdout)
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"yt-dlp returned invalid JSON for {candidate_url}") from exc

        if not isinstance(payload, dict):
            raise RuntimeError(f"yt-dlp returned unexpected payload type for {candidate_url}")

        return extract_video_entries(payload)

    failure_summary = " | ".join(failures) if failures else "no candidate URL succeeded"
    raise RuntimeError(f"yt-dlp failed for {author_url}: {failure_summary}")


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
