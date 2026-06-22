import unittest
from datetime import date, datetime
from unittest.mock import patch
from zoneinfo import ZoneInfo

from scripts.douyin_author_feed import (
    _build_video_record,
    _filter_author_video_cards,
    extract_author_id,
    extract_title_date,
    filter_today_videos,
    get_author_video_urls,
    get_author_videos,
    normalize_author_url,
    parse_publish_time,
    parse_publish_time_text,
)


class FakePage:
    def __init__(self, author_cards=None, page_text_by_url=None, html_by_url=None, recovery_cards=None):
        self.author_cards = author_cards or []
        self.page_text_by_url = page_text_by_url or {}
        self.html_by_url = html_by_url or {}
        self.recovery_cards = recovery_cards or []
        self.current_url = ""

    def goto(self, url: str, wait_until: str, timeout: int) -> None:
        self.current_url = url

    def wait_for_timeout(self, _timeout_ms: int) -> None:
        return None

    def reload(self, wait_until: str, timeout: int) -> None:
        return None

    def evaluate(self, _script: str):
        if "clickByText" in _script:
            self.author_cards = self.recovery_cards
            self.html_by_url[self.current_url] = ""
            return "recovered"
        if "window.scrollTo" in _script:
            return None
        return self.author_cards

    def locator(self, _selector: str):
        return FakeLocator(self.page_text_by_url.get(self.current_url, ""))

    def content(self) -> str:
        return self.html_by_url.get(self.current_url, "")


class FakeLocator:
    def __init__(self, text: str):
        self.text = text

    def inner_text(self, timeout: int) -> str:
        return self.text

    def text_content(self, timeout: int) -> str:
        return self.text


class FakeContext:
    def __init__(self, author_cards=None, page_text_by_url=None, html_by_url=None, recovery_cards=None):
        self.author_cards = author_cards or []
        self.page_text_by_url = page_text_by_url or {}
        self.html_by_url = html_by_url or {}
        self.recovery_cards = recovery_cards or []
        self.page_index = 0

    def new_page(self):
        self.page_index += 1
        if self.page_index == 1:
            return FakePage(
                author_cards=self.author_cards,
                page_text_by_url=self.page_text_by_url,
                html_by_url=self.html_by_url,
                recovery_cards=self.recovery_cards,
            )
        return FakePage(
            page_text_by_url=self.page_text_by_url,
            html_by_url=self.html_by_url,
            recovery_cards=self.recovery_cards,
        )

    def close(self) -> None:
        return None


class FakeBrowser:
    def __init__(self, author_cards=None, page_text_by_url=None, html_by_url=None, recovery_cards=None):
        self.author_cards = author_cards or []
        self.page_text_by_url = page_text_by_url or {}
        self.html_by_url = html_by_url or {}
        self.recovery_cards = recovery_cards or {}

    def new_context(self, **_kwargs):
        return FakeContext(
            author_cards=self.author_cards,
            page_text_by_url=self.page_text_by_url,
            html_by_url=self.html_by_url,
            recovery_cards=self.recovery_cards,
        )

    def close(self) -> None:
        return None


class FakeBrowserContextManager:
    def __init__(self, browser: FakeBrowser):
        self.browser = browser

    def __enter__(self):
        return self.browser

    def __exit__(self, exc_type, exc, tb):
        return False


