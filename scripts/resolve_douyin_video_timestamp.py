#!/usr/bin/env python3
"""解析抖音视频发布时间并输出适合文件命名的时间戳。"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.douyin_author_feed import SHANGHAI_TZ, get_video_publish_time


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="解析抖音视频发布时间")
    parser.add_argument("--video-url", required=True, help="抖音视频链接")
    parser.add_argument(
        "--format",
        choices=("filename", "iso"),
        default="filename",
        help="输出格式：filename 为 YYYYMMDD-HHMM，iso 为 ISO 8601",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    published_at = get_video_publish_time(args.video_url)
    if published_at is None:
        return 1
    published_at = published_at.astimezone(SHANGHAI_TZ)
    if args.format == "iso":
        print(published_at.isoformat())
    else:
        print(published_at.strftime("%Y%m%d-%H%M"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
