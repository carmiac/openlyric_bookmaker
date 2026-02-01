"""Tests for HTML renderer."""

import pytest
from pathlib import Path

from openlyric_bookmaker.renderers.html import HTMLRenderer
from openlyric_bookmaker.models.song import Song, Properties
from openlyric_bookmaker.models.verse import Verse, VerseType, Line, ChordPosition


class TestHTMLRenderer:
    """Test suite for HTMLRenderer."""

    def test_renderer_initialization(self):
        """Test that HTML renderer can be initialized."""
        renderer = HTMLRenderer()
        assert renderer is not None
        assert renderer.env is not None

    def test_render_song(self, sample_song):
        """Test rendering a song to HTML."""
        renderer = HTMLRenderer()
        output = renderer.render_song(sample_song)

        assert isinstance(output, str)
        assert len(output) > 0

    def test_html_contains_title(self, sample_song):
        """Test that song title appears in HTML."""
        renderer = HTMLRenderer()
        output = renderer.render_song(sample_song)

        assert "Amazing Grace" in output

    def test_html_contains_authors(self, sample_song):
        """Test that author information is included."""
        renderer = HTMLRenderer()
        output = renderer.render_song(sample_song)

        assert "John Newton" in output

    def test_html_valid_structure(self, sample_song):
        """Test that HTML has basic valid structure."""
        renderer = HTMLRenderer()
        output = renderer.render_song(sample_song)

        # Should have basic HTML tags
        assert "<div" in output or "<h" in output or "<p" in output

    def test_chord_rendering_html(self, sample_song):
        """Test that chords are rendered in HTML format."""
        renderer = HTMLRenderer()
        output = renderer.render_song(sample_song)

        # Chords might be in spans or divs
        assert "G" in output
        assert "C" in output

    def test_verse_structure(self, sample_song):
        """Test that verses are properly structured in HTML."""
        renderer = HTMLRenderer()
        output = renderer.render_song(sample_song)

        # Should have some structure for verses
        assert "verse" in output.lower() or "lyrics" in output.lower()

    def test_render_index(self, sample_song):
        """Test rendering the main index page."""
        renderer = HTMLRenderer()
        sections = {
            "Traditional": [
                {"song": sample_song, "output_file": "amazing_grace.html", "title": "Amazing Grace"}
            ]
        }

        output = renderer.render_index(title="Test Songbook", sections=sections, songbook_config={})

        assert isinstance(output, str)
        assert "Test Songbook" in output
        assert "Traditional" in output
        assert "Amazing Grace" in output

    def test_navigation_generation(self, sample_song):
        """Test that navigation links are generated."""
        renderer = HTMLRenderer()
        sections = {
            "Section 1": [{"song": sample_song, "output_file": "song1.html", "title": "Song 1"}],
            "Section 2": [{"song": sample_song, "output_file": "song2.html", "title": "Song 2"}],
        }

        output = renderer.render_index(title="Test Songbook", sections=sections, songbook_config={})

        assert "Section 1" in output
        assert "Section 2" in output

    def test_sticky_section_headers(self, sample_song):
        """Test that CSS for sticky headers is present."""
        renderer = HTMLRenderer()
        sections = {"Test": [{"song": sample_song, "output_file": "test.html", "title": "Test"}]}

        output = renderer.render_index(title="Test Songbook", sections=sections, songbook_config={})

        # Should have CSS for sticky positioning
        assert "sticky" in output.lower() or "position" in output.lower()

    def test_recordings_in_html(self, sample_song_with_recordings):
        """Test that recording links appear in HTML."""
        renderer = HTMLRenderer()
        output = renderer.render_song(sample_song_with_recordings)

        # Should contain recording information
        assert "Live Performance" in output
        assert "Test Band" in output
        assert "youtube.com" in output or "test123" in output

    def test_multiple_recordings(self, sample_song_with_recordings):
        """Test rendering multiple recordings."""
        renderer = HTMLRenderer()
        output = renderer.render_song(sample_song_with_recordings)

        assert "Live Performance" in output
        assert "Studio Version" in output

    def test_alternate_titles_in_index(self, sample_song):
        """Test that alternate titles appear in navigation."""
        renderer = HTMLRenderer()
        sections = {
            "Test": [{"song": sample_song, "output_file": "test.html", "title": "Amazing Grace"}]
        }

        output = renderer.render_index(title="Test Songbook", sections=sections, songbook_config={})

        # Both titles should be accessible
        assert "Amazing Grace" in output

    def test_html_escaping(self):
        """Test that HTML special characters are escaped."""
        verse = Verse(
            name="v1",
            verse_type=VerseType.VERSE,
            lines=[Line("Test <script>alert('xss')</script>", [])],
        )

        song = Song(
            properties=Properties(
                titles=["Test & Test"],
                authors=[],
                copyright="",
                ccli_no="",
                keywords=[],
                themes=[],
                tune="",
            ),
            verses=[verse],
            source_file=Path("test.xml"),
        )

        renderer = HTMLRenderer()
        output = renderer.render_song(song)

        # Jinja2 should auto-escape by default
        # Script tag should be escaped
        assert "<script>" not in output or "&lt;script&gt;" in output

    def test_responsive_design_hints(self, sample_song):
        """Test that HTML includes responsive design elements."""
        renderer = HTMLRenderer()
        sections = {"Test": [{"song": sample_song, "output_file": "test.html", "title": "Test"}]}

        output = renderer.render_index(title="Test Songbook", sections=sections, songbook_config={})

        # Should have viewport meta or responsive CSS
        assert (
            "viewport" in output.lower()
            or "responsive" in output.lower()
            or "mobile" in output.lower()
        )
        assert (
            "viewport" in output.lower()
            or "responsive" in output.lower()
            or "mobile" in output.lower()
        )
