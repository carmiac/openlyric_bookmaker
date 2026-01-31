# Open Lyric Book Maker

A modern Python tool for creating beautiful songbooks in multiple formats (PDF, HTML, EPUB) from songs in the [OpenLyrics](https://github.com/openlyrics/openlyrics/) XML format.

## Features

- 📚 **Multiple output formats**: PDF (bound/display/ereader), HTML with navigation, EPUB (coming soon)
- 🎵 **Rich song metadata**: Titles, authors, CCLI numbers, copyright, themes, alternate titles
- 🎸 **Chord support**: Display guitar/ukulele chords with lyrics
- 📑 **Automatic indices**: Table of contents, author index with configurable sorting
- 🎨 **Customizable templates**: Jinja2-based templates for full control
- 📱 **Responsive HTML**: Mobile-friendly navigation with sticky section headers
- 🎬 **Recording metadata**: Built-in support for linking audio/video recordings (YouTube, etc.)
- 📖 **Section support**: Organize songs into themed sections
- 🔍 **Type-safe**: Full type hints throughout codebase

## Installation

### From Source

```bash
git clone https://github.com/yourusername/openlyric_bookmaker.git
cd openlyric_bookmaker
pip install -e .
```

### Requirements

- Python 3.10+
- LaTeX distribution (TeX Live, MiKTeX) for PDF output
  - Required packages: `songs`, `geometry`, `fancyhdr`, `titleidx`, `multicol`
- Modern web browser for HTML output

## Quick Start

```bash
# Create a songbook from example songs
openlyric_bookmaker --config examples/example_config.toml

# Or specify custom paths
openlyric_bookmaker --config mybook.toml --input songs/ --output output/

# Build only specific formats
openlyric_bookmaker --config mybook.toml --formats html bound_pdf
```

## Usage

### Command Line Options

```
openlyric_bookmaker [OPTIONS]

Options:
  --config PATH      Configuration file (default: book_config.toml)
  --input DIR        Input directory with .xml songs (default: songs/)
  --output DIR       Output directory (default: output/)
  --formats FORMATS  Comma-separated format names or 'all' (default: all)
  --help            Show this help message
```

### Configuration File

The tool uses TOML configuration files. See [examples/example_config.toml](examples/example_config.toml) for a complete example.

**Basic structure:**

```toml
[general]
title = "My Songbook"
subtitle = "A Collection of Songs"
author = "Editor Name"
sections_file = "sections.toml"

[html]
enabled = true
template = "html/index.html.j2"
introduction = "intro.html"

[bound_pdf]
enabled = true
template = "latex/songbook.tex.j2"
paper = "letterpaper"
columns = 2
songs_index = true
```

**Multiple PDF formats:**

You can define multiple PDF outputs with different settings (e.g., one for printing, one for screen viewing):

```toml
[bound_pdf]
enabled = true
paper = "letterpaper"
two_sided = true
columns = 2
inner_margin = "4cm"
outer_margin = "2cm"

[display_pdf]
enabled = true
paper = "letterpaper"
two_sided = false
columns = 2
left_margin = "3cm"
right_margin = "3cm"

[ereader_pdf]
enabled = true
template = "latex/songbook_ereader.tex.j2"
paper = "a5paper"
font_size = "14pt"
columns = 1
lyric_mode = true  # Hide chords for simpler display
```

### Song Format

Songs must be in OpenLyrics XML format. Example:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<song xmlns="http://openlyrics.info/namespace/2009/song" 
      xml:lang="en" 
      createdIn="OpenLP 2.4.6">
  <properties>
    <titles>
      <title>Amazing Grace</title>
      <title lang="en">How Sweet the Sound</title>
    </titles>
    <authors>
      <author>John Newton</author>
    </authors>
    <copyright>Public Domain</copyright>
    <ccliNo>22025</ccliNo>
  </properties>
  <lyrics>
    <verse name="v1">
      <lines>
        <line><chord name="G"/>Amazing <chord name="C"/>grace...</line>
      </lines>
    </verse>
    <verse name="c" type="chorus">
      <lines>
        <line>Saved a wretch like me</line>
      </lines>
    </verse>
  </lyrics>
</song>
```

### Sections File

Organize songs into sections:

```toml
[[section]]
name = "Traditional Songs"
files = ["amazing_grace.xml", "swing_low.xml"]

[[section]]
name = "Modern Worship"
files = ["how_great.xml", "cornerstone.xml"]
```

## Architecture

The tool follows a clean separation of concerns:

```
XML Files → Parser → Data Models → Renderer → Output Files
                                      ↓
                                  Compiler (PDF only)
```

### Components

- **Parsers** (`parsers/`): Convert OpenLyrics XML to Python data models
- **Models** (`models/`): Type-safe dataclasses for songs, verses, chords
- **Renderers** (`renderers/`): Generate format-specific output using Jinja2 templates
- **Compilers** (`compilers/`): Post-process rendered output (e.g., run pdflatex)
- **Builder** (`builder.py`): Orchestrates the entire build process

### Data Flow

1. **Parse**: OpenLyrics XML → `Song` objects with full metadata
2. **Render**: `Song` objects → LaTeX/HTML via Jinja2 templates
3. **Compile**: LaTeX files → PDF via pdflatex (two-pass for indices)
4. **Output**: Final PDFs, HTML site, or EPUB

## OpenLyrics Extensions

This tool extends OpenLyrics with additional metadata:

### Recordings

Link to audio/video recordings:

```xml
<properties>
  <recordings>
    <recording>
      <title>Live Performance</title>
      <artist>Original Artist</artist>
      <url>https://www.youtube.com/watch?v=...</url>
    </recording>
  </recordings>
</properties>
```

## Development

### Project Structure

```
openlyric_bookmaker/
├── src/openlyric_bookmaker/
│   ├── models/          # Data models (Song, Verse, Chord)
│   ├── parsers/         # XML → models
│   ├── renderers/       # models → LaTeX/HTML
│   ├── compilers/       # Post-processing (pdflatex, etc.)
│   ├── templates/       # Jinja2 templates
│   ├── builder.py       # Build orchestrator
│   ├── config.py        # Config loading
│   └── cli.py           # Command-line interface
├── tests/               # Unit & integration tests
└── examples/            # Example configs & songs
```

### Running Tests

```bash
# Install development dependencies
pip install -e ".[dev]"

# Run all tests
pytest

# Run with coverage
pytest --cov=openlyric_bookmaker
```

## Migration from Legacy Script

If you're using the old `ol_bookmaker.py` script:

1. **Config file**: Rename `config.yaml` → `book_config.toml` (same format)
2. **Command**: Replace `python ol_bookmaker.py` → `openlyric_bookmaker`
3. **Options**: Same CLI options work (--config, --input, --output, --formats)

The legacy script is still available but deprecated. New projects should use the package.

## Examples

See the [examples/](examples/) directory for:

- `example_config.toml` - Comprehensive configuration with all options
- `tex/` - Example LaTeX templates
- Test songbook builds

Real-world example: [SwillingSwedesSongbook](https://github.com/carmiac/SwillingSwedesSongbook) (349 songs)

## Contributing

Contributions welcome! Areas needing help:

- EPUB output support (tex4ebook integration)
- Media player UI for recordings
- Additional LaTeX templates
- Unit tests for edge cases

## License

[Your License Here]

## Changelog

### v2.0.0 (2026-01-31)

Complete rewrite with modern Python architecture:

- ✨ New package structure with proper separation of concerns
- ✨ Jinja2 templates replace string concatenation
- ✨ Full type hints throughout
- ✨ Multiple PDF format support (bound, display, ereader)
- ✨ Sticky section headers in HTML navigation
- ✨ Two-pass PDF compilation for indices
- ✨ Table of contents with alternate titles
- ✨ Improved section handling in multi-column layouts
- 🐛 Fixed song numbering (now starts at 1)
- 🐛 Fixed blank pages between songs
- 🐛 Fixed author index generation
- 📦 Modern packaging with pyproject.toml
- 🧪 Test infrastructure ready

### v1.0.0 (Original)

- Initial monolithic script (`ol_bookmaker.py`)
- Basic PDF and HTML output
