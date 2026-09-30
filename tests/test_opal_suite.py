"""
tests/test_opal_suite.py
Comprehensive unit test suite for Opal Universal Media & Streaming Suite in Prime AI:
1. Live IPTV & 24/7 Web Radio Catalog
2. Native Player Launcher & Playback Control Bridge
3. AI Media Copilot & Natural Language Mood Matcher
4. Universal Media Hub & Multi-Source Search
5. Tool Catalog Registration & Dispatch Integration
"""

import json
import os
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from actions.opal_iptv import OpalIPTVCatalog, list_iptv_channels, get_iptv_stream
from actions.opal_player_bridge import OpalPlayerBridge, play_media_stream, control_player
from actions.opal_ai_copilot import OpalMediaCopilot, match_mood_media
from actions.opal_media_hub import OpalMediaHub, search_universal_media, play_universal_media, get_media_playback_history
import tool_definitions


class TestOpalIPTV(unittest.TestCase):
    """Test Suite for Live IPTV and Web Radio Catalog."""

    def setUp(self):
        self.catalog = OpalIPTVCatalog()

    def test_list_channels_and_filter(self):
        # All channels
        all_ch = self.catalog.list_channels()
        self.assertTrue(all_ch["ok"])
        self.assertGreaterEqual(all_ch["count"], 10)

        # Filter by News
        news_ch = self.catalog.list_channels(category="News")
        self.assertTrue(news_ch["ok"])
        self.assertTrue(all(c["category"] == "News" for c in news_ch["channels"]))
        self.assertTrue(any("NDTV" in c["name"] or "BBC" in c["name"] for c in news_ch["channels"]))

        # Filter by Music
        music_ch = self.catalog.list_channels(category="Music")
        self.assertTrue(music_ch["ok"])
        self.assertTrue(any("Lofi" in c["name"] for c in music_ch["channels"]))

    def test_get_channel_by_id(self):
        ch = self.catalog.get_channel("lofi_girl")
        self.assertIsNotNone(ch)
        self.assertEqual(ch["name"], "Lofi Girl (Beats to Relax/Study to)")
        self.assertIn("youtube.com", ch["url"])

        # By partial name
        ch_nasa = self.catalog.get_channel("NASA")
        self.assertIsNotNone(ch_nasa)
        self.assertIn("NASA", ch_nasa["name"])


class TestOpalPlayerBridge(unittest.TestCase):
    """Test Suite for Player Launcher and Playback Controls."""

    def setUp(self):
        self.test_np = Path(__file__).resolve().parent / "tmp_opal_now_playing.json"
        self.bridge = OpalPlayerBridge(state_path=self.test_np)

    def tearDown(self):
        if self.test_np.exists():
            try:
                self.test_np.unlink()
            except Exception:
                pass

    @patch("shutil.which")
    def test_detect_players(self, mock_which):
        mock_which.side_effect = lambda cmd: "/usr/bin/vlc" if "vlc" in cmd else None
        players = self.bridge.detect_players()
        self.assertIn("vlc", players)
        self.assertEqual(players["vlc"], "/usr/bin/vlc")

    @patch("subprocess.Popen")
    @patch.object(OpalPlayerBridge, "detect_players")
    def test_play_stream_vlc(self, mock_detect, mock_popen):
        mock_detect.return_value = {"opal": None, "vlc": "C:\\Program Files\\vlc.exe", "mpv": None}
        mock_proc = MagicMock()
        mock_popen.return_value = mock_proc

        res = self.bridge.play_stream("https://live.stream.m3u8", title="Live News", player_preference="auto")
        self.assertTrue(res["ok"])
        self.assertEqual(res["player_used"], "vlc")
        self.assertEqual(self.bridge.now_playing["state"], "playing")

    @patch("webbrowser.open")
    @patch.object(OpalPlayerBridge, "detect_players")
    def test_play_stream_browser_fallback(self, mock_detect, mock_browser):
        mock_detect.return_value = {"opal": None, "vlc": None, "mpv": None}

        res = self.bridge.play_stream("https://www.youtube.com/watch?v=123", title="Video")
        self.assertTrue(res["ok"])
        self.assertEqual(res["player_used"], "browser_default")
        mock_browser.assert_called_once()

    def test_control_playback(self):
        res = self.bridge.control_playback("pause")
        self.assertTrue(res["ok"])


