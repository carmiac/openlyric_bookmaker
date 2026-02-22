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

    def render_song(self, song: Song, songbook_config: dict | None = None) -> str:
        """Render a single song to HTML.

        Args:
            song: The song to render
            songbook_config: Optional songbook configuration (for edit links, etc.)

        Returns:
            HTML string for the song
        """
        template = self.env.get_template("song.html.j2")
        return template.render(song=song, config=songbook_config or {})

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

    def render_manifest(
        self,
        title: str,
        description: str = "",
        short_title: str | None = None,
        start_url: str | None = None,
    ) -> str:
        """Render the PWA manifest file.

        Args:
            title: Full songbook title
            description: Description of the songbook
            short_title: Short title for app (defaults to title)
            start_url: URL to launch when PWA is opened (defaults to ./index.html)

        Returns:
            JSON string for manifest.json
        """
        template = self.env.get_template("manifest.json.j2")
        return template.render(
            title=title,
            short_title=short_title or title[:12],  # Limit to 12 chars
            description=description or f"{title} songbook",
            start_url=start_url,
        )

    def render_service_worker(self, song_files: list[str]) -> str:
        """Render the service worker with pre-cache list.

        Args:
            song_files: List of song HTML filenames to pre-cache

        Returns:
            JavaScript service worker code
        """
        import datetime

        build_timestamp = datetime.datetime.utcnow().strftime("%Y%m%d%H%M%S")
        template = self.env.get_template("sw.js.j2")
        return template.render(song_files=song_files, build_timestamp=build_timestamp)

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
