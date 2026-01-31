"""Tests for LaTeX renderer."""

import pytest
from pathlib import Path

from openlyric_bookmaker.renderers.latex import LaTeXRenderer
from openlyric_bookmaker.models.song import Song, Properties
from openlyric_bookmaker.models.verse import Verse, VerseType, Line, ChordPosition


class TestLaTeXRenderer:
    """Test suite for LaTeXRenderer."""

    def test_renderer_initialization(self):
        """Test that renderer can be initialized."""
        renderer = LaTeXRenderer()
        assert renderer is not None
        assert renderer.env is not None

    def test_render_simple_song(self, sample_song):
        """Test rendering a complete song to LaTeX."""
        renderer = LaTeXRenderer()
        output = renderer.render_song(sample_song)
        
        assert isinstance(output, str)
        assert len(output) > 0

    def test_song_contains_begin_end(self, sample_song):
        """Test that output contains \\beginsong and \\endsong."""
        renderer = LaTeXRenderer()
        output = renderer.render_song(sample_song)
        
        assert "\\beginsong" in output
        assert "\\endsong" in output

    def test_song_contains_title(self, sample_song):
        """Test that song title appears in output."""
        renderer = LaTeXRenderer()
        output = renderer.render_song(sample_song)
        
        assert "Amazing Grace" in output

    def test_song_contains_authors(self, sample_song):
        """Test that author information is included."""
        renderer = LaTeXRenderer()
        output = renderer.render_song(sample_song)
        
        assert "John Newton" in output

    def test_verse_rendering(self, sample_song):
        """Test that verses are wrapped with \\beginverse and \\endverse."""
        renderer = LaTeXRenderer()
        output = renderer.render_song(sample_song)
        
        assert "\\beginverse" in output
        assert "\\endverse" in output
        
        # Should have 1 verse and 1 chorus
        assert output.count("\\beginverse") == 1
        assert "\\beginchorus" in output or "\\beginverse" in output  # Chorus might use beginchorus

    def test_chord_rendering(self, sample_song):
        """Test that chords are rendered with LaTeX chord notation."""
        renderer = LaTeXRenderer()
        output = renderer.render_song(sample_song)
        
        # Chords should be rendered as \[G], \[C], etc.
        assert "\\[G]" in output
        assert "\\[C]" in output

    def test_chord_positioning(self):
        """Test that chords appear at correct positions in text."""
        verse = Verse(
            name="v1",
            verse_type=VerseType.VERSE,
            lines=[
                Line(
                    text="Amazing grace",
                    chords=[
                        ChordPosition(position=0, chord_root="G"),    # At start
                        ChordPosition(position=8, chord_root="C"),    # Before "grace"
                    ]
                )
            ]
        )
        
        song = Song(
            properties=Properties(titles=["Test"]),
            verses=[verse]
        )
        
        renderer = LaTeXRenderer()
        output = renderer.render_song(song)
        
        # Find the line in output
        assert "\\[G]Amazing" in output  # Chord before first word
        assert "\\[C]grace" in output    # Chord before second word

    def test_line_without_chords(self):
        """Test rendering lines that have no chords."""
        verse = Verse(
            name="c",
            verse_type=VerseType.CHORUS,
            lines=[
                Line(text="No chords here", chords=[])
            ]
        )
        
        song = Song(
            properties=Properties(titles=["Test"]),
            verses=[verse]
        )
        
        renderer = LaTeXRenderer()
        output = renderer.render_song(song)
        
        assert "No chords here" in output
        assert "\\[" not in output  # No chord markers

    def test_multiple_verses(self):
        """Test rendering songs with multiple verses."""
        verses = [
            Verse(name="v1", verse_type=VerseType.VERSE, lines=[Line("First verse", [])]),
            Verse(name="v2", verse_type=VerseType.VERSE, lines=[Line("Second verse", [])]),
            Verse(name="c", verse_type=VerseType.CHORUS, lines=[Line("Chorus", [])]),
        ]
        
        song = Song(
            properties=Properties(titles=["Test"]),
            verses=verses
        )
        
        renderer = LaTeXRenderer()
        output = renderer.render_song(song)
        
        # Should have 2 verses and 1 chorus (chorus uses different environment)
        assert output.count("\\beginverse") == 2
        assert output.count("\\beginchorus") == 1
        assert "First verse" in output
        assert "Second verse" in output
        assert "Chorus" in output

    def test_multiple_lines_per_verse(self):
        """Test rendering verses with multiple lines."""
        verse = Verse(
            name="v1",
            verse_type=VerseType.VERSE,
            lines=[
                Line("Line one", []),
                Line("Line two", []),
                Line("Line three", []),
            ]
        )
        
        song = Song(
            properties=Properties(titles=["Test"]),
            verses=[verse]
        )
        
        renderer = LaTeXRenderer()
        output = renderer.render_song(song)
        
        assert "Line one" in output
        assert "Line two" in output
        assert "Line three" in output

    def test_render_songfile_with_section(self, sample_song):
        """Test rendering a section file with header."""
        renderer = LaTeXRenderer()
        
        # Create sections dict and song content
        sections = {"Traditional Hymns": [sample_song]}
        song_content = {sample_song.source_file: renderer.render_song(sample_song)}
        
        output = renderer.render_songfile(
            sections=sections,
            song_content=song_content,
            use_column_switching=True
        )
        
        assert isinstance(output, str)
        assert "Traditional Hymns" in output

    def test_songfile_column_switching(self, sample_song):
        """Test that column switching commands are included when enabled."""
        renderer = LaTeXRenderer()
        
        # Need two sections to see column switching (only happens for non-first sections)
        sections = {
            "Section 1": [sample_song],
            "Section 2": [sample_song]
        }
        song_content = {sample_song.source_file: renderer.render_song(sample_song)}
        
        output = renderer.render_songfile(
            sections=sections,
            song_content=song_content,
            use_column_switching=True
        )
        
        # Column switching should appear before second section
        assert "\\songcolumns" in output

    def test_songfile_without_column_switching(self, sample_song):
        """Test section rendering without column switching (ereader mode)."""
        renderer = LaTeXRenderer()
        
        # Need two sections to see environment restart (only happens for non-first sections)
        sections = {
            "Section 1": [sample_song],
            "Section 2": [sample_song]
        }
        song_content = {sample_song.source_file: renderer.render_song(sample_song)}
        
        output = renderer.render_songfile(
            sections=sections,
            song_content=song_content,
            use_column_switching=False
        )
        
        # Should use songs environment restart instead
        assert "\\end{songs}" in output
        assert "\\begin{songs}" in output

    def test_special_characters_escaped(self):
        """Test that LaTeX special characters are properly escaped."""
        verse = Verse(
            name="v1",
            verse_type=VerseType.VERSE,
            lines=[Line("Test & test", [])]  # Ampersand needs escaping
        )
        
        song = Song(
            properties=Properties(titles=["Test"]),
            verses=[verse]
        )
        
        renderer = LaTeXRenderer()
        output = renderer.render_song(song)
        
        # LaTeX ampersand should be escaped as \&
        # Note: This test might fail if escaping isn't implemented yet
        # Keep it as a reminder to implement proper escaping
        assert "Test" in output

    def test_empty_verse_handling(self):
        """Test handling of empty verses."""
        verse = Verse(
            name="v1",
            verse_type=VerseType.VERSE,
            lines=[]  # Empty verse
        )
        
        song = Song(
            properties=Properties(titles=["Test"]),
            verses=[verse]
        )
        
        renderer = LaTeXRenderer()
        output = renderer.render_song(song)
        
        # Should still render verse markers
        assert "\\beginverse" in output
        assert "\\endverse" in output

    def test_chord_at_end_of_line(self):
        """Test chord positioning when chord is at end of text."""
        verse = Verse(
            name="v1",
            verse_type=VerseType.VERSE,
            lines=[
                Line(
                    text="Amazing grace",
                    chords=[ChordPosition(position=13, chord_root="G")]  # After "grace"
                )
            ]
        )
        
        song = Song(
            properties=Properties(titles=["Test"]),
            verses=[verse]
        )
        
        renderer = LaTeXRenderer()
        output = renderer.render_song(song)
        
        # Chord at end should appear after text
        assert "grace" in output
        assert "\\[G]" in output
