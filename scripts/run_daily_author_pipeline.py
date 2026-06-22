#!/usr/bin/env python3
"""抖音作者日批处理入口。"""

from __future__ import annotations

import argparse
import inspect
import subprocess
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Any, Callable

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts import douyin_author_feed
from scripts.douyin_author_feed import SHANGHAI_TZ, filter_today_videos
from scripts.douyin_state import ProcessedVideoStore


DEFAULT_AUTHOR_URL = (
    "https://www.douyin.com/user/"
    "MS4wLjABAAAAWGs2N4r_PbCH8uXi07DlK8G5T-dz2EA_bnoWb00V5BaR_-LdVLMDxIfqFbU8qbwX"
)
DEFAULT_AUTHOR_ID = "MS4wLjABAAAAWGs2N4r_PbCH8uXi07DlK8G5T-dz2EA_bnoWb00V5BaR_-LdVLMDxIfqFbU8qbwX"
DEFAULT_STATE_FILE = Path("data/processed_douyin_videos.json")

VideoFetcher = Callable[[str], list[dict[str, Any]]]
SingleVideoRunner = Callable[..., int]


def _is_non_empty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _parse_published_at_iso(value: str) -> datetime | None:
    if not _is_non_empty_string(value):
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=SHANGHAI_TZ)
    return parsed.astimezone(SHANGHAI_TZ)


def validate_video_record(video: dict[str, Any]) -> tuple[str, str, str] | None:
    """校验批处理所需的视频字段契约。

    合法记录必须显式包含：
    - `video_id`: 非空字符串
    - `video_url`: 非空字符串
    - `published_at`: 非空字符串
    """
    video_id = video.get("video_id")
    video_url = video.get("video_url")
    published_at = video.get("published_at")
    if not _is_non_empty_string(video_id):
        return None
    if not _is_non_empty_string(video_url):
        return None
    if not _is_non_empty_string(published_at):
        return None
    return video_id, video_url, published_at


def normalize_today_videos(
    videos: list[dict[str, Any]], target_day: date | None
) -> tuple[list[dict[str, Any]], int]:
    """把抓取结果规范化为带 `published_at` 字符串的当天视频记录。

    支持两种输入：
    - 已经带 `published_at` 非空字符串的记录：视为上游已完成时间规范化
    - 仅带 `published_at_raw` 的记录：使用 `filter_today_videos()` 转成当天记录
    """
    if target_day is None:
        target_day = datetime.now(SHANGHAI_TZ).date()

    ready_videos: list[dict[str, Any]] = []
    invalid_count = 0
    for video in videos:
        published_at = video.get("published_at")
        if not _is_non_empty_string(published_at):
            continue
        parsed = _parse_published_at_iso(published_at)
        if parsed is None:
            invalid_count += 1
            continue
        if parsed.date() != target_day:
            continue
        ready_videos.append({**video, "published_at": parsed.isoformat()})

    raw_videos = [video for video in videos if not _is_non_empty_string(video.get("published_at"))]
    normalized_raw_videos = filter_today_videos(raw_videos, target_day=target_day)
    return [*ready_videos, *normalized_raw_videos], invalid_count


def normalize_all_videos(videos: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], int]:
    normalized: list[dict[str, Any]] = []
    invalid_count = 0

    for video in videos:
        published_at = video.get("published_at")
        if _is_non_empty_string(published_at):
            parsed = _parse_published_at_iso(published_at)
            if parsed is None:
                invalid_count += 1
                continue
            normalized.append({**video, "published_at": parsed.isoformat()})
            continue

        published_at_raw = video.get("published_at_raw")
        parsed_raw = douyin_author_feed.parse_publish_time(published_at_raw)
        if parsed_raw is None:
            invalid_count += 1
            continue
        normalized.append({**video, "published_at": parsed_raw.isoformat()})

    return normalized, invalid_count


def _run_single_video_with_timestamp(
    runner: SingleVideoRunner, video_url: str, published_at: str
) -> int:
    parameter_count = len(inspect.signature(runner).parameters)
    if parameter_count >= 2:
        return int(runner(video_url, published_at))
    return int(runner(video_url))


def run_daily_pipeline(
    author_url: str = DEFAULT_AUTHOR_URL,
    author_id: str = DEFAULT_AUTHOR_ID,
    state_file: str | Path = DEFAULT_STATE_FILE,
    target_day: date | None = None,
    process_all_history: bool = False,
    fetch_author_videos: VideoFetcher | None = None,
    run_single_video: SingleVideoRunner | None = None,
) -> int:
    """运行作者当天未处理视频的批处理流程。

    `fetch_author_videos` 返回的视频记录在进入单视频流水线前必须满足
    `validate_video_record()` 的字段契约；不合法记录记为失败，但不会中断整批。
    """
    fetcher = fetch_author_videos or _default_fetch_author_videos
    single_video_runner = run_single_video or _run_single_video_pipeline
    store = ProcessedVideoStore(state_file)

    videos = fetcher(author_url)
    if process_all_history:
        candidate_videos, invalid_count = normalize_all_videos(videos)
    else:
        candidate_videos, invalid_count = normalize_today_videos(videos, target_day=target_day)
    exit_code = 1 if invalid_count > 0 else 0

    for video in candidate_videos:
        validated = validate_video_record(video)
        if validated is None:
            exit_code = 1
            continue

        video_id, video_url, published_at = validated
        if store.is_processed(author_id, video_id):
            continue

        result = _run_single_video_with_timestamp(single_video_runner, video_url, published_at)
        if result != 0:
            exit_code = 1
            continue

        store.record_processed(
            author_id=author_id,
            video_id=video_id,
            video_url=video_url,
            published_at=published_at,
            processed_at=datetime.now(SHANGHAI_TZ).isoformat(),
        )

    return exit_code


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="处理抖音作者当天未处理视频")
    parser.add_argument("--author-url", default=DEFAULT_AUTHOR_URL, help="抖音作者主页 URL")
    parser.add_argument("--author-id", default=DEFAULT_AUTHOR_ID, help="抖音作者唯一 ID")
    parser.add_argument("--state-file", default=str(DEFAULT_STATE_FILE), help="已处理状态文件路径")
    parser.add_argument("--all-history", action="store_true", help="处理全部历史未处理视频")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return run_daily_pipeline(
        author_url=args.author_url,
        author_id=args.author_id,
        state_file=args.state_file,
        process_all_history=args.all_history,
    )


def _default_fetch_author_videos(author_url: str) -> list[dict[str, Any]]:
    fetcher = getattr(douyin_author_feed, "get_author_videos", None)
    if fetcher is None:
        raise NotImplementedError(f"get_author_videos is not implemented for {author_url}")
    return fetcher(author_url)


def _published_at_to_timestamp(published_at: str) -> str:
    parsed = _parse_published_at_iso(published_at)
    if parsed is None:
        raise ValueError(f"invalid published_at: {published_at}")
    return parsed.strftime("%Y%m%d-%H%M")


def _run_single_video_pipeline(video_url: str, published_at: str) -> int:
    script_path = Path(__file__).with_name("run_pipeline.py")
    timestamp = _published_at_to_timestamp(published_at)
    result = subprocess.run(
        [sys.executable, str(script_path), video_url, "--timestamp", timestamp],
        check=False,
    )
    return int(result.returncode)


if __name__ == "__main__":
    raise SystemExit(main())
