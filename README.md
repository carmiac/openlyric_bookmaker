# Open Lyric Book Maker

A modern Python tool for creating beautiful songbooks in multiple formats (PDF, HTML, EPUB) from songs in **OpenLyrics XML** or **ChordPro** format.

## Features

- **Multiple output formats**: PDF (bound/display/ereader), static HTML, progressive web app
- **Multiple input formats**: OpenLyrics XML and ChordPro (.cho, .chordpro, .crd)
- **Rich song metadata**: Titles, authors, CCLI numbers, copyright, themes, alternate titles
- **Chord support**: Display guitar/ukulele chords with lyrics
- **Automatic indices**: Table of contents, author index with configurable sorting
- **Customizable templates**: Jinja2-based templates for full control
- **Responsive HTML**: Mobile-friendly navigation with sticky section headers, dark mode
- **Media player**: Built-in support for linking audio/video recordings (YouTube, audio files)
- **Print-optimized**: CSS print styles for clean two-column printed output
- **Search**: Real-time search by title, author in HTML output
- **Section support**: Organize songs into themed sections

## Supported Song Formats

### ChordPro (Easy to Write)

Simple text-based format with inline chords. Perfect for quick song entry and editing:

```
{title: Amazing Grace}
{x-alt-title: How Sweet the Sound}
{artist: John Newton}
{copyright: Public Domain}
{ccli: 22025}
{key: D}
{x-tune: NEW BRITAIN}
{x-theme: Traditional}
{x-theme: Hymns}
{x-recording-url: https://youtube.com/watch?v=xyz}
{x-recording-title: Live Performance}
{x-recording-artist: Mormon Tabernacle Choir}

{start_of_verse}
Amazing [D]grace how [G]sweet the [D]sound
That saved a wretch like [A]me
{end_of_verse}
```

**Standard directives:** `{title}`, `{artist}`, `{composer}`, `{copyright}`, `{ccli}`, `{key}`

**Custom extensions (x- prefix) for full metadata:**

- `{x-alt-title}` - Alternate titles
- `{x-tune}` - Traditional tune names
- `{x-theme}` - Song themes (can have multiple)
- `{x-keyword}` - Keywords/tags (can have multiple)
- `{x-recording-url/title/artist}` - Rich recording metadata

Supported file extensions: `.cho`, `.chordpro`, `.chopro`, `.crd`

### OpenLyrics XML (Structured)

Standard XML format with rich metadata support:

```xml
<song xmlns="http://openlyrics.info/namespace/2009/song">
  <properties>
    <titles><title>Amazing Grace</title></titles>
  </properties>
  <lyrics>
    <verse name="v1">
      <lines>Amazing <chord root="D"/>grace...</lines>
    </verse>
  </lyrics>
</song>
```

**The tool automatically detects the format** based on file extension!

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

### Song Edit Suggestions

Enable users to suggest corrections and edits to songs by adding these optional config fields to your `[songbook]` section:

```toml
[songbook]
title = "My Songbook"
# ... other fields ...
edit_github_repo = "username/repository"  # Enables "Suggest Edit (GitHub)" button
edit_email = "corrections@example.com"     # Enables "Email Correction" button
```

**GitHub Issue Button** (`edit_github_repo`):
- Creates a pre-filled GitHub issue with song title and filename
- Requires users to have a GitHub account
- Best for tracking and managing suggestions

**Email Button** (`edit_email`):
- Opens default email client with pre-filled subject and body
- No account required - accessible to everyone
- Good fallback for non-technical users

Both buttons appear on each song page. You can enable one, both, or neither. The buttons are automatically hidden when printing.

