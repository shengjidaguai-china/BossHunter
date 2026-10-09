"""Font-derived BOSS digit mapping, exercised on synthetic fonts."""

import io
import json
import unittest
from unittest import TestCase

from bosshunter.collection.platforms import boss as boss_module
from bosshunter.collection.platforms import boss_font
from bosshunter.collection.platforms.boss import decode_boss_text, install_boss_digit_map

try:
    from fontTools.fontBuilder import FontBuilder
    from fontTools.pens.ttGlyphPen import TTGlyphPen

    HAVE_FONTTOOLS = True
except ImportError:
    HAVE_FONTTOOLS = False


def _rect(width, height):
    pen = TTGlyphPen(None)
    pen.moveTo((10, 10))
    pen.lineTo((10 + width, 10))
    pen.lineTo((10 + width, 10 + height))
    pen.lineTo((10, 10 + height))
    pen.closePath()
    return pen


def _build_font(digit_shapes, pua_assignments, *, include_ascii=True, woff2=True, unmatched_pua=()):
    """Build a synthetic font whose PUA glyphs copy the given digit outlines.

    digit_shapes maps a digit to its rectangle, pua_assignments maps a PUA
    codepoint to the digit whose outline it copies, and unmatched_pua lists
    PUA codepoints carrying an outline no digit shares.
    """
    glyphs = {".notdef": TTGlyphPen(None).glyph()}
    cmap = {}
    names = [".notdef"]
    if include_ascii:
        for digit, (width, height) in digit_shapes.items():
            name = f"d{digit}"
            names.append(name)
            glyphs[name] = _rect(width, height).glyph()
            cmap[ord(digit)] = name
    for code, digit in pua_assignments.items():
        name = f"p{code}"
        names.append(name)
        glyphs[name] = _rect(*digit_shapes[digit]).glyph()
        cmap[code] = name
    for code in unmatched_pua:
        name = f"u{code}"
        names.append(name)
        glyphs[name] = _rect(300, 300).glyph()
        cmap[code] = name
    builder = FontBuilder(1000, isTTF=True)
    builder.setupGlyphOrder(names)
    builder.setupCharacterMap(cmap)
    builder.setupGlyf(glyphs)
    builder.setupHorizontalMetrics({name: (600, 50) for name in names})
    builder.setupHorizontalHeader(ascent=800, descent=-200)
    builder.setupNameTable({"familyName": "BossHunterTest", "styleName": "Regular"})
    builder.setupOS2()
    builder.setupPost()
    buffer = io.BytesIO()
    if woff2:
        builder.font.flavor = "woff2"
    builder.font.save(buffer)
    return buffer.getvalue()


@unittest.skipUnless(HAVE_FONTTOOLS, "fontTools is required for the synthetic font tests")
class BuildBossDigitMapTest(TestCase):
    @classmethod
    def setUpClass(cls):
        # Every digit gets a distinct rectangle outline.
        cls.digit_shapes = {digit: (100 + 10 * index, 700 - 10 * index) for index, digit in enumerate("0123456789")}

    def test_map_follows_outlines_not_codepoints(self):
        # A reshuffled mapping: E031 carries the outline of 7, not of 0.
        font = _build_font(self.digit_shapes, {0xE031: "7", 0xE032: "3", 0xE036: "5"})
        mapping = boss_font.build_boss_digit_map(font)
        self.assertEqual({"\ue031": "7", "\ue032": "3", "\ue036": "5"}, mapping)

    def test_ttf_and_woff2_both_decode(self):
        for woff2 in (False, True):
            with self.subTest(woff2=woff2):
                font = _build_font(self.digit_shapes, {0xE038: "9"}, woff2=woff2)
                self.assertEqual({"\ue038": "9"}, boss_font.build_boss_digit_map(font))

    def test_font_without_ascii_reference_maps_nothing(self):
        # No in-font reference exists when the ASCII digits are gone from cmap.
        font = _build_font(self.digit_shapes, {0xE031: "7"}, include_ascii=False)
        self.assertEqual({}, boss_font.build_boss_digit_map(font))

    def test_unmatched_pua_glyph_is_skipped(self):
        font = _build_font(self.digit_shapes, {0xE031: "4"}, unmatched_pua=[0xE0AA])
        mapping = boss_font.build_boss_digit_map(font)
        self.assertEqual({"\ue031": "4"}, mapping)
        self.assertNotIn("\ue0aa", mapping)

    def test_garbage_font_bytes_map_nothing(self):
        self.assertEqual({}, boss_font.build_boss_digit_map(b"not a font at all"))


