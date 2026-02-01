"""HTML renderer using Jinja2 templates."""

import logging
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from openlyric_bookmaker.models.song import Song

logger = logging.getLogger(__name__)


class HTMLRenderer:
    """Renders songs to HTML using Jinja2 templates."""

    def __init__(self, template_dir: Path | None = None) -> None:
        """Initialize the HTML renderer.

        Args:
            template_dir: Directory containing Jinja2 templates.
                         If None, uses built-in templates.
        """
        if template_dir:
            self.env = Environment(loader=FileSystemLoader(template_dir), autoescape=True)
        else:
            # Use built-in templates from package
            builtin_templates = Path(__file__).parent.parent / "templates" / "html"
            self.env = Environment(loader=FileSystemLoader(builtin_templates), autoescape=True)

        # Add custom filters
        self.env.filters["chord_display"] = self._format_chord

    def render_song(self, song: Song) -> str:
        """Render a single song to HTML.

        Args:
            song: The song to render

        Returns:
            HTML string for the song
        """
        template = self.env.get_template("song.html.j2")
        return template.render(song=song)

    def render_index(
        self, title: str, sections: dict[str, list[dict]], songbook_config: dict
    ) -> str:
        """Render the index/navigation page.

        Args:
            title: Songbook title
            sections: Dict mapping section names to lists of song info dicts
            songbook_config: Additional songbook configuration

        Returns:
            HTML string for the index page
        """
        template = self.env.get_template("index.html.j2")
        return template.render(title=title, sections=sections, config=songbook_config)

    def render_introduction(self, intro_text: str, songbook_config: dict) -> str:
        """Render the introduction page.

        Args:
            intro_text: Introduction text
            songbook_config: Songbook configuration

        Returns:
            HTML string for the introduction page
        """
        template = self.env.get_template("introduction.html.j2")
        return template.render(intro=intro_text, config=songbook_config)

    @staticmethod
    def _format_chord(chord_pos: object) -> str:
        """Format a chord for display (Jinja2 filter)."""
        if hasattr(chord_pos, "full_chord"):
            return chord_pos.full_chord
        return str(chord_pos)
