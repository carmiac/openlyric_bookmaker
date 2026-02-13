"""LaTeX renderer using Jinja2 templates."""

import logging
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from openlyric_bookmaker.models.song import Song

logger = logging.getLogger(__name__)


def latex_escape(text: str) -> str:
    """Escape special LaTeX characters in text.

    Args:
        text: Text to escape

    Returns:
        Escaped text safe for LaTeX
    """
    # Order matters - backslash must be done first, but we handle it differently
    # to avoid double-escaping
    text = text.replace("\\", r"\textbackslash{}")
    # Now handle other special characters
    replacements = {
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }
    for char, replacement in replacements.items():
        text = text.replace(char, replacement)
    return text


class LaTeXRenderer:
    """Renders songs to LaTeX .sbd format using Jinja2 templates."""

    def __init__(self, template_dir: Path | None = None) -> None:
        """Initialize the LaTeX renderer.

        Args:
            template_dir: Directory containing Jinja2 templates.
                         If None, uses built-in templates.
        """
        if template_dir:
            self.env = Environment(
                loader=FileSystemLoader(template_dir),
                block_start_string="\\BLOCK{",
                block_end_string="}",
                variable_start_string="\\VAR{",
                variable_end_string="}",
                comment_start_string="\\#{",
                comment_end_string="}",
                line_statement_prefix="%%",
                line_comment_prefix="%#",
                trim_blocks=True,
                autoescape=False,
            )
        else:
            # Use built-in templates from package
            builtin_templates = Path(__file__).parent.parent / "templates" / "latex"
            self.env = Environment(
                loader=FileSystemLoader(builtin_templates),
                # Use Jinja2 defaults since we're using {{ }} syntax
                trim_blocks=True,
                lstrip_blocks=True,
                autoescape=False,
            )

        # Add LaTeX escape filter
        self.env.filters["latex_escape"] = latex_escape

    def render_song(self, song: Song) -> str:
        """Render a single song to LaTeX .sbd format.

        Args:
            song: The song to render

        Returns:
            LaTeX string for the song
        """
        template = self.env.get_template("song.sbd.j2")
        return template.render(song=song)

    def render_songfile(
        self,
        sections: dict[str, list[Song]],
        song_content: dict[Path, str],
        sbd_header: str = "",
        use_column_switching: bool = True,
    ) -> str:
        """Render the complete songfile containing all songs.

        Args:
            sections: Dict mapping section names to lists of songs
            song_content: Dict mapping song file paths to rendered LaTeX content
            sbd_header: Optional header content (custom LaTeX commands)
            use_column_switching: Whether to use column switching for section headers (default True)

        Returns:
            Complete songfile.sbd content
        """
        template = self.env.get_template("songfile.sbd.j2")
        return template.render(
            sections=sections,
            song_content=song_content,
            sbd_header=sbd_header,
            use_column_switching=use_column_switching,
        )
