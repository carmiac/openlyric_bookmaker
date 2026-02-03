"""Tests for ChordPro parser."""

import pytest
from pathlib import Path
from openlyric_bookmaker.parsers.chordpro import ChordProParser
from openlyric_bookmaker.models.verse import VerseType


class TestChordProParser:
    """Test ChordPro format parsing."""

    def test_parse_basic_song(self, tmp_path):
        """Test parsing a basic ChordPro song."""
        song_file = tmp_path / "test.cho"
        song_file.write_text("""{title: Test Song}
{artist: Test Artist}

{start_of_verse}
This is a [C]test
{end_of_verse}
""")

        parser = ChordProParser(song_file)
        song = parser.parse()

        assert song.properties.titles == ["Test Song"]
        assert song.properties.authors == ["Test Artist"]
        assert len(song.verses) == 1

    def test_parse_inline_chords(self, tmp_path):
        """Test parsing inline chord notation."""
        song_file = tmp_path / "test.cho"
        song_file.write_text("""{title: Chord Test}

{start_of_verse}
Amazing [D]grace how [G]sweet the [D]sound
{end_of_verse}
""")

        parser = ChordProParser(song_file)
        song = parser.parse()

        line = song.verses[0].lines[0]
        assert line.text == "Amazing grace how sweet the sound"
        assert len(line.chords) == 3
        assert line.chords[0].chord_root == "D"
        assert line.chords[0].position == 8
        assert line.chords[1].chord_root == "G"
        assert line.chords[1].position == 18

    def test_parse_chord_structures(self, tmp_path):
        """Test parsing chords with structures (m, 7, maj7, etc.)."""
        song_file = tmp_path / "test.cho"
        song_file.write_text("""{title: Complex Chords}

{start_of_verse}
Test [Dm]minor and [G7]seventh and [Cmaj7]major seventh
{end_of_verse}
""")

        parser = ChordProParser(song_file)
        song = parser.parse()

        chords = song.verses[0].lines[0].chords
        assert chords[0].chord_root == "D"
        assert chords[0].chord_structure == "m"
        assert chords[0].full_chord == "Dm"

        assert chords[1].chord_root == "G"
        assert chords[1].chord_structure == "7"
        assert chords[1].full_chord == "G7"

        assert chords[2].chord_root == "C"
        assert chords[2].chord_structure == "maj7"
        assert chords[2].full_chord == "Cmaj7"

    def test_parse_multiple_verses(self, tmp_path):
        """Test parsing multiple verses."""
        song_file = tmp_path / "test.cho"
        song_file.write_text("""{title: Multi-Verse}

{start_of_verse}
Verse one
{end_of_verse}

{start_of_verse}
Verse two
{end_of_verse}

{start_of_chorus}
Chorus here
{end_of_chorus}
""")

        parser = ChordProParser(song_file)
        song = parser.parse()

        assert len(song.verses) == 3
        assert song.verses[0].name == "v1"
        assert song.verses[0].verse_type == VerseType.VERSE
        assert song.verses[1].name == "v2"
        assert song.verses[1].verse_type == VerseType.VERSE
        assert song.verses[2].name == "c1"
        assert song.verses[2].verse_type == VerseType.CHORUS

    def test_parse_directives(self, tmp_path):
        """Test parsing various directives."""
        song_file = tmp_path / "test.cho"
        song_file.write_text("""{title: Directive Test}
{composer: John Doe}
{copyright: 2026}
{ccli: 12345}
{key: D}

{start_of_verse}
Test line
{end_of_verse}
""")

        parser = ChordProParser(song_file)
        song = parser.parse()

        assert "Directive Test" in song.properties.titles
        assert "John Doe" in song.properties.authors
        assert song.properties.copyright == "2026"
        assert song.properties.ccli_no == "12345"
        assert "Key: D" in song.properties.keywords

    def test_parse_short_directives(self, tmp_path):
        """Test parsing short directive forms."""
        song_file = tmp_path / "test.cho"
        song_file.write_text("""{t: Short Title}
{st: Short Subtitle}
{c: Comment}

{sov}
Verse
{eov}

{soc}
Chorus
{eoc}
""")

        parser = ChordProParser(song_file)
        song = parser.parse()

        assert "Short Title" in song.properties.titles
        assert len(song.verses) == 2
        assert song.verses[0].verse_type == VerseType.VERSE
        assert song.verses[1].verse_type == VerseType.CHORUS

    def test_parse_without_sections(self, tmp_path):
        """Test parsing lyrics without explicit section markers."""
        song_file = tmp_path / "test.cho"
        song_file.write_text("""{title: Implicit Verse}

This is a line [C]without section markers
Another [G]line""")

        parser = ChordProParser(song_file)
        song = parser.parse()

        # Should treat as verse
        assert len(song.verses) == 1
        assert song.verses[0].verse_type == VerseType.VERSE
        assert len(song.verses[0].lines) >= 2  # May have empty line at end

    def test_parse_empty_lines(self, tmp_path):
        """Test handling of empty lines in verses."""
        song_file = tmp_path / "test.cho"
        song_file.write_text("""{title: Empty Lines}

{start_of_verse}
Line one

Line three
{end_of_verse}
""")

        parser = ChordProParser(song_file)
        song = parser.parse()

        assert len(song.verses[0].lines) == 3
        assert song.verses[0].lines[0].text == "Line one"
        assert song.verses[0].lines[1].text == ""
        assert song.verses[0].lines[2].text == "Line three"

    def test_filename_as_fallback_title(self, tmp_path):
        """Test using filename as title when no title directive."""
        song_file = tmp_path / "my_awesome_song.cho"
        song_file.write_text("""{start_of_verse}
No title directive
{end_of_verse}
""")

        parser = ChordProParser(song_file)
        song = parser.parse()

        assert song.properties.titles == ["My Awesome Song"]

    def test_parse_bridge(self, tmp_path):
        """Test parsing bridge sections."""
        song_file = tmp_path / "test.cho"
        song_file.write_text("""{title: Bridge Test}

{start_of_bridge}
Bridge content
{end_of_bridge}
""")

        parser = ChordProParser(song_file)
        song = parser.parse()

        assert len(song.verses) == 1
        assert song.verses[0].name == "b1"
        assert song.verses[0].verse_type == VerseType.BRIDGE

    def test_tab_sections_ignored(self, tmp_path):
        """Test that tab sections are ignored."""
        song_file = tmp_path / "test.cho"
        song_file.write_text("""{title: Tab Test}

{start_of_tab}
E|---0---
B|---1---
{end_of_tab}

{start_of_verse}
Lyrics here
{end_of_verse}
""")

        parser = ChordProParser(song_file)
        song = parser.parse()

        # Only verse should be parsed, not tab
        assert len(song.verses) == 1
        assert song.verses[0].verse_type == VerseType.VERSE