class TestOpalMediaCopilot(unittest.TestCase):
    """Test Suite for AI Media Copilot & Mood Matcher."""

    def setUp(self):
        self.copilot = OpalMediaCopilot()

    def test_mood_matching_coding(self):
        res = self.copilot.match_media_intent("play some cyberpunk synthwave beats for coding")
        self.assertTrue(res["ok"])
        self.assertEqual(res["type"], "live_stream")
        self.assertEqual(res["matched_channel"]["id"], "synthwave_radio")

    def test_mood_matching_chill(self):
        res = self.copilot.match_media_intent("I need some chill lofi music to study")
        self.assertTrue(res["ok"])
        self.assertEqual(res["type"], "live_stream")
        self.assertEqual(res["matched_channel"]["id"], "lofi_girl")

    def test_movie_recommendations(self):
        res = self.copilot.match_media_intent("recommend movies like interstellar")
        self.assertTrue(res["ok"])
        self.assertEqual(res["type"], "movie_recommendations")
        self.assertEqual(res["target"], "Interstellar")
        self.assertGreaterEqual(len(res["recommendations"]), 2)


class TestOpalMediaHub(unittest.TestCase):
    """Test Suite for Universal Media Hub & Playback Dispatcher."""

    def setUp(self):
        self.test_hist = Path(__file__).resolve().parent / "tmp_opal_hist.json"
        self.hub = OpalMediaHub(history_path=self.test_hist)

    def tearDown(self):
        if self.test_hist.exists():
            try:
                self.test_hist.unlink()
            except Exception:
                pass

    def test_universal_search(self):
        res = self.hub.universal_search("lofi")
        self.assertTrue(res["ok"])
        self.assertIn("iptv_channels", res["results"])
        self.assertIn("local_media", res["results"])
        self.assertIn("youtube_stream_url", res["results"])

    @patch("actions.opal_player_bridge.player_bridge.play_stream")
    def test_play_media_channel(self, mock_play):
        mock_play.return_value = {"ok": True, "player_used": "vlc"}
        res = self.hub.play_media("lofi_girl")
        self.assertTrue(res["ok"])
        self.assertEqual(res["media_type"], "iptv_channel")
        self.assertEqual(len(self.hub.history), 1)

    def test_history_retrieval(self):
        self.hub._record_history("Track 1", "https://stream.com/1", "stream", "vlc")
        self.hub._record_history("Track 2", "https://stream.com/2", "stream", "vlc")
        hist = self.hub.get_history(limit=5)
        self.assertTrue(hist["ok"])
        self.assertEqual(hist["count"], 2)
        self.assertEqual(hist["recent_plays"][0]["title"], "Track 2")


class TestToolDefinitionsOpalIntegration(unittest.TestCase):
    """Test Suite for Opal Tool Registration & Dispatcher Integration."""

    def test_specs_registered(self):
        names = [s["name"] for s in tool_definitions.TOOL_SPECS]
        self.assertIn("searchUniversalMedia", names)
        self.assertIn("playMediaStream", names)
        self.assertIn("listIPTVChannels", names)
        self.assertIn("aiMediaCopilot", names)
        self.assertIn("getMediaPlaybackHistory", names)

    @patch("actions.opal_media_hub.search_universal_media")
    def test_execute_search_media(self, mock_search):
        mock_search.return_value = {"ok": True, "results": []}
        res = tool_definitions.execute_tool("searchUniversalMedia", {"query": "chillhop"})
        self.assertTrue(res["ok"])
        mock_search.assert_called_with("chillhop")

    @patch("actions.opal_media_hub.play_universal_media")
    def test_execute_play_media(self, mock_play):
        mock_play.return_value = {"ok": True, "status": "playing"}
        res = tool_definitions.execute_tool("playMediaStream", {"stream_url": "lofi_girl"})
        self.assertTrue(res["ok"])
        mock_play.assert_called_with("lofi_girl", title="", player_preference="auto")

    @patch("actions.opal_iptv.list_iptv_channels")
    def test_execute_list_iptv(self, mock_list):
        mock_list.return_value = {"ok": True, "channels": []}
        res = tool_definitions.execute_tool("listIPTVChannels", {"category": "News"})
        self.assertTrue(res["ok"])
        mock_list.assert_called_with(category="News", query="")

    @patch("actions.opal_ai_copilot.match_mood_media")
    def test_execute_ai_copilot(self, mock_copilot):
        mock_copilot.return_value = {"ok": True, "vibe": "chill"}
        res = tool_definitions.execute_tool("aiMediaCopilot", {"prompt": "play study music"})
        self.assertTrue(res["ok"])
        mock_copilot.assert_called_with("play study music")

    @patch("actions.opal_media_hub.get_media_playback_history")
    def test_execute_get_history(self, mock_hist):
        mock_hist.return_value = {"ok": True, "recent_plays": []}
        res = tool_definitions.execute_tool("getMediaPlaybackHistory", {"limit": 10})
        self.assertTrue(res["ok"])
        mock_hist.assert_called_with(limit=10)


if __name__ == "__main__":
    unittest.main()
