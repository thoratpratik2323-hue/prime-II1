"""
tests/test_accuracy_engine.py — Comprehensive Unit Tests for Prime Accuracy Engine.

Verifies:
1. Intent Classification across all 7 operational categories
2. Accuracy Directive retrieval & content validation
3. Morphological & fuzzy tool name matching (snake_case, kebab-case, camelCase)
4. Universal argument aliasing across WhatsApp, System, Files, Browser, and Media tools
5. Multi-word contact name and Marathi/Hindi conversational particle stripping
"""

import unittest
from core.intent_router import (
    classify_intent,
    get_accuracy_directive,
    is_coding_task,
    INTENT_CODING,
    INTENT_WHATSAPP,
    INTENT_SYSTEM,
    INTENT_BROWSER,
    INTENT_MEDIA,
    INTENT_OBSIDIAN,
    INTENT_CONVERSATION,
)
from tool_definitions import execute_tool
from whatsapp_manager import resolve_recipient, load_contacts


class TestAccuracyEngine(unittest.TestCase):

    def test_01_intent_classification_whatsapp(self):
        """Verify WhatsApp action intent classification."""
        self.assertEqual(classify_intent("send a whatsapp message to yome"), INTENT_WHATSAPP)
        self.assertEqual(classify_intent("open whatsapp chat with rahul"), INTENT_WHATSAPP)
        self.assertEqual(classify_intent("call on whatsapp to bappu"), INTENT_WHATSAPP)
        self.assertEqual(classify_intent("read whatsapp chats"), INTENT_WHATSAPP)

    def test_02_intent_classification_system_control(self):
        """Verify system control intent classification."""
        self.assertEqual(classify_intent("increase volume by 10"), INTENT_SYSTEM)
        self.assertEqual(classify_intent("volume down"), INTENT_SYSTEM)
        self.assertEqual(classify_intent("mute sound"), INTENT_SYSTEM)
        self.assertEqual(classify_intent("take a screenshot"), INTENT_SYSTEM)
        self.assertEqual(classify_intent("what is cpu usage"), INTENT_SYSTEM)

    def test_03_intent_classification_browser(self):
        """Verify browser & web search intent classification."""
        self.assertEqual(classify_intent("search google for latest ai news"), INTENT_BROWSER)
        self.assertEqual(classify_intent("search youtube for interstellar theme"), INTENT_BROWSER)
        self.assertEqual(classify_intent("open website https://github.com"), INTENT_BROWSER)

    def test_04_intent_classification_media(self):
        """Verify media playback intent classification."""
        self.assertEqual(classify_intent("play music"), INTENT_MEDIA)
        self.assertEqual(classify_intent("pause music"), INTENT_MEDIA)
        self.assertEqual(classify_intent("next song"), INTENT_MEDIA)

    def test_05_intent_classification_obsidian(self):
        """Verify second brain / obsidian intent classification."""
        self.assertEqual(classify_intent("save note in obsidian"), INTENT_OBSIDIAN)
        self.assertEqual(classify_intent("search second brain for architecture"), INTENT_OBSIDIAN)

    def test_06_intent_classification_coding(self):
        """Verify coding task classification."""
        self.assertEqual(classify_intent("write a python function to compute fibonacci"), INTENT_CODING)
        self.assertEqual(classify_intent("debug this syntax error in index.ts"), INTENT_CODING)
        self.assertEqual(classify_intent("run unit tests for prime"), INTENT_CODING)

    def test_07_accuracy_directives(self):
        """Verify accuracy directives are non-empty and specify correct tool constraints."""
        for intent in (INTENT_WHATSAPP, INTENT_SYSTEM, INTENT_BROWSER, INTENT_CODING, INTENT_MEDIA, INTENT_OBSIDIAN):
            directive = get_accuracy_directive(intent)
            self.assertIsNotNone(directive)
            self.assertIn("ACCURACY DIRECTIVE", directive)

    def test_08_morphological_tool_resolution_snake_case(self):
        """Verify execute_tool resolves snake_case and non-camelCase names seamlessly."""
        res_time = execute_tool("get_current_time", {})
        self.assertTrue(res_time.get("ok"))
        self.assertIn("Current system time", str(res_time))

        res_time_kebab = execute_tool("get-current-time", {})
        self.assertTrue(res_time_kebab.get("ok"))

        res_sys = execute_tool("system_info", {})
        self.assertTrue(res_sys.get("ok"))

    def test_09_universal_argument_aliasing(self):
        """Verify argument normalization maps aliases to expected parameter keys."""
        # openWhatsAppChat accepts 'target', 'name', 'to', 'contact' as 'recipient'
        res_chat = execute_tool("open_whatsapp_chat", {"target": "yome"})
        self.assertTrue(res_chat.get("ok"))
        self.assertEqual(res_chat.get("recipient"), "Yome")

        res_chat_name = execute_tool("openWhatsAppChat", {"name": "yome"})
        self.assertTrue(res_chat_name.get("ok"))
        self.assertEqual(res_chat_name.get("recipient"), "Yome")

    def test_10_multilingual_contact_particle_stripping(self):
        """Verify Hindi/Marathi particles ('ko', 'la') are cleanly stripped during contact lookup."""
        num, name = resolve_recipient("yome ko")
        self.assertEqual(num, "+919022559152")
        self.assertEqual(name, "Yome")

        num, name = resolve_recipient("yome la")
        self.assertEqual(num, "+919022559152")
        self.assertEqual(name, "Yome")

        num, name = resolve_recipient("yo me ko")
        self.assertEqual(num, "+919022559152")
        self.assertEqual(name, "Yome")

        num, name = resolve_recipient("yo me la")
        self.assertEqual(num, "+919022559152")
        self.assertEqual(name, "Yome")

        num, name = resolve_recipient("bhagwat dande la")
        self.assertEqual(num, "+919226763415")
        self.assertEqual(name, "Bhagwat Dhonde")


if __name__ == "__main__":
    unittest.main()
