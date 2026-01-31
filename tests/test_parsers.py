"""Tests for OpenLyrics XML parser."""

from pathlib import Path
import pytest

from openlyric_bookmaker.parsers.openlyrics import OpenLyricsParser
from openlyric_bookmaker.models.song import Song
from openlyric_bookmaker.models.verse import ChordPosition


class TestOpenLyricsParser:
    """Test suite for OpenLyrics parser functions."""

    def test_parse_basic_song(self, sample_xml_file):
        """Test parsing a complete OpenLyrics XML file."""
        song = OpenLyricsParser.parse_file(sample_xml_file)
        
        assert isinstance(song, Song)
        assert song.source_file == sample_xml_file

    def test_parse_titles(self, sample_xml_file):
        """Test parsing primary and alternate titles."""
        song = OpenLyricsParser.parse_file(sample_xml_file)
        
        assert len(song.properties.titles) == 2
        assert "Amazing Grace" in song.properties.titles
        assert "How Sweet the Sound" in song.properties.titles

    def test_parse_authors(self, sample_xml_file):
        """Test parsing author information."""
        song = OpenLyricsParser.parse_file(sample_xml_file)
        
        assert len(song.properties.authors) == 1
        assert "John Newton" in song.properties.authors

    def test_parse_copyright(self, sample_xml_file):
        """Test parsing copyright information."""
        song = OpenLyricsParser.parse_file(sample_xml_file)
        
        assert song.properties.copyright == "Public Domain"

    def test_parse_ccli_number(self, sample_xml_file):
        """Test parsing CCLI number."""
        song = OpenLyricsParser.parse_file(sample_xml_file)
        
        assert song.properties.ccli_no == "22025"

    def test_parse_verses(self, sample_xml_file):
        """Test parsing verse structure."""
        song = OpenLyricsParser.parse_file(sample_xml_file)
        
        assert len(song.verses) == 3
        assert song.verses[0].name == "v1"
        assert song.verses[1].name == "v2"
        assert song.verses[2].name == "c"

    def test_parse_verse_types(self, sample_xml_file):
        """Test parsing verse types (verse, chorus, etc.)."""
        song = OpenLyricsParser.parse_file(sample_xml_file)
        
        # First two should default to "verse"
        assert song.verses[0].verse_type.value == "verse"
        assert song.verses[1].verse_type.value == "verse"
        
        # Last one explicitly marked as chorus
        assert song.verses[2].verse_type.value == "chorus"

    def test_parse_lines(self, sample_xml_file):
        """Test parsing lines within verses."""
        song = OpenLyricsParser.parse_file(sample_xml_file)
        
        verse1 = song.verses[0]
        assert len(verse1.lines) == 2
        
        # Check text content (chords should be removed from text)
        assert "Amazing" in verse1.lines[0].text
        assert "grace" in verse1.lines[0].text

    def test_parse_chords(self, sample_xml_file):
        """Test parsing chord information."""
        song = OpenLyricsParser.parse_file(sample_xml_file)
        
        verse1 = song.verses[0]
        line1 = verse1.lines[0]
        
        # First line should have 3 chords: G, C, G
        assert len(line1.chords) == 3
        assert line1.chords[0].chord_root == "G"
        assert line1.chords[1].chord_root == "C"
        assert line1.chords[2].chord_root == "G"

    def test_parse_chord_positions(self, sample_xml_file):
        """Test that chord positions are correctly calculated."""
        song = OpenLyricsParser.parse_file(sample_xml_file)
        
        verse1 = song.verses[0]
        line1 = verse1.lines[0]
        
        # First chord at position 0 (start of line)
        assert line1.chords[0].position == 0
        
        # Subsequent chords should have positions > 0
        assert line1.chords[1].position > 0
        assert line1.chords[2].position > line1.chords[1].position

    def test_parse_verse_without_chords(self, sample_xml_file):
        """Test parsing verses that have no chords."""
        song = OpenLyricsParser.parse_file(sample_xml_file)
        
        chorus = song.verses[2]  # Chorus has no chords
        assert len(chorus.lines) == 2
        assert len(chorus.lines[0].chords) == 0
        assert "I once was lost" in chorus.lines[0].text

    def test_parse_keywords(self, sample_xml_file):
        """Test parsing keywords/tags."""
        song = OpenLyricsParser.parse_file(sample_xml_file)
        
        # Keywords should be parsed from comma-separated string
        assert len(song.properties.keywords) >= 2
        assert "grace" in song.properties.keywords
        assert "hymn" in song.properties.keywords

    def test_parse_themes(self, sample_xml_file):
        """Test parsing theme information."""
        song = OpenLyricsParser.parse_file(sample_xml_file)
        
        assert len(song.properties.themes) == 2
        assert "Grace" in song.properties.themes
        assert "Redemption" in song.properties.themes

    def test_parse_missing_optional_fields(self, fixtures_dir):
        """Test parsing a minimal song with only required fields."""
        # Create minimal XML
        minimal_xml = fixtures_dir / "minimal.xml"
        minimal_xml.write_text("""<?xml version="1.0" encoding="UTF-8"?>
<song xmlns="http://openlyrics.info/namespace/2009/song">
  <properties>
    <titles>
      <title>Test Song</title>
    </titles>
  </properties>
  <lyrics>
    <verse name="v1">
      <lines>
        <line>Test lyrics</line>
      </lines>
    </verse>
  </lyrics>
</song>""")
        
        song = OpenLyricsParser.parse_file(minimal_xml)
        
        assert song.properties.titles == ["Test Song"]
        assert song.properties.authors == []
        assert song.properties.copyright is None or song.properties.copyright == ""
        assert song.properties.ccli_no is None or song.properties.ccli_no == ""

    def test_parse_with_recordings(self, fixtures_dir):
        """Test parsing recording metadata (extension to OpenLyrics)."""
        # Create XML with recordings
        recording_xml = fixtures_dir / "with_recordings.xml"
        recording_xml.write_text("""<?xml version="1.0" encoding="UTF-8"?>
<song xmlns="http://openlyrics.info/namespace/2009/song">
  <properties>
    <titles>
      <title>Song with Recordings</title>
    </titles>
    <recordings>
      <recording>
        <title>Live Performance</title>
        <artist>Test Band</artist>
        <url>https://www.youtube.com/watch?v=test</url>
      </recording>
      <recording>
        <title>Studio Version</title>
        <artist>Test Artist</artist>
        <url>https://example.com/test.mp3</url>
      </recording>
    </recordings>
  </properties>
  <lyrics>
    <verse name="v1">
      <lines><line>Test</line></lines>
    </verse>
  </lyrics>
</song>""")
        
        song = OpenLyricsParser.parse_file(recording_xml)
        
        assert len(song.recordings) == 2
        assert song.recordings[0].title == "Live Performance"
        assert song.recordings[0].artist == "Test Band"
        assert "youtube.com" in song.recordings[0].url
        assert song.recordings[1].title == "Studio Version"

    def test_parse_nonexistent_file(self):
        """Test error handling for missing files."""
        with pytest.raises(FileNotFoundError):
            OpenLyricsParser.parse_file(Path("nonexistent.xml"))

    def test_parse_invalid_xml(self, fixtures_dir):
        """Test error handling for malformed XML."""
        invalid_xml = fixtures_dir / "invalid.xml"
        invalid_xml.write_text("This is not XML")
        
        # Should raise XML parsing error
        with pytest.raises(Exception):  # xml.etree.ElementTree.ParseError
            OpenLyricsParser.parse_file(invalid_xml)