class DouyinAuthorFeedTests(unittest.TestCase):
    def test_filter_author_video_cards_keeps_only_current_author_videos(self):
        cards = [
            {
                "video_id": "7652253434476875054",
                "video_url": "https://www.douyin.com/video/7652253434476875054",
                "title": "牛二研报纪要：金融、交运、汽车、铀行业更新 20260617",
                "raw_href": "/video/7652253434476875054",
            },
            {
                "video_id": "7602874137111006500",
                "video_url": "https://www.douyin.com/video/7602874137111006500",
                "title": "",
                "raw_href": "https://www.douyin.com/video/7602874137111006500?source=Baiduspider",
            },
            {
                "video_id": "7181443957048479034",
                "video_url": "https://www.douyin.com/video/7181443957048479034",
                "title": "别的账号视频标题",
                "raw_href": "/video/7181443957048479034",
            },
        ]

        filtered = _filter_author_video_cards(cards, author_name="牛二研报纪要")

        self.assertEqual(
            filtered,
            [
                {
                    "video_id": "7652253434476875054",
                    "video_url": "https://www.douyin.com/video/7652253434476875054",
                    "title": "牛二研报纪要：金融、交运、汽车、铀行业更新 20260617",
                }
            ],
        )

    def test_extract_author_id_reads_user_path_segment(self):
        author_id = extract_author_id(
            "https://www.douyin.com/user/MS4wLjABAAAAWGs2N4r_PbCH8uXi07DlK8G5T-dz2EA_bnoWb00V5BaR_-LdVLMDxIfqFbU8qbwX?from_tab_name=main"
        )

        self.assertEqual(
            author_id,
            "MS4wLjABAAAAWGs2N4r_PbCH8uXi07DlK8G5T-dz2EA_bnoWb00V5BaR_-LdVLMDxIfqFbU8qbwX",
        )

    def test_normalize_author_url_strips_query(self):
        normalized = normalize_author_url(
            "https://www.douyin.com/user/MS4wLjABAAAAWGs2N4r_PbCH8uXi07DlK8G5T-dz2EA_bnoWb00V5BaR_-LdVLMDxIfqFbU8qbwX?from_tab_name=main"
        )

        self.assertEqual(
            normalized,
            "https://www.douyin.com/user/MS4wLjABAAAAWGs2N4r_PbCH8uXi07DlK8G5T-dz2EA_bnoWb00V5BaR_-LdVLMDxIfqFbU8qbwX",
        )

    def test_parse_publish_time_text_reads_visible_publish_label(self):
        published_at = parse_publish_time_text("点赞 12 发布时间：2026-06-17 14:51 全部评论")

        self.assertEqual(
            published_at,
            datetime(2026, 6, 17, 14, 51, tzinfo=ZoneInfo("Asia/Shanghai")),
        )

    def test_extract_title_date_reads_yyyymmdd_suffix(self):
        self.assertEqual(extract_title_date("行业更新 20260617"), date(2026, 6, 17))
        self.assertIsNone(extract_title_date("行业更新"))

    def test_build_video_record_falls_back_to_title_date(self):
        record = _build_video_record(
            {
                "video_id": "123",
                "video_url": "https://www.douyin.com/video/123",
                "title": "行业更新 20260617",
            },
            published_at=None,
        )

        self.assertEqual(record["video_id"], "123")
        self.assertEqual(
            record["published_at_raw"],
            int(datetime(2026, 6, 17, 0, 0, tzinfo=ZoneInfo("Asia/Shanghai")).timestamp() * 1000),
        )

    @patch("scripts.douyin_author_feed._playwright_browser")
    def test_get_author_videos_reads_author_cards_and_publish_time(self, mock_browser):
        author_cards = [
            {
                "video_id": "100",
                "video_url": "https://www.douyin.com/video/100",
                "title": "行业更新 20260618",
            }
        ]
        page_text_by_url = {
            "https://www.douyin.com/video/100": "发布时间：2026-06-18 09:30",
        }
        mock_browser.return_value = FakeBrowserContextManager(
            FakeBrowser(author_cards=author_cards, page_text_by_url=page_text_by_url)
        )

        videos = get_author_videos("https://www.douyin.com/user/test-author", target_day=date(2026, 6, 18))

        self.assertEqual(
            videos,
            [
                {
                    "video_id": "100",
                    "video_url": "https://www.douyin.com/video/100",
                    "title": "行业更新 20260618",
                    "published_at_raw": int(
                        datetime(2026, 6, 18, 9, 30, tzinfo=ZoneInfo("Asia/Shanghai")).timestamp() * 1000
                    ),
                }
            ],
        )

    @patch("scripts.douyin_author_feed._playwright_browser")
    def test_get_author_videos_falls_back_to_title_date_when_publish_text_missing(self, mock_browser):
        author_cards = [
            {
                "video_id": "100",
                "video_url": "https://www.douyin.com/video/100",
                "title": "行业更新 20260618",
            }
        ]
        mock_browser.return_value = FakeBrowserContextManager(FakeBrowser(author_cards=author_cards))

        videos = get_author_videos("https://www.douyin.com/user/test-author", target_day=date(2026, 6, 18))

        self.assertEqual(
            videos[0]["published_at_raw"],
            int(datetime(2026, 6, 18, 0, 0, tzinfo=ZoneInfo("Asia/Shanghai")).timestamp() * 1000),
        )

    @patch("scripts.douyin_author_feed._playwright_browser")
    def test_get_author_videos_tolerates_challenge_page_html(self, mock_browser):
        author_cards = [
            {
                "video_id": "100",
                "video_url": "https://www.douyin.com/video/100",
                "title": "行业更新 20260618",
            }
        ]
        html_by_url = {
            "https://www.douyin.com/user/test-author": "<script>window.byted_acrawler={};var __ac_signature='x';</script>",
        }
        page_text_by_url = {
            "https://www.douyin.com/video/100": "发布时间：2026-06-18 09:30",
        }
        mock_browser.return_value = FakeBrowserContextManager(
            FakeBrowser(author_cards=author_cards, page_text_by_url=page_text_by_url, html_by_url=html_by_url)
        )

        videos = get_author_videos("https://www.douyin.com/user/test-author", target_day=date(2026, 6, 18))

        self.assertEqual(videos[0]["video_id"], "100")

    @patch("scripts.douyin_author_feed._playwright_browser")
    def test_get_author_video_urls_recovers_from_service_error_page(self, mock_browser):
        html_by_url = {
            "https://www.douyin.com/user/test-author": "服务异常，重新刷新拉取数据 刷新",
        }
        recovery_cards = [
            {
                "video_id": "100",
                "video_url": "https://www.douyin.com/video/100",
                "title": "行业更新 20260618",
            }
        ]
        mock_browser.return_value = FakeBrowserContextManager(
            FakeBrowser(html_by_url=html_by_url, recovery_cards=recovery_cards)
        )

        video_urls = get_author_video_urls("https://www.douyin.com/user/test-author")

        self.assertEqual(video_urls, ["https://www.douyin.com/video/100"])

    @patch("scripts.douyin_author_feed._playwright_browser")
    def test_get_author_video_urls_returns_urls_in_author_page_order(self, mock_browser):
        author_cards = [
            {
                "video_id": "newest",
                "video_url": "https://www.douyin.com/video/newest",
                "title": "行业更新 20260618",
            },
            {
                "video_id": "older",
                "video_url": "https://www.douyin.com/video/older",
                "title": "行业更新 20260617",
            },
        ]
        mock_browser.return_value = FakeBrowserContextManager(FakeBrowser(author_cards=author_cards))

        video_urls = get_author_video_urls("https://www.douyin.com/user/test-author")

        self.assertEqual(
            video_urls,
            [
                "https://www.douyin.com/video/newest",
                "https://www.douyin.com/video/older",
            ],
        )

    @patch("scripts.douyin_author_feed._playwright_browser")
    def test_get_author_videos_stops_after_multiple_older_videos(self, mock_browser):
        author_cards = [
            {
                "video_id": "today",
                "video_url": "https://www.douyin.com/video/today",
                "title": "行业更新 20260618",
            },
            {
                "video_id": "old-1",
                "video_url": "https://www.douyin.com/video/old-1",
                "title": "行业更新 20260617",
            },
            {
                "video_id": "old-2",
                "video_url": "https://www.douyin.com/video/old-2",
                "title": "行业更新 20260616",
            },
            {
                "video_id": "old-3",
                "video_url": "https://www.douyin.com/video/old-3",
                "title": "行业更新 20260615",
            },
            {
                "video_id": "old-4",
                "video_url": "https://www.douyin.com/video/old-4",
                "title": "行业更新 20260614",
            },
        ]
        page_text_by_url = {
            "https://www.douyin.com/video/today": "发布时间：2026-06-18 09:30",
            "https://www.douyin.com/video/old-1": "发布时间：2026-06-17 09:30",
            "https://www.douyin.com/video/old-2": "发布时间：2026-06-16 09:30",
            "https://www.douyin.com/video/old-3": "发布时间：2026-06-15 09:30",
            "https://www.douyin.com/video/old-4": "发布时间：2026-06-14 09:30",
        }
        mock_browser.return_value = FakeBrowserContextManager(
            FakeBrowser(author_cards=author_cards, page_text_by_url=page_text_by_url)
        )

        videos = get_author_videos(
            "https://www.douyin.com/user/test-author",
            max_detail_pages=1,
            consecutive_old_limit=3,
            target_day=date(2026, 6, 18),
        )

        self.assertEqual([video["video_id"] for video in videos], ["today", "old-1", "old-2", "old-3"])

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
