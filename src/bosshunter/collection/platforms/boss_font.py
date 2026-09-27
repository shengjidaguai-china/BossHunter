"""Dynamic decoding for BOSS's obfuscated salary font.

BOSS maps the digits 0-9 onto private-use-area codepoints and reshuffles that
mapping every time the page loads a fresh font file, so a static translation
table silently decodes wrong digits once the mapping moves. This module reads
the font the tab actually loaded: the collector asks the tab for its loaded
font faces (with a stylesheet scan as fallback), downloads the font file, and
rebuilds the mapping by comparing each private-use glyph's outline with the
glyphs bound to the ASCII digits in the same font.
"""

from __future__ import annotations

import io
import json
import re
from typing import Any

_PUA_MIN = 0xE000
_PUA_MAX = 0xF8FF
_ASCII_DIGITS = "0123456789"

# BOSS lists obfuscated glyphs inside the private use area block.
_RANGE_CODE = re.compile(r"[Uu]\+([0-9A-Fa-f]{4})")
_FONT_URL = re.compile(r"url\(\s*['\"]?([^'\")]+)['\"]?\s*\)")
_STYLESHEET_URL = re.compile(r"^https?://")

JS_COLLECT_FONT_SOURCES = """
(() => {
	const faces = [];
	try {
		document.fonts.forEach((face) => {
			faces.push({src: String(face.src || ''), range: String(face.unicodeRange || '')});
		});
	} catch (err) {}
	const sheets = [];
	try {
		document.querySelectorAll('link[rel="stylesheet"][href]').forEach((link) => sheets.push(link.href));
	} catch (err) {}
	const inline = [];
	try {
		document.querySelectorAll('style').forEach((tag) => inline.push(String(tag.textContent || '')));
	} catch (err) {}
	return JSON.stringify({faces, sheets, inline});
})()
"""


def _covers_private_use(range_text: str) -> bool:
	for hex_code in _RANGE_CODE.findall(range_text or ""):
		if _PUA_MIN <= int(hex_code, 16) <= _PUA_MAX:
			return True
	return False


def _face_font_urls(faces: Any) -> list[str]:
	urls: list[str] = []
	for face in faces if isinstance(faces, list) else []:
		if not isinstance(face, dict) or not _covers_private_use(str(face.get("range") or "")):
			continue
		match = _FONT_URL.search(str(face.get("src") or ""))
		if match and match.group(1) not in urls:
			urls.append(match.group(1))
	return urls


def parse_font_face_urls(css: str) -> list[str]:
	"""Font URLs from @font-face rules whose unicode-range covers the PUA block."""
	urls: list[str] = []
	for block in re.findall(r"@font-face\s*\{[^}]*\}", css or ""):
		if not _covers_private_use(block):
			continue
		match = _FONT_URL.search(block)
		if match and match.group(1) not in urls:
			urls.append(match.group(1))
	return urls


def collect_font_sources(evaluate_result: Any) -> tuple[list[str], list[str]]:
	"""Split the tab's answer into (font_urls, css_sources_for_fallback_scan)."""
	data: Any = evaluate_result
	if isinstance(data, str):
		try:
			data = json.loads(data)
		except json.JSONDecodeError:
			return [], []
	if not isinstance(data, dict):
		return [], []
	urls = _face_font_urls(data.get("faces"))
	css_sources: list[str] = [str(text) for text in data.get("inline") or [] if isinstance(text, str)]
	sheets = data.get("sheets")
	for href in sheets if isinstance(sheets, list) else []:
		if isinstance(href, str) and _STYLESHEET_URL.match(href):
			css_sources.append(href)
	return urls, css_sources


def _glyph_signature(glyph_set: Any, glyph_name: str) -> tuple | None:
	try:
		from fontTools.pens.recordingPen import DecomposingRecordingPen
	except ImportError:
		return None
	pen = DecomposingRecordingPen(glyph_set)
	try:
		glyph_set[glyph_name].draw(pen)
	except Exception:
		return None
	points: list[tuple[float, float]] = []
	for _operator, args in pen.value:
		for arg in args:
			if isinstance(arg, tuple) and len(arg) == 2:
				points.append((float(arg[0]), float(arg[1])))
	if len(points) < 3:
		return None
	min_x = min(point[0] for point in points)
	min_y = min(point[1] for point in points)
	span = max(max(point[0] for point in points) - min_x, max(point[1] for point in points) - min_y) or 1.0
	ops: list[tuple[str, tuple]] = []
	for operator, args in pen.value:
		normalized: list[tuple[float, float]] = []
		for arg in args:
			if not (isinstance(arg, tuple) and len(arg) == 2):
				return None
			normalized.append((
				round((float(arg[0]) - min_x) / span, 3),
				round((float(arg[1]) - min_y) / span, 3),
			))
		ops.append((operator, tuple(normalized)))
	return tuple(ops)


def build_boss_digit_map(font_bytes: bytes) -> dict[str, str]:
	"""Map private-use characters to the ASCII digits whose glyph outlines they copy.

	Requires the font to still bind the ASCII digit codepoints; a font that
	dropped them gives no in-font reference, so nothing is mapped and the
	caller keeps its previous behavior instead of guessing.
	"""
	try:
		from fontTools.ttLib import TTFont
	except ImportError:
		return {}
	font = None
	try:
		font = TTFont(io.BytesIO(font_bytes), fontNumber=0, lazy=True)
		cmap = font.getBestCmap()
		if not cmap:
			return {}
		glyph_set = font.getGlyphSet()
		digit_names: dict[str, str] = {}
		for digit in _ASCII_DIGITS:
			name = cmap.get(ord(digit))
			if name:
				digit_names[name] = digit
		if not digit_names:
			return {}
		signatures = {name: _glyph_signature(glyph_set, name) for name in digit_names}
		mapping: dict[str, str] = {}
		for code, glyph_name in cmap.items():
			if not (_PUA_MIN <= code <= _PUA_MAX):
				continue
			signature = _glyph_signature(glyph_set, glyph_name)
			if signature is None:
				continue
			for name, digit in digit_names.items():
				if signatures.get(name) == signature:
					mapping[chr(code)] = digit
					break
		return mapping
	except Exception:
		return {}
	finally:
		if font is not None:
			try:
				font.close()
			except Exception:
				pass
