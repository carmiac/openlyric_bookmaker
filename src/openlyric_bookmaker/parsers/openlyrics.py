"""Parser for OpenLyrics XML format."""

import logging
import xml.etree.ElementTree as ET
from pathlib import Path

from openlyric_bookmaker.models.song import Song, Properties, Recording
from openlyric_bookmaker.models.verse import Verse, Line, Chord, ChordPosition, VerseType

logger = logging.getLogger(__name__)

# OpenLyrics namespace
OPENLYRICS_NS = "http://openlyrics.info/namespace/2009/song"
NS = {"ol": OPENLYRICS_NS}


class OpenLyricsParser:
    """Parser for OpenLyrics XML files."""

    @staticmethod
    def parse_file(file_path: Path) -> Song:
        """Parse an OpenLyrics XML file into a Song object."""
        with open(file_path, "r", encoding="utf-8") as f:
            xml_content = f.read()
        song = OpenLyricsParser.parse_string(xml_content)
        song.source_file = file_path
        return song

    @staticmethod
    def parse_string(xml_string: str) -> Song:
        """Parse an OpenLyrics XML string into a Song object."""
        xml_bytes = xml_string.encode("utf-8")
        root = ET.fromstring(xml_bytes)

        properties = OpenLyricsParser._parse_properties(root)
        verses = OpenLyricsParser._parse_verses(root)
        recordings = OpenLyricsParser._parse_recordings(root)
        comments = OpenLyricsParser._parse_top_level_comments(root)

        return Song(
            properties=properties,
            verses=verses,
            recordings=recordings,
            comments=comments,
        )

    @staticmethod
    def _parse_properties(root: ET.Element) -> Properties:
        """Parse song properties from XML."""
        props_elem = root.find(".//ol:properties", NS)
        if props_elem is None:
            logger.warning("No properties found in song")
            return Properties()

        properties = Properties()

        # Parse titles
        titles_elem = props_elem.find("ol:titles", NS)
        if titles_elem is not None:
            properties.titles = [
                title.text for title in titles_elem.findall("ol:title", NS) if title.text
            ]

        # Parse authors
        authors_elem = props_elem.find("ol:authors", NS)
        if authors_elem is not None:
            properties.authors = [
                author.text for author in authors_elem.findall("ol:author", NS) if author.text
            ]

        # Parse keywords
        keywords_elem = props_elem.find("ol:keywords", NS)
        if keywords_elem is not None:
            properties.keywords = [
                kw.text for kw in keywords_elem.findall("ol:keyword", NS) if kw.text
            ]

        # Parse themes
        themes_elem = props_elem.find("ol:themes", NS)
        if themes_elem is not None:
            properties.themes = [
                theme.text for theme in themes_elem.findall("ol:theme", NS) if theme.text
            ]

        # Parse single-value properties
        copyright_elem = props_elem.find("ol:copyright", NS)
        if copyright_elem is not None and copyright_elem.text:
            properties.copyright = copyright_elem.text

        ccli_elem = props_elem.find("ol:ccliNo", NS)
        if ccli_elem is not None and ccli_elem.text:
            properties.ccli_no = ccli_elem.text

        # Parse verse order
        verse_order_elem = props_elem.find("ol:verseOrder", NS)
        if verse_order_elem is not None and verse_order_elem.text:
            properties.verse_order = verse_order_elem.text.split()

        # Parse custom "tune" extension (not standard OpenLyrics)
        tune_elem = props_elem.find("ol:tune", NS)
        if tune_elem is not None and tune_elem.text:
            properties.tune = tune_elem.text

        return properties

    @staticmethod
    def _parse_verses(root: ET.Element) -> list[Verse]:
        """Parse all verses from XML."""
        verses = []
        lyrics_elem = root.find(".//ol:lyrics", NS)
        if lyrics_elem is None:
            logger.warning("No lyrics found in song")
            return verses

        for verse_elem in lyrics_elem.findall("ol:verse", NS):
            verse = OpenLyricsParser._parse_verse(verse_elem)
            if verse:
                verses.append(verse)

        return verses

    @staticmethod
    def _parse_verse(verse_elem: ET.Element) -> Verse | None:
        """Parse a single verse element."""
        name = verse_elem.get("name", "")
        if not name:
            logger.warning("Verse without name attribute")
            return None

        # Determine verse type from name
        verse_type = OpenLyricsParser._determine_verse_type(name)

        lines = []
        lines_elem = verse_elem.find("ol:lines", NS)
        if lines_elem is not None:
            lines = OpenLyricsParser._parse_lines(lines_elem)

        return Verse(name=name, verse_type=verse_type, lines=lines)

    @staticmethod
    def _determine_verse_type(name: str) -> VerseType:
        """Determine verse type from its name."""
        name_lower = name.lower()
        if name_lower.startswith("c"):
            return VerseType.CHORUS
        elif name_lower.startswith("v"):
            return VerseType.VERSE
        elif name_lower.startswith("b"):
            return VerseType.BRIDGE
        elif name_lower.startswith("p"):
            return VerseType.PRECHORUS
        elif name_lower.startswith("e"):
            return VerseType.ENDING
        elif name_lower.startswith("i"):
            return VerseType.INTRO
        elif name_lower.startswith("o"):
            return VerseType.OUTRO
        elif name_lower.startswith("t"):
            return VerseType.TAG
        else:
            return VerseType.UNKNOWN

    @staticmethod
    def _parse_lines(lines_elem: ET.Element) -> list[Line]:
        """Parse lines from a lines element."""
        lines = []
        current_text = lines_elem.text or ""
        current_chords: list[ChordPosition] = []
        current_comment: str | None = None

        for child in lines_elem:
            tag = OpenLyricsParser._strip_namespace(child.tag)

            if tag == "br":
                # Line break - save current line and start new one
                if current_text.strip() or current_chords:
                    # Strip leading whitespace and adjust chord positions
                    stripped_text = current_text.lstrip()
                    offset = len(current_text) - len(stripped_text)
                    adjusted_chords = [
                        ChordPosition(
                            position=max(0, c.position - offset),
                            chord_root=c.chord_root,
                            chord_structure=c.chord_structure,
                        )
                        for c in current_chords
                    ]
                    
                    lines.append(
                        Line(
                            text=stripped_text.rstrip(),
                            chords=adjusted_chords,
                            comment=current_comment,
                        )
                    )
                current_text = child.tail or ""
                current_chords = []
                current_comment = None

            elif tag == "chord":
                # Chord notation
                position = len(current_text)
                root = child.get("root", "")
                structure = child.get("structure")

                if root:
                    current_chords.append(
                        ChordPosition(position=position, chord_root=root, chord_structure=structure)
                    )

                if child.tail:
                    current_text += child.tail

            elif tag == "comment":
                # Inline comment
                if child.text:
                    current_comment = child.text
                if child.tail:
                    current_text += child.tail

            else:
                # Unknown tag - just get the text
                if child.text:
                    current_text += child.text
                if child.tail:
                    current_text += child.tail

        # Add final line if any content
        if current_text.strip() or current_chords:
            # Strip leading whitespace and adjust chord positions
            stripped_text = current_text.lstrip()
            offset = len(current_text) - len(stripped_text)
            adjusted_chords = [
                ChordPosition(
                    position=max(0, c.position - offset),
                    chord_root=c.chord_root,
                    chord_structure=c.chord_structure,
                )
                for c in current_chords
            ]
            
            lines.append(
                Line(text=stripped_text.rstrip(), chords=adjusted_chords, comment=current_comment)
            )

        return lines

    @staticmethod
    def _parse_recordings(root: ET.Element) -> list[Recording]:
        """Parse recording metadata (custom extension)."""
        recordings = []
        # Look for recordings in properties (custom extension)
        props_elem = root.find(".//ol:properties", NS)
        if props_elem is not None:
            recordings_elem = props_elem.find("ol:recordings", NS)
            if recordings_elem is not None:
                for rec_elem in recordings_elem.findall("ol:recording", NS):
                    url_elem = rec_elem.find("ol:url", NS)
                    if url_elem is not None and url_elem.text:
                        title_elem = rec_elem.find("ol:title", NS)
                        artist_elem = rec_elem.find("ol:artist", NS)

                        recordings.append(
                            Recording(
                                url=url_elem.text,
                                title=title_elem.text if title_elem is not None else None,
                                artist=artist_elem.text if artist_elem is not None else None,
                            )
                        )

        return recordings

    @staticmethod
    def _parse_top_level_comments(root: ET.Element) -> list[str]:
        """Parse comments that appear before the first verse."""
        comments = []
        # Look for comment elements directly under song root
        for child in root:
            tag = OpenLyricsParser._strip_namespace(child.tag)
            if tag == "comment" and child.text:
                comments.append(child.text)
            elif tag == "lyrics":
                # Stop when we hit lyrics section
                break

        return comments

    @staticmethod
    def _strip_namespace(tag: str) -> str:
        """Remove namespace from an XML tag."""
        if "}" in tag:
            return tag.split("}", 1)[1]
        return tag