class InstallAndDecodeTest(TestCase):
    def tearDown(self):
        boss_module._BOSS_DYNAMIC_DIGITS.clear()

    def test_install_replaces_and_reports_changes(self):
        self.assertTrue(install_boss_digit_map({"\ue031": "7"}))
        self.assertFalse(install_boss_digit_map({"\ue031": "7"}))
        self.assertTrue(install_boss_digit_map({"\ue031": "8"}))

    def test_install_rejects_invalid_entries(self):
        self.assertFalse(install_boss_digit_map({}))
        self.assertFalse(install_boss_digit_map({"ab": "1", "\ue031": "12", "\ue032": "x"}))
        self.assertEqual({}, boss_module._BOSS_DYNAMIC_DIGITS)

    def test_decode_prefers_dynamic_table_then_falls_back_to_static(self):
        # Static table: E031 -> 0, E036 -> 5.
        self.assertEqual("05", decode_boss_text("\ue031\ue036"))
        install_boss_digit_map({"\ue031": "7", "\ue036": "5"})
        self.assertEqual("75", decode_boss_text("\ue031\ue036"))
        # A codepoint the dynamic mapping does not cover keeps the static decode.
        install_boss_digit_map({"\ue031": "7"})
        self.assertEqual("75", decode_boss_text("\ue031\ue036"))
        # Residual private-use characters outside both tables stay untouched.
        self.assertEqual("7\ue400", decode_boss_text("\ue031\ue400"))


class FontSourceTest(TestCase):
    def test_collect_font_sources_from_json_string(self):
        raw = json.dumps({
            "faces": [
                {"src": 'url("https://static.zhipin.com/font/mix.woff2") format("woff2")', "range": "U+E031-U+E03A"},
                {"src": 'url("https://static.zhipin.com/font/latin.woff2")', "range": "U+0000-00FF"},
            ],
            "sheets": ["https://www.zhipin.com/css/main.css"],
            "inline": ["@font-face{font-family:latin;}"],
        })
        urls, css_sources = boss_font.collect_font_sources(raw)
        self.assertEqual(["https://static.zhipin.com/font/mix.woff2"], urls)
        self.assertEqual(["@font-face{font-family:latin;}", "https://www.zhipin.com/css/main.css"], css_sources)

    def test_collect_font_sources_handles_garbage(self):
        for value in (None, "not json", 42, {"faces": "nope"}):
            with self.subTest(value=value):
                self.assertEqual(([], []), boss_font.collect_font_sources(value))

    def test_parse_font_face_urls_keeps_only_pua_ranges(self):
        css = (
            "@font-face{font-family:mix;src:url(https://cdn/x.woff2) format(\"woff2\");unicode-range:U+E031-U+E03A;}"
            "@font-face{font-family:latin;src:url(https://cdn/y.woff2);unicode-range:U+0000-00FF;}"
        )
        self.assertEqual(["https://cdn/x.woff2"], boss_font.parse_font_face_urls(css))

    def test_parse_font_face_urls_deduplicates(self):
        css = (
            "@font-face{font-family:a;src:url(https://cdn/x.woff2);unicode-range:U+E031;}"
            "@font-face{font-family:b;src:url(https://cdn/x.woff2);unicode-range:U+E032;}"
        )
        self.assertEqual(["https://cdn/x.woff2"], boss_font.parse_font_face_urls(css))


if __name__ == "__main__":
    unittest.main()
