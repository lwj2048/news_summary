#!/usr/bin/env python3
"""已处理抖音视频状态存储。"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


class ProcessedVideoStore:
    """基于 JSON 文件的已处理视频状态存储。"""

    def __init__(self, store_path: str | Path):
        self.store_path = Path(store_path)
        self._data = self._load()

    def is_processed(self, author_id: str, video_id: str) -> bool:
        videos = self._data.get("authors", {}).get(author_id, {}).get("videos", {})
        return video_id in videos

    def record_processed(
        self,
        author_id: str,
        video_id: str,
        video_url: str,
        published_at: str,
        processed_at: str,
    ) -> None:
        authors = self._data.setdefault("authors", {})
        author_entry = authors.setdefault(author_id, {"videos": {}})
        videos = author_entry.setdefault("videos", {})
        videos[video_id] = {
            "video_id": video_id,
            "video_url": video_url,
            "published_at": published_at,
            "processed_at": processed_at,
        }
        self._save()

    def _load(self) -> dict[str, Any]:
        if not self.store_path.exists():
            return self._empty_payload()

        try:
            with self.store_path.open("r", encoding="utf-8") as handle:
                payload = json.load(handle)
        except json.JSONDecodeError as exc:
            raise ValueError("Invalid processed video store JSON") from exc

        self._validate_payload(payload)
        return payload

    def _save(self) -> None:
        self.store_path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = self.store_path.with_name(f"{self.store_path.name}.tmp")
        with temp_path.open("w", encoding="utf-8") as handle:
            json.dump(self._data, handle, ensure_ascii=False, indent=2)
        os.replace(temp_path, self.store_path)

    @staticmethod
    def _empty_payload() -> dict[str, Any]:
        return {"version": 1, "authors": {}}

    @staticmethod
    def _validate_payload(payload: Any) -> None:
        if not isinstance(payload, dict):
            raise ValueError("Invalid processed video store schema: top-level payload must be an object")
        if payload.get("version") != 1:
            raise ValueError("Invalid processed video store schema: version must be 1")
        authors = payload.get("authors")
        if not isinstance(authors, dict):
            raise ValueError("Invalid processed video store schema: authors must be an object")
        for author_id, author_entry in authors.items():
            if not isinstance(author_entry, dict):
                raise ValueError(
                    f"Invalid processed video store schema: author entry for {author_id!r} must be an object"
                )
            videos = author_entry.get("videos")
            if not isinstance(videos, dict):
                raise ValueError(
                    f"Invalid processed video store schema: videos for {author_id!r} must be an object"
                )
            for video_id, video_entry in videos.items():
                if not isinstance(video_entry, dict):
                    raise ValueError(
                        f"Invalid processed video store schema: video entry for {video_id!r} must be an object"
                    )
