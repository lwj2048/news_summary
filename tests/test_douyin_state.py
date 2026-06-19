import json
import tempfile
import unittest
from pathlib import Path

from scripts.douyin_state import ProcessedVideoStore


class ProcessedVideoStoreTests(unittest.TestCase):
    def test_unknown_video_is_not_processed_when_store_file_missing(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            store_path = Path(tmp_dir) / "processed_videos.json"

            store = ProcessedVideoStore(store_path)

            self.assertFalse(store.is_processed("author-1", "video-1"))

    def test_record_processed_persists_to_json_and_survives_reload(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            store_path = Path(tmp_dir) / "processed_videos.json"
            store = ProcessedVideoStore(store_path)

            store.record_processed(
                author_id="author-1",
                video_id="video-1",
                video_url="https://example.com/video-1",
                published_at="2026-06-18T09:30:00+08:00",
                processed_at="2026-06-18T10:00:00+08:00",
            )

            reloaded_store = ProcessedVideoStore(store_path)

            self.assertTrue(reloaded_store.is_processed("author-1", "video-1"))
            with store_path.open("r", encoding="utf-8") as handle:
                payload = json.load(handle)

            self.assertEqual(payload["version"], 1)
            self.assertIn("author-1", payload["authors"])
            self.assertEqual(
                payload["authors"]["author-1"]["videos"]["video-1"],
                {
                    "video_id": "video-1",
                    "video_url": "https://example.com/video-1",
                    "published_at": "2026-06-18T09:30:00+08:00",
                    "processed_at": "2026-06-18T10:00:00+08:00",
                },
            )

    def test_load_raises_value_error_for_invalid_json(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            store_path = Path(tmp_dir) / "processed_videos.json"
            store_path.write_text("{invalid json", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "Invalid processed video store JSON"):
                ProcessedVideoStore(store_path)

    def test_load_raises_value_error_for_invalid_schema(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            store_path = Path(tmp_dir) / "processed_videos.json"
            store_path.write_text(json.dumps({"version": 2, "authors": []}), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "Invalid processed video store schema"):
                ProcessedVideoStore(store_path)

    def test_load_raises_value_error_for_invalid_nested_schema(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            store_path = Path(tmp_dir) / "processed_videos.json"
            store_path.write_text(
                json.dumps(
                    {
                        "version": 1,
                        "authors": {
                            "author-1": {
                                "videos": {
                                    "video-1": "invalid",
                                }
                            }
                        },
                    }
                ),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "Invalid processed video store schema"):
                ProcessedVideoStore(store_path)

    def test_record_processed_keeps_multiple_authors(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            store_path = Path(tmp_dir) / "processed_videos.json"
            store = ProcessedVideoStore(store_path)

            store.record_processed(
                author_id="author-1",
                video_id="video-1",
                video_url="https://example.com/video-1",
                published_at="2026-06-18T09:30:00+08:00",
                processed_at="2026-06-18T10:00:00+08:00",
            )
            store.record_processed(
                author_id="author-2",
                video_id="video-2",
                video_url="https://example.com/video-2",
                published_at="2026-06-18T11:30:00+08:00",
                processed_at="2026-06-18T12:00:00+08:00",
            )

            reloaded_store = ProcessedVideoStore(store_path)

            self.assertTrue(reloaded_store.is_processed("author-1", "video-1"))
            self.assertTrue(reloaded_store.is_processed("author-2", "video-2"))
            with store_path.open("r", encoding="utf-8") as handle:
                payload = json.load(handle)

            self.assertEqual(set(payload["authors"].keys()), {"author-1", "author-2"})


if __name__ == "__main__":
    unittest.main()
