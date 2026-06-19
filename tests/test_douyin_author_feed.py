import unittest
from datetime import date, datetime
from unittest.mock import Mock, patch
import subprocess
from zoneinfo import ZoneInfo

from scripts.douyin_author_feed import (
    build_author_candidate_urls,
    extract_author_id,
    extract_video_entries,
    filter_today_videos,
    get_author_videos,
    parse_publish_time,
)


class DouyinAuthorFeedTests(unittest.TestCase):
    def test_extract_author_id_reads_user_path_segment(self):
        author_id = extract_author_id(
            "https://www.douyin.com/user/MS4wLjABAAAAWGs2N4r_PbCH8uXi07DlK8G5T-dz2EA_bnoWb00V5BaR_-LdVLMDxIfqFbU8qbwX?from_tab_name=main"
        )

        self.assertEqual(
            author_id,
            "MS4wLjABAAAAWGs2N4r_PbCH8uXi07DlK8G5T-dz2EA_bnoWb00V5BaR_-LdVLMDxIfqFbU8qbwX",
        )

    def test_build_author_candidate_urls_includes_share_user_fallback(self):
        author_id = "MS4wLjABAAAAWGs2N4r_PbCH8uXi07DlK8G5T-dz2EA_bnoWb00V5BaR_-LdVLMDxIfqFbU8qbwX"

        candidates = build_author_candidate_urls(f"https://www.douyin.com/user/{author_id}")

        self.assertEqual(
            candidates,
            [
                f"https://www.douyin.com/user/{author_id}",
                f"https://www.douyin.com/user/{author_id}?showTab=post",
                f"https://www.iesdouyin.com/share/user/{author_id}",
            ],
        )

    def test_extract_video_entries_normalizes_flat_playlist_entries(self):
        payload = {
            "entries": [
                {
                    "id": "100",
                    "url": "https://www.douyin.com/video/100",
                    "title": "video 100",
                    "timestamp": 1781746200,
                },
                {
                    "id": "200",
                    "webpage_url": "https://www.douyin.com/video/200",
                    "title": "video 200",
                    "create_time": 1781746300,
                },
                {
                    "id": "300",
                    "title": "video 300",
                    "timestamp": 1781746400,
                },
            ]
        }

        videos = extract_video_entries(payload)

        self.assertEqual(
            videos,
            [
                {
                    "video_id": "100",
                    "video_url": "https://www.douyin.com/video/100",
                    "title": "video 100",
                    "published_at_raw": 1781746200,
                },
                {
                    "video_id": "200",
                    "video_url": "https://www.douyin.com/video/200",
                    "title": "video 200",
                    "published_at_raw": 1781746300,
                },
                {
                    "video_id": "300",
                    "video_url": "https://www.douyin.com/video/300",
                    "title": "video 300",
                    "published_at_raw": 1781746400,
                },
            ],
        )

    def test_extract_video_entries_prefers_webpage_url_over_url(self):
        payload = {
            "entries": [
                {
                    "id": "500",
                    "url": "video/500",
                    "webpage_url": "https://www.douyin.com/video/500",
                    "title": "video 500",
                    "timestamp": 1781746500,
                }
            ]
        }

        videos = extract_video_entries(payload)

        self.assertEqual(
            videos,
            [
                {
                    "video_id": "500",
                    "video_url": "https://www.douyin.com/video/500",
                    "title": "video 500",
                    "published_at_raw": 1781746500,
                }
            ],
        )

    @patch("scripts.douyin_author_feed.subprocess.run")
    def test_get_author_videos_reads_flat_playlist_json(self, mock_run: Mock):
        mock_run.return_value = Mock(
            returncode=0,
            stdout=(
                '{"entries":[{"id":"100","title":"video 100","webpage_url":"https://www.douyin.com/video/100",'
                '"timestamp":1781746200}]}'
            ),
            stderr="",
        )

        videos = get_author_videos(
            "https://www.douyin.com/user/MS4wLjABAAAAWGs2N4r_PbCH8uXi07DlK8G5T-dz2EA_bnoWb00V5BaR_-LdVLMDxIfqFbU8qbwX"
        )

        self.assertEqual(
            videos,
            [
                {
                    "video_id": "100",
                    "video_url": "https://www.douyin.com/video/100",
                    "title": "video 100",
                    "published_at_raw": 1781746200,
                }
            ],
        )

    @patch("scripts.douyin_author_feed.subprocess.run")
    def test_get_author_videos_falls_back_to_share_user_url(self, mock_run: Mock):
        mock_run.side_effect = [
            Mock(returncode=1, stdout="", stderr="Unsupported URL"),
            Mock(returncode=1, stdout="", stderr="Unsupported URL"),
            Mock(
                returncode=0,
                stdout=(
                    '{"entries":[{"id":"100","title":"video 100","webpage_url":"https://www.douyin.com/video/100",'
                    '"timestamp":1781746200}]}'
                ),
                stderr="",
            ),
        ]

        author_url = (
            "https://www.douyin.com/user/"
            "MS4wLjABAAAAWGs2N4r_PbCH8uXi07DlK8G5T-dz2EA_bnoWb00V5BaR_-LdVLMDxIfqFbU8qbwX"
        )
        videos = get_author_videos(author_url)

        self.assertEqual(videos[0]["video_id"], "100")
        called_urls = [call.args[0][-1] for call in mock_run.call_args_list]
        self.assertEqual(
            called_urls,
            [
                author_url,
                f"{author_url}?showTab=post",
                "https://www.iesdouyin.com/share/user/MS4wLjABAAAAWGs2N4r_PbCH8uXi07DlK8G5T-dz2EA_bnoWb00V5BaR_-LdVLMDxIfqFbU8qbwX",
            ],
        )

    @patch("scripts.douyin_author_feed.subprocess.run")
    def test_get_author_videos_raises_clear_error_when_command_fails(self, mock_run: Mock):
        mock_run.return_value = Mock(returncode=1, stdout="", stderr="site blocked")

        with self.assertRaisesRegex(RuntimeError, "yt-dlp .* site blocked"):
            get_author_videos(
                "https://www.douyin.com/user/MS4wLjABAAAAWGs2N4r_PbCH8uXi07DlK8G5T-dz2EA_bnoWb00V5BaR_-LdVLMDxIfqFbU8qbwX"
            )

    @patch("scripts.douyin_author_feed.subprocess.run")
    def test_get_author_videos_raises_clear_error_when_yt_dlp_missing(self, mock_run: Mock):
        mock_run.side_effect = FileNotFoundError()

        with self.assertRaisesRegex(RuntimeError, "yt-dlp not found"):
            get_author_videos(
                "https://www.douyin.com/user/MS4wLjABAAAAWGs2N4r_PbCH8uXi07DlK8G5T-dz2EA_bnoWb00V5BaR_-LdVLMDxIfqFbU8qbwX"
            )

    @patch("scripts.douyin_author_feed.subprocess.run")
    def test_get_author_videos_raises_clear_error_when_yt_dlp_times_out(self, mock_run: Mock):
        mock_run.side_effect = subprocess.TimeoutExpired(cmd=["yt-dlp"], timeout=60)

        with self.assertRaisesRegex(RuntimeError, "yt-dlp timed out"):
            get_author_videos(
                "https://www.douyin.com/user/MS4wLjABAAAAWGs2N4r_PbCH8uXi07DlK8G5T-dz2EA_bnoWb00V5BaR_-LdVLMDxIfqFbU8qbwX"
            )

    def test_parse_publish_time_parses_epoch_milliseconds(self):
        published_at = parse_publish_time(1718674200000)

        self.assertEqual(
            published_at,
            datetime(2024, 6, 18, 9, 30, tzinfo=ZoneInfo("Asia/Shanghai")),
        )

    def test_parse_publish_time_supports_seconds_and_numeric_strings(self):
        self.assertEqual(
            parse_publish_time(1718674200),
            datetime(2024, 6, 18, 9, 30, tzinfo=ZoneInfo("Asia/Shanghai")),
        )
        self.assertEqual(
            parse_publish_time("1718674200000"),
            datetime(2024, 6, 18, 9, 30, tzinfo=ZoneInfo("Asia/Shanghai")),
        )

    def test_parse_publish_time_returns_none_for_invalid_values(self):
        self.assertIsNone(parse_publish_time("not-a-timestamp"))
        self.assertIsNone(parse_publish_time(""))
        self.assertIsNone(parse_publish_time(12.34))
        self.assertIsNone(parse_publish_time(True))
        self.assertIsNone(parse_publish_time(False))
        self.assertIsNone(parse_publish_time(None))

    def test_filter_today_videos_keeps_only_today_and_sets_published_at(self):
        target_day = date(2026, 6, 18)
        videos = [
            {
                "aweme_id": "today",
                "published_at_raw": int(
                    datetime(2026, 6, 18, 9, 30, tzinfo=ZoneInfo("Asia/Shanghai")).timestamp() * 1000
                ),
            },
            {
                "aweme_id": "yesterday",
                "published_at_raw": int(
                    datetime(2026, 6, 17, 21, 0, tzinfo=ZoneInfo("Asia/Shanghai")).timestamp() * 1000
                ),
            },
            {"aweme_id": "missing", "published_at_raw": None},
        ]

        filtered = filter_today_videos(videos, target_day=target_day)

        self.assertEqual(
            filtered,
            [
                {
                    "aweme_id": "today",
                    "published_at_raw": int(
                        datetime(2026, 6, 18, 9, 30, tzinfo=ZoneInfo("Asia/Shanghai")).timestamp() * 1000
                    ),
                    "published_at": "2026-06-18T09:30:00+08:00",
                }
            ],
        )


if __name__ == "__main__":
    unittest.main()
