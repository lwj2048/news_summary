#!/usr/bin/env python3
"""打印抖音作者主页下的全部作品 URL。"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.douyin_author_feed import get_author_video_urls


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="打印抖音作者主页作品 URL")
    parser.add_argument("--author-url", required=True, help="抖音作者主页 URL")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    for video_url in get_author_video_urls(args.author_url):
        print(video_url)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
