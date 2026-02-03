"""Parser for ChordPro format files."""

import logging
import re
from pathlib import Path

from openlyric_bookmaker.models.song import Song, Properties, Recording
from openlyric_bookmaker.models.verse import Verse, Line, ChordPosition

logger = logging.getLogger(__name__)


class ChordProParser:
    """Parser for ChordPro format (.cho, .chordpro, .chopro, .crd files)."""

    # Directive patterns
    DIRECTIVE_PATTERN = re.compile(r"\{([^:}]+)(?::(.+))?\}")
    CHORD_PATTERN = re.compile(r"\[([^\]]+)\]")

    # Directive mappings to our data model
    TITLE_DIRECTIVES = {"title", "t"}
    SUBTITLE_DIRECTIVES = {"subtitle", "st", "artist"}
    AUTHOR_DIRECTIVES = {"composer", "writer", "artist"}
    COPYRIGHT_DIRECTIVES = {"copyright", "c"}
    CCLI_DIRECTIVES = {"ccli"}
    KEY_DIRECTIVES = {"key", "k"}

    # Custom extension directives (x-prefix)
    ALT_TITLE_DIRECTIVES = {"x-alt-title", "x-subtitle"}
    TUNE_DIRECTIVES = {"x-tune"}
    THEME_DIRECTIVES = {"x-theme"}
    KEYWORD_DIRECTIVES = {"x-keyword"}
    RECORDING_URL_DIRECTIVES = {"x-recording-url"}
    RECORDING_TITLE_DIRECTIVES = {"x-recording-title"}
    RECORDING_ARTIST_DIRECTIVES = {"x-recording-artist"}

    # Section markers
    VERSE_START = {"start_of_verse", "sov"}
    VERSE_END = {"end_of_verse", "eov"}
    CHORUS_START = {"start_of_chorus", "soc"}
    CHORUS_END = {"end_of_chorus", "eoc"}
    BRIDGE_START = {"start_of_bridge", "sob"}
    BRIDGE_END = {"end_of_bridge", "eob"}
    TAB_START = {"start_of_tab", "sot"}
    TAB_END = {"end_of_tab", "eot"}

    def __init__(self, file_path: Path):
        """Initialize parser with a ChordPro file path."""
        self.file_path = file_path
        self.properties = Properties()
        self.verses: list[Verse] = []
        self.recordings: list[Recording] = []
        self.current_section: str | None = None
        self.current_section_lines: list[str] = []
        self.verse_counter = 1
        self.chorus_counter = 1
        self.bridge_counter = 1
        self.in_tab = False
        self.pending_recording_url: str | None = None
        self.pending_recording_title: str | None = None
        self.pending_recording_artist: str | None = None

    def parse(self) -> Song:
        """Parse the ChordPro file and return a Song object."""
        logger.info("Parsing ChordPro file: %s", self.file_path)

        with open(self.file_path, "r", encoding="utf-8") as f:
            content = f.read()

        lines = content.split("\n")

        for line in lines:
            line = line.strip()

            # Skip empty lines when not in a section
            if not line and not self.current_section:
                continue

            # Check for directives
            if line.startswith("{"):
                self._process_directive(line)
            # Check for lyrics/chords
            elif self.current_section and not self.in_tab:
                self.current_section_lines.append(line)
            elif self.in_tab:
                # Skip tab content
                continue
            elif line and not self.current_section:
                # Lyrics without explicit section - treat as verse
                self._start_section("verse")
                self.current_section_lines.append(line)

        # Close any open section
        if self.current_section:
            self._end_section()

        # Save any pending recording
        if self.pending_recording_url:
            self._save_pending_recording()

        # Use filename as title if no title directive found
        if not self.properties.titles:
            self.properties.titles = [self.file_path.stem.replace("_", " ").title()]

        song = Song(
            properties=self.properties,
            verses=self.verses,
            recordings=self.recordings,
        )

        logger.info(
            "Parsed ChordPro song: %s",
            song.properties.titles[0] if song.properties.titles else "Untitled",
        )
        return song

    def _process_directive(self, line: str) -> None:
        """Process a ChordPro directive line."""
        matches = self.DIRECTIVE_PATTERN.findall(line)
        for directive, value in matches:
            directive = directive.lower().strip()
            value = value.strip() if value else ""

            # Title
            if directive in self.TITLE_DIRECTIVES:
                if value not in self.properties.titles:
                    self.properties.titles.append(value)

            # Subtitle (can be alternate title or author)
            elif directive in self.SUBTITLE_DIRECTIVES:
                # If we have no authors yet, treat as author
                if not self.properties.authors and directive in {"subtitle", "st", "artist"}:
                    self.properties.authors.append(value)
                # Otherwise, treat as alternate title
                elif value not in self.properties.titles:
                    self.properties.titles.append(value)

            # Author/Composer
            elif directive in self.AUTHOR_DIRECTIVES:
                if value not in self.properties.authors:
                    self.properties.authors.append(value)

            # Copyright
            elif directive in self.COPYRIGHT_DIRECTIVES:
                self.properties.copyright = value

            # CCLI
            elif directive in self.CCLI_DIRECTIVES:
                self.properties.ccli_no = value

            # Key (store as keyword for now)
            elif directive in self.KEY_DIRECTIVES:
                if "Key: " + value not in self.properties.keywords:
                    self.properties.keywords.append("Key: " + value)

            # Custom extension directives
            # Alternate titles
            elif directive in self.ALT_TITLE_DIRECTIVES:
                if value not in self.properties.titles:
                    self.properties.titles.append(value)

            # Tune name
            elif directive in self.TUNE_DIRECTIVES:
                self.properties.tune = value

            # Themes (can have multiple)
            elif directive in self.THEME_DIRECTIVES:
                if value not in self.properties.themes:
                    self.properties.themes.append(value)

            # Keywords (can have multiple)
            elif directive in self.KEYWORD_DIRECTIVES:
                if value not in self.properties.keywords:
                    self.properties.keywords.append(value)

            # Recording metadata (can specify multiple parts)
            elif directive in self.RECORDING_URL_DIRECTIVES:
                # If we have a pending recording, save it first
                if self.pending_recording_url:
                    self._save_pending_recording()
                self.pending_recording_url = value

            elif directive in self.RECORDING_TITLE_DIRECTIVES:
                self.pending_recording_title = value

            elif directive in self.RECORDING_ARTIST_DIRECTIVES:
                self.pending_recording_artist = value

            # Section starts
            elif directive in self.VERSE_START:
                self._start_section("verse", value)
            elif directive in self.CHORUS_START:
                self._start_section("chorus", value)
            elif directive in self.BRIDGE_START:
                self._start_section("bridge", value)

            # Section ends
            elif directive in self.VERSE_END:
                self._end_section()
            elif directive in self.CHORUS_END:
                self._end_section()
            elif directive in self.BRIDGE_END:
                self._end_section()

            # Tab sections (ignore content)
            elif directive in self.TAB_START:
                self.in_tab = True
            elif directive in self.TAB_END:
                self.in_tab = False

            # Comment (treat as verse name/label)
            elif directive in {"comment", "c"}:
                # If we're in a section, this is a label
                if self.current_section and value:
                    # Use comment as verse name
                    pass  # We'll handle this when creating the verse

            # URL (legacy recording - just URL)
            elif directive == "url" and value:
                self.recordings.append(Recording(url=value))

    def _save_pending_recording(self) -> None:
        """Save the pending recording data to the recordings list."""
        if self.pending_recording_url:
            recording = Recording(
                url=self.pending_recording_url,
                title=self.pending_recording_title,
                artist=self.pending_recording_artist,
            )
            self.recordings.append(recording)

            # Reset pending state
            self.pending_recording_url = None
            self.pending_recording_title = None
            self.pending_recording_artist = None

    def _start_section(self, section_type: str, label: str = "") -> None:
        """Start a new song section."""
        # Close previous section if any
        if self.current_section:
            self._end_section()

        self.current_section = section_type
        self.current_section_lines = []

    def _end_section(self) -> None:
        """End current section and create a Verse."""
        if not self.current_section:
            return

        # Skip empty sections
        if not self.current_section_lines:
            self.current_section = None
            return

        # Determine verse name and type
        if self.current_section == "verse":
            verse_name = f"v{self.verse_counter}"
            verse_type_str = "verse"
            self.verse_counter += 1
        elif self.current_section == "chorus":
            verse_name = f"c{self.chorus_counter}"
            verse_type_str = "chorus"
            self.chorus_counter += 1
        elif self.current_section == "bridge":
            verse_name = f"b{self.bridge_counter}"
            verse_type_str = "bridge"
            self.bridge_counter += 1
        else:
            verse_name = self.current_section
            verse_type_str = "unknown"

        # Parse lines and extract chords
        verse_lines = self._parse_lines(self.current_section_lines)

        # Import VerseType here to avoid circular import
        from openlyric_bookmaker.models.verse import VerseType

        # Map string to enum
        verse_type_map = {
            "verse": VerseType.VERSE,
            "chorus": VerseType.CHORUS,
            "bridge": VerseType.BRIDGE,
            "unknown": VerseType.UNKNOWN,
        }

        verse = Verse(
            name=verse_name,
            verse_type=verse_type_map.get(verse_type_str, VerseType.UNKNOWN),
            lines=verse_lines,
        )

        self.verses.append(verse)

        # Reset section state
        self.current_section = None
        self.current_section_lines = []

    def _parse_lines(self, raw_lines: list[str]) -> list[Line]:
        """Parse lines with inline chords into Line objects."""
        result_lines = []

        for raw_line in raw_lines:
            if not raw_line.strip():
                # Empty line
                result_lines.append(Line(text="", chords=[]))
                continue

            # Extract chords and text
            chords = []
            text_parts = []
            last_pos = 0

            # Find all chord positions
            for match in self.CHORD_PATTERN.finditer(raw_line):
                chord_notation = match.group(1)
                chord_pos = match.start()

                # Add text before this chord
                text_parts.append(raw_line[last_pos:chord_pos])

                # Calculate position in final text (without chord markers)
                text_before = "".join(text_parts)
                position = len(text_before)

                # Parse chord into root and structure
                chord_root, chord_structure = self._parse_chord_notation(chord_notation)

                chords.append(
                    ChordPosition(
                        position=position,
                        chord_root=chord_root,
                        chord_structure=chord_structure,
                    )
                )
                last_pos = match.end()

            # Add remaining text
            text_parts.append(raw_line[last_pos:])

            # Join text (removes chord markers)
            final_text = "".join(text_parts)

            result_lines.append(Line(text=final_text, chords=chords))

        return result_lines

    def _parse_chord_notation(self, notation: str) -> tuple[str, str | None]:
        """Parse chord notation like 'Dm7' into root and structure.

        Args:
            notation: Chord notation (e.g., 'C', 'Dm', 'G7', 'Cmaj7')

        Returns:
            Tuple of (root, structure) where structure may be None
        """
        # Pattern: root note (C, D, E, F, G, A, B) + optional b/# + structure
        match = re.match(r"^([A-G][b#]?)(.*)$", notation)
        if match:
            root = match.group(1)
            structure = match.group(2) if match.group(2) else None
            return root, structure

        # If parsing fails, treat whole thing as root
        return notation, None
