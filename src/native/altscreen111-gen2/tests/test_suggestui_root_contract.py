"""Static source-contract guard for suggestUI URL advertisement.

This is NOT a QNX build, CoreFoundation unit test, iPhone acceptance test,
or evidence that a non-empty suggestUI was received.
Run with: python3 -m unittest discover -s src/native/altscreen111-gen2/tests -p 'test_suggestui_root_contract.py'
"""
from pathlib import Path
import re
import unittest


SOURCE = Path(__file__).resolve().parents[1] / "libaltscreen111_gen2.c"


def section(source: str, start: str, end: str) -> str:
    assert source.count(start) == 1, f"expected exactly one {start}"
    _, tail = source.split(start, 1)
    assert end in tail, f"missing marker {end}"
    return tail.split(end, 1)[0]


class SuggestUIRootContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = SOURCE.read_text(encoding="utf-8")
        cls.writer = section(
            cls.source,
            "static int add_alt_suggest_ui_urls(CFMutableDictionaryRef info)",
            "static int add_reference_viewarea",
        )
        cls.server = section(
            cls.source,
            "static CFDictionaryRef gen2_serverinfo_scoped(",
            "static ",
        )
        cls.platform = section(
            cls.source,
            "static OSStatus mibr_platform_control(",
            "OSStatus AirPlayReceiverSessionPlatformControl(",
        )

    def test_key_exactly_lower_camel(self):
        self.assertIn('s_cf("altScreenSuggestUIURLs")', self.writer)

    def test_writer_sets_root_not_display(self):
        self.assertIn("p_CFDictionarySetValue(info,key,urls);", self.writer)
        self.assertNotIn("p_CFDictionarySetValue(alt,key,urls);", self.writer)
        self.assertIn("p_CFDictionaryGetValue(info,key)!=urls", self.writer)

    def test_single_root_call_after_displays_are_advertised(self):
        self.assertEqual(self.source.count("add_alt_suggest_ui_urls(info)"), 1)
        self.assertNotIn("add_alt_suggest_ui_urls(alt)", self.source)
        self.assertLess(
            self.server.index("p_CFDictionarySetValue(info,kdisplays,displays)"),
            self.server.index("add_alt_suggest_ui_urls(info)"),
        )

    def test_classic_parity_keeps_capability_disabled(self):
        self.assertIn(
            "if(!compat_profile_exact_reference() && !add_alt_suggest_ui_urls(info))",
            self.server,
        )

    def test_no_inherited_nested_capability_on_custom_display(self):
        self.assertIn(
            'remove_key(alt,"altScreenSuggestUIURLs")',
            self.server,
        )

    def test_error_returns_original_stock_descriptor(self):
        ix = self.server.index("if(!compat_profile_exact_reference() && !add_alt_suggest_ui_urls(info))")
        self.assertIn("return base;", self.server[ix:ix + 350])

    def test_list_not_truncated_at_previous_192_byte_buffer(self):
        self.assertIn("char blob[2048],url[2048];", self.writer)
        self.assertIn('config_line_value(blob,"urls",url,sizeof(url))', self.writer)
        self.assertIn('read_layered_value(g_ui_urls_config_name', self.writer)

    def test_root_logging_is_shape_only(self):
        self.assertIn("GEN2 stock ROOT altScreenSuggestUIURLs=array count=", self.server)
        self.assertIn("GEN2 /info root altScreenSuggestUIURLs count=", self.writer)
        self.assertNotIn('logf_u2("GEN2 stock ROOT altScreenSuggestUIURLs[%', self.server)

    def test_passive_suggestui_behavior_is_retained(self):
        self.assertIn('strcmp(c,"suggestUI")==0', self.platform)
        self.assertIn("policy=LIVI_NOOP urls_not_shown=1", self.platform)
        self.assertIn("return K_NO_ERR;", self.platform)
        self.assertNotIn("command_showui", self.platform)

    def test_no_new_user_toggle_or_settings_key(self):
        self.assertNotIn("navigation.followSuggestions", self.source)
        self.assertNotIn("follow_suggestions", self.source)


if __name__ == "__main__":
    unittest.main()
