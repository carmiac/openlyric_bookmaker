"""Data models for verses, chords, and lyrics."""

from dataclasses import dataclass, field
from enum import Enum


class VerseType(Enum):
    """Type of verse in a song."""

    VERSE = "verse"
    CHORUS = "chorus"
    BRIDGE = "bridge"
    PRECHORUS = "prechorus"
    ENDING = "ending"
    INTRO = "intro"
    OUTRO = "outro"
    TAG = "tag"
    UNKNOWN = "unknown"


@dataclass
class ChordPosition:
    """Position and chord information within a line of lyrics."""

    position: int  # Character position in the line
    chord_root: str  # e.g., "C", "D", "Eb"
    chord_structure: str | None = None  # e.g., "m", "7", "maj7"

    @property
    def full_chord(self) -> str:
        """Get the full chord notation."""
        if self.chord_structure:
            return f"{self.chord_root}{self.chord_structure}"
        return self.chord_root


@dataclass
class Chord:
    """A chord with its root and optional structure."""

    root: str  # e.g., "C", "D", "E&" (OpenLyrics uses & for flat)
    structure: str | None = None  # e.g., "m", "7", "maj7", "sus4"

    @property
    def display(self) -> str:
        """Get display representation, converting & to ♭."""
        root = self.root.replace("&", "b")  # Convert OpenLyrics flat to b
        if self.structure:
            return f"{root}{self.structure}"
        return root

    @property
    def latex(self) -> str:
        """Get LaTeX representation."""
        root = self.root.replace("&", "b")
        if self.structure:
            return f"{root}{self.structure}"
        return root


@dataclass
class Line:
    """A single line of lyrics, potentially with chords and comments."""

    text: str
    chords: list[ChordPosition] = field(default_factory=list)
    comment: str | None = None


@dataclass
class Verse:
    """A verse, chorus, or other section of a song."""

    name: str  # e.g., "v1", "c1", "b1"
    verse_type: VerseType
    lines: list[Line] = field(default_factory=list)

    @property
    def is_chorus(self) -> bool:
        """Check if this is a chorus."""
        return self.verse_type == VerseType.CHORUS

    @property
    def display_name(self) -> str:
        """Get a human-readable name for this verse."""
        type_name = self.verse_type.value.title()
        # Extract number from name if present (e.g., "v1" -> "1")
        number = "".join(c for c in self.name if c.isdigit())
        if number:
            return f"{type_name} {number}"
        return type_name
