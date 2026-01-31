"""Data models for songs and their metadata."""

from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from openlyric_bookmaker.models.verse import Verse


@dataclass
class Recording:
    """A recording of a song (audio, video, or link)."""

    url: str
    title: str | None = None
    artist: str | None = None

    @property
    def is_youtube(self) -> bool:
        """Check if this is a YouTube link."""
        return "youtube.com" in self.url or "youtu.be" in self.url

    @property
    def is_audio(self) -> bool:
        """Check if this is an audio file."""
        return self.url.lower().endswith((".mp3", ".ogg", ".wav", ".m4a", ".flac"))

    @property
    def is_video(self) -> bool:
        """Check if this is a video file."""
        return self.url.lower().endswith((".mp4", ".webm", ".ogv"))


@dataclass
class Properties:
    """Song properties/metadata."""

    titles: list[str] = field(default_factory=list)
    authors: list[str] = field(default_factory=list)
    copyright: str | None = None
    ccli_no: str | None = None
    keywords: list[str] = field(default_factory=list)
    themes: list[str] = field(default_factory=list)
    tune: str | None = None  # Custom extension for traditional tune names
    verse_order: list[str] = field(default_factory=list)
    release_date: date | None = None

    @property
    def primary_title(self) -> str:
        """Get the primary title of the song."""
        return self.titles[0] if self.titles else "Untitled"

    @property
    def author_string(self) -> str:
        """Get authors as a comma-separated string."""
        return ", ".join(self.authors)


@dataclass
class Song:
    """A complete song with metadata, lyrics, and optional recordings."""

    properties: Properties
    verses: list[Verse] = field(default_factory=list)
    recordings: list[Recording] = field(default_factory=list)
    comments: list[str] = field(default_factory=list)  # Pre-verse comments
    source_file: Path | None = None

    @property
    def title(self) -> str:
        """Get the primary title."""
        return self.properties.primary_title

    @property
    def authors(self) -> list[str]:
        """Get the list of authors."""
        return self.properties.authors

    @property
    def ordered_verses(self) -> list[Verse]:
        """Get verses in the order specified by verse_order, or XML order if not specified."""
        if not self.properties.verse_order:
            return self.verses

        # Create a map of verse names to verse objects
        verse_map = {v.name: v for v in self.verses}

        # Return verses in the specified order
        ordered = []
        for verse_name in self.properties.verse_order:
            if verse_name in verse_map:
                ordered.append(verse_map[verse_name])

        # Add any verses not in verse_order at the end
        ordered_names = set(self.properties.verse_order)
        for verse in self.verses:
            if verse.name not in ordered_names:
                ordered.append(verse)

        return ordered

    def get_verse_by_name(self, name: str) -> Verse | None:
        """Get a verse by its name."""
        for verse in self.verses:
            if verse.name == name:
                return verse
        return None

    def validate(self) -> list[str]:
        """Validate the song and return a list of validation errors."""
        errors = []

        if not self.properties.titles:
            errors.append("Song must have at least one title")

        if not self.verses:
            errors.append("Song must have at least one verse")

        # Check that all verses in verse_order exist
        verse_names = {v.name for v in self.verses}
        for verse_name in self.properties.verse_order:
            if verse_name not in verse_names:
                errors.append(f"verse_order references non-existent verse: {verse_name}")

        return errors
