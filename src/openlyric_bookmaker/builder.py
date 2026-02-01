"""Main builder class that orchestrates songbook creation."""

import logging
import shutil
from pathlib import Path

from openlyric_bookmaker.config import get_file_list, load_config
from openlyric_bookmaker.parsers.openlyrics import OpenLyricsParser
from openlyric_bookmaker.renderers.html import HTMLRenderer
from openlyric_bookmaker.renderers.latex import LaTeXRenderer
from openlyric_bookmaker.compilers.pdf import PDFCompiler

logger = logging.getLogger(__name__)


class SongBookBuilder:
    """Builds songbooks from OpenLyrics XML files."""

    def __init__(
        self,
        config_path: Path,
        output_dir: Path | None = None,
        base_path: Path | None = None,
        clean: bool = False,
    ) -> None:
        """Initialize the songbook builder.

        Args:
            config_path: Path to TOML configuration file
            output_dir: Override output directory from config
            base_path: Base path for resolving relative paths (defaults to config file dir)
            clean: Whether to clean output directories before building
        """
        self.config = load_config(config_path)
        self.config_path = config_path
        self.base_path = base_path or config_path.parent
        self.output_dir = Path(output_dir) if output_dir else self.base_path / "output"
        self.clean = clean

        logger.info(f"Initialized SongBookBuilder with config: {config_path}")
        logger.info(f"Base path: {self.base_path}")
        logger.info(f"Output directory: {self.output_dir}")

    def build(self) -> None:
        """Build all configured output formats."""
        if self.clean:
            self._clean_output()

        # Parse all songs organized by section
        sections = self._parse_sections()

        # Build each output format
        for format_name, format_config in self.config["output_formats"].items():
            logger.info(f"Building output format: {format_name}")

            format_type = format_config["type"]
            if format_type == "html":
                self._build_html(format_name, format_config, sections)
            elif format_type == "pdf":
                self._build_pdf(format_name, format_config, sections)
            elif format_type == "epub":
                logger.warning(f"EPUB output not yet implemented, skipping {format_name}")

        logger.info("Build complete!")

    def _clean_output(self) -> None:
        """Clean output and build directories."""
        logger.info("Cleaning output directories")
        if self.output_dir.exists():
            shutil.rmtree(self.output_dir)

        build_dir = self.base_path / "build"
        if build_dir.exists():
            shutil.rmtree(build_dir)

    def _parse_sections(self) -> dict[str, list]:
        """Parse all songs organized by sections.

        Returns:
            Dictionary mapping section names to lists of parsed Song objects
        """
        sections = {}
        parser = OpenLyricsParser()

        for section_name, section_config in self.config["sections"].items():
            logger.info(f"Parsing section: {section_name}")

            # Get list of files for this section
            file_patterns = section_config.get("files", [])
            files = get_file_list(file_patterns, self.base_path)

            # Sort files if requested
            if section_config.get("sort") == "filename":
                files.sort(key=lambda f: f.name)

            # Parse each file
            songs = []
            for file_path in files:
                try:
                    logger.debug(f"Parsing {file_path}")
                    song = parser.parse_file(file_path)
                    
                    # Validate song
                    errors = song.validate()
                    if errors:
                        logger.warning(f"Validation errors in {file_path}: {errors}")
                    
                    songs.append(song)
                except Exception as e:
                    logger.error(f"Error parsing {file_path}: {e}")

            sections[section_name] = songs
            logger.info(f"Parsed {len(songs)} songs in section {section_name}")

        return sections

    def _build_html(
        self, format_name: str, format_config: dict, sections: dict[str, list]
    ) -> None:
        """Build HTML output.

        Args:
            format_name: Name of this output format
            format_config: Configuration for this format
            sections: Parsed songs organized by section
        """
        output_dir = self.output_dir / format_config["output_dir"]
        output_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Creating HTML output in {output_dir}")

        # Initialize renderer
        template_dir = format_config.get("template_dir")
        if template_dir:
            template_path = self.base_path / template_dir
            # Only use custom templates if they actually exist
            if template_path.exists():
                renderer = HTMLRenderer(template_path)
            else:
                logger.warning(f"Template directory not found: {template_path}, using built-in templates")
                renderer = HTMLRenderer()
        else:
            renderer = HTMLRenderer()

        # Copy stylesheets
        if "stylesheets" in format_config:
            for stylesheet_path in format_config["stylesheets"]:
                src = self.base_path / stylesheet_path
                if src.is_dir():
                    dest = output_dir / src.name
                    if dest.exists():
                        shutil.rmtree(dest)
                    shutil.copytree(src, dest)
                    logger.debug(f"Copied stylesheet directory: {src} -> {dest}")
                elif src.is_file():
                    dest = output_dir / src.name
                    shutil.copy(src, dest)
                    logger.debug(f"Copied stylesheet: {src} -> {dest}")

        # Copy images
        if "image_dir" in format_config:
            src = self.base_path / format_config["image_dir"]
            if src.exists():
                dest = output_dir / format_config["image_dir"]
                if dest.exists():
                    shutil.rmtree(dest)
                shutil.copytree(src, dest)
                logger.debug(f"Copied images: {src} -> {dest}")

        # Create songs directory
        songs_dir = output_dir / "songs"
        songs_dir.mkdir(exist_ok=True)

        # Render each song and build section index
        section_index = {}
        for section_name, songs in sections.items():
            song_list = []
            for song in songs:
                # Render song to HTML
                html = renderer.render_song(song)
                
                # Write to file
                song_filename = f"{song.source_file.stem}.html"
                song_path = songs_dir / song_filename
                song_path.write_text(html, encoding="utf-8")
                
                # Add to section index
                song_list.append({
                    "title": song.title,
                    "file": song.source_file,
                    "output_file": f"songs/{song_filename}",
                    "authors": song.properties.authors,
                    "alternate_titles": song.properties.titles[1:] if len(song.properties.titles) > 1 else [],
                })

            section_index[section_name] = song_list

        # Render index page
        index_html = renderer.render_index(
            self.config["songbook"]["title"],
            section_index,
            self.config["songbook"],
        )
        (output_dir / "index.html").write_text(index_html, encoding="utf-8")

        # Render introduction page
        intro_text = self.config["songbook"].get("intro_blurb", "")
        intro_html = renderer.render_introduction(intro_text, self.config["songbook"])
        (output_dir / "introduction.html").write_text(intro_html, encoding="utf-8")

        logger.info(f"HTML build complete: {len(sum(sections.values(), []))} songs rendered")

    def _build_pdf(
        self, format_name: str, format_config: dict, sections: dict[str, list]
    ) -> None:
        """Build PDF output.

        Args:
            format_name: Name of this output format
            format_config: Configuration for this format
            sections: Parsed songs organized by section
        """
        output_dir = self.output_dir / format_config["output_dir"]
        output_dir.mkdir(parents=True, exist_ok=True)
        build_dir = self.base_path / "build" / format_config["output_dir"]
        build_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Creating PDF output in {output_dir}")

        # Initialize renderer
        renderer = LaTeXRenderer()

        # Render each song to LaTeX
        song_content = {}
        for section_songs in sections.values():
            for song in section_songs:
                latex = renderer.render_song(song)
                song_content[song.source_file] = latex

        # Get sbd_header from render_variables if present
        sbd_header = ""
        if "render_variables" in format_config:
            sbd_header = format_config["render_variables"].get("sbd_header", "")

        # Determine if we should use column switching for sections
        # Disable for ereader templates which use single column
        songbook_template = format_config.get("songbook_template", "")
        use_column_switching = "ereader" not in songbook_template.lower()

        # Render the complete songfile
        songfile_content = renderer.render_songfile(
            sections, song_content, sbd_header, use_column_switching
        )
        songfile_path = build_dir / "songfile.sbd"
        songfile_path.write_text(songfile_content, encoding="utf-8")
        logger.debug(f"Wrote songfile: {songfile_path}")

        # Copy template files to build directory
        template_dir = format_config.get("template_dir")
        if template_dir:
            template_path = self.base_path / template_dir
            if template_path.exists():
                for template_file in template_path.glob("*.tex"):
                    # Render Jinja2 templates
                    from jinja2 import Environment, FileSystemLoader
                    env = Environment(
                        loader=FileSystemLoader(template_path),
                        trim_blocks=True,
                        lstrip_blocks=True,
                        autoescape=False,
                    )
                    template = env.get_template(template_file.name)
                    
                    # Prepare template variables
                    template_vars = (
                        format_config.get("render_variables", {})
                        | self.config["songbook"]
                        | {"sections": list(sections.keys())}
                    )
                    
                    rendered = template.render(**template_vars)
                    (build_dir / template_file.name).write_text(rendered, encoding="utf-8")
                    logger.debug(f"Rendered template: {template_file.name}")

        # Copy style file
        if "songbook_style" in format_config:
            src = self.base_path / format_config["songbook_style"]
            if src.exists():
                shutil.copy(src, build_dir)
                logger.debug(f"Copied style file: {src}")

        # Copy images
        if "image_dir" in format_config:
            src = self.base_path / format_config["image_dir"]
            if src.exists():
                dest = build_dir / format_config["image_dir"]
                if dest.exists():
                    shutil.rmtree(dest)
                shutil.copytree(src, dest)
                logger.debug(f"Copied images: {src} -> {dest}")

        # Compile PDF
        output_filename = format_config.get("output_file", "songbook")
        main_tex = format_config.get("songbook_template", "songbook.tex")
        
        compiler = PDFCompiler(build_dir)
        try:
            pdf_path = compiler.compile(main_tex, output_filename, runs=2)
            
            # Copy to output directory
            shutil.copy(pdf_path, output_dir)
            logger.info(f"✓ PDF build complete: {output_dir / pdf_path.name}")
        except RuntimeError as e:
            logger.error(f"PDF compilation failed: {e}")
            raise
