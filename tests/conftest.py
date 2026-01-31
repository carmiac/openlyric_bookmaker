"""Pytest configuration and shared fixtures."""

from pathlib import Path
import pytest

from openlyric_bookmaker.models.song import Song, Properties, Recording
from openlyric_bookmaker.models.verse import Verse, VerseType, Line, ChordPosition


@pytest.fixture
def fixtures_dir() -> Path:
    """Return path to test fixtures directory."""
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def sample_xml_file(fixtures_dir) -> Path:
    """Return path to sample XML file."""
    return fixtures_dir / "amazing_grace.xml"


@pytest.fixture
def sample_song() -> Song:
    """Return a sample Song object for testing."""
    properties = Properties(
        titles=["Amazing Grace", "How Sweet the Sound"],
        authors=["John Newton"],
        copyright="Public Domain",
        ccli_no="22025",
        keywords=[],
        themes=[],
        tune=""
    )
    
    verse1 = Verse(
        name="v1",
        verse_type=VerseType.VERSE,
        lines=[
            Line(
                text="Amazing grace, how sweet the sound",
                chords=[
                    ChordPosition(position=0, chord_root="G"),
                    ChordPosition(position=16, chord_root="C"),
                ]
            ),
            Line(
                text="That saved a wretch like me",
                chords=[
                    ChordPosition(position=0, chord_root="G"),
                ]
            ),
        ]
    )
    
    chorus = Verse(
        name="c",
        verse_type=VerseType.CHORUS,
        lines=[
            Line(
                text="I once was lost, but now am found",
                chords=[]
            ),
        ]
    )
    
    return Song(
        properties=properties,
        verses=[verse1, chorus],
        source_file=Path("test.xml")
    )


@pytest.fixture
def sample_song_with_recordings() -> Song:
    """Return a Song with recording metadata."""
    properties = Properties(
        titles=["Test Song"],
        authors=["Test Author"],
        copyright="Copyright 2026",
        ccli_no="123456",
        keywords=["test"],
        themes=["testing"],
        tune="Test Tune"
    )
    
    verse = Verse(
        name="v1",
        verse_type=VerseType.VERSE,
        lines=[
            Line(text="Test lyrics", chords=[])
        ]
    )
    
    return Song(
        properties=properties,
        verses=[verse],
        recordings=[
            Recording(
                url="https://www.youtube.com/watch?v=test123",
                title="Live Performance",
                artist="Test Band"
            ),
            Recording(
                url="https://example.com/audio/test.mp3",
                title="Studio Version",
                artist="Test Artist"
            ),
        ],
        source_file=Path("test.xml")
    )


@pytest.fixture
def temp_output_dir(tmp_path) -> Path:
    """Return a temporary output directory for tests."""
    output = tmp_path / "output"
    output.mkdir()
    return output


@pytest.fixture
def temp_build_dir(tmp_path) -> Path:
    """Return a temporary build directory for tests."""
    build = tmp_path / "build"
    build.mkdir()
    return build
