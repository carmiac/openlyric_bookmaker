# OpenLyric Bookmaker Architecture

This document describes the internal architecture of the openlyric_bookmaker package.

## Overview

The package follows a pipeline architecture with clear separation of concerns:

```
Input (XML) → Parser → Data Models → Renderer → Output (LaTeX/HTML)
                                        ↓
                                    Compiler (optional)
                                        ↓
                                  Final Output (PDF/EPUB)
```

## Core Components

### 1. Data Models (`models/`)

**Purpose**: Type-safe representations of songs, verses, and metadata.

**Files**:
- `song.py`: `Song`, `SongProperties`, `SongRecording`
- `verse.py`: `Verse`, `Chord`, `ChordLine`

**Key Design Decisions**:
- Use `@dataclass` for simplicity (not Pydantic) to avoid extra dependencies
- Full type hints for IDE support and type checking
- Immutable where possible (use `frozen=True` for dataclasses)
- Separate concerns: `SongProperties` handles metadata, `Verse` handles lyrics

**Example**:
```python
@dataclass
class Song:
    """Represents a complete song with metadata and lyrics."""
    xml_file: Path
    properties: SongProperties
    verses: list[Verse]
    
@dataclass
class Verse:
    """A single verse, chorus, or bridge."""
    name: str          # e.g., "v1", "c", "b1"
    type: str          # e.g., "verse", "chorus", "bridge"
    lines: list[ChordLine]
```

### 2. Parsers (`parsers/`)

**Purpose**: Convert XML files into data models.

**Files**:
- `openlyrics.py`: `OpenLyricsParser`

**Responsibilities**:
1. Parse OpenLyrics XML (with namespace handling)
2. Extract song properties (titles, authors, CCLI, etc.)
3. Parse lyrics with chord positions
4. Handle alternate titles
5. Extract recordings metadata
6. Validate required fields

**Key Methods**:
```python
class OpenLyricsParser:
    def parse(self, xml_path: Path) -> Song:
        """Parse an OpenLyrics XML file into a Song object."""
        
    def _parse_properties(self, root: Element) -> SongProperties:
        """Extract metadata from <properties> tag."""
        
    def _parse_verse(self, verse_elem: Element) -> Verse:
        """Parse a single verse with chords."""
```

**Chord Parsing**:
The parser handles inline chords like this:
```xml
<line><chord name="G"/>Amazing <chord name="C"/>grace</line>
```

It tracks chord positions relative to text, creating `ChordLine` objects that know both the text and where chords should appear.

### 3. Renderers (`renderers/`)

**Purpose**: Generate format-specific output from data models using templates.

**Files**:
- `base.py`: `BaseRenderer` (abstract base class)
- `latex.py`: `LaTeXRenderer` 
- `html.py`: `HTMLRenderer`

**Key Design**:
- Use Jinja2 templates (no string concatenation)
- Templates in `templates/latex/` and `templates/html/`
- Renderers are stateless (pure functions)
- Return strings (caller handles file I/O)

**Example**:
```python
class LaTeXRenderer(BaseRenderer):
    def render_song(self, song: Song) -> str:
        """Render a single song to LaTeX (.sbd format)."""
        template = self.env.get_template("latex/song.sbd.j2")
        return template.render(song=song)
        
    def render_songfile(self, songs: list[Song], section_name: str) -> str:
        """Render a section file with multiple songs."""
        template = self.env.get_template("latex/songfile.sbd.j2")
        return template.render(songs=songs, section_name=section_name)
```

**Template Variables**:
Templates receive full `Song` objects and can access all fields:
```jinja2
{% for verse in song.verses %}
  \beginverse
  {% for line in verse.lines %}
    {{ line.text }}
  {% endfor %}
  \endverse
{% endfor %}
```

### 4. Templates (`templates/`)

**Purpose**: Jinja2 templates for rendering output.

**Structure**:
```
templates/
├── latex/
│   ├── song.sbd.j2           # Single song
│   ├── songfile.sbd.j2       # Section file (multiple songs)
│   ├── songbook.tex.j2       # Main LaTeX document
│   └── songbook_ereader.tex.j2  # eReader-optimized version
└── html/
    ├── index.html.j2         # Main page with navigation
    ├── song.html.j2          # Single song page
    └── introduction.html.j2  # Intro/about page
```

**LaTeX Template Challenges**:

1. **Chord Positioning**: Chords must appear above specific characters
   ```jinja2
   {% set ns = namespace(prev_pos=0) %}
   {% for chord in line.chords %}
     {% if chord.position > ns.prev_pos %}
       {{ line.text[ns.prev_pos:chord.position] }}
     {% endif %}
     \[{{ chord.name }}]
     {% set ns.prev_pos = chord.position %}
   {% endfor %}
   ```

2. **Jinja2 Scoping**: Can't reassign loop variables, use `namespace()` instead

3. **Column Switching**: Must handle section breaks differently for 1-column vs 2-column layouts
   ```jinja2
   {% if use_column_switching %}
     \songcolumns{1}
     \clearpage
     {Section header}
     \songcolumns{2}
   {% else %}
     \end{songs}
     {Section header}
     \begin{songs}{...}
   {% endif %}
   ```

### 5. Compilers (`compilers/`)

**Purpose**: Post-process rendered output into final formats.

**Files**:
- `pdf.py`: `PDFCompiler`
- (Future: `epub.py`: `EPUBCompiler`)

**PDFCompiler Workflow**:

The PDF compiler handles LaTeX compilation with a **two-pass process** for indices:

```python
class PDFCompiler:
    def compile(self, tex_file: Path, output_dir: Path) -> Path:
        """Compile LaTeX to PDF with index generation."""
        
        # Pass 1: Generate index files (.sxd)
        self._run_pdflatex(tex_file, output_dir)
        
        # Generate .sbx files from .sxd
        self._generate_indices(output_dir)
        
        # Pass 2: Compile with indices
        return self._run_pdflatex(tex_file, output_dir)
```

**Index Generation**:
1. First pdflatex run creates `.sxd` files (raw index data)
2. Custom Python code parses `.sxd` and generates `.sbx` files (formatted indices)
3. Second pdflatex run includes the formatted indices

**Why Two Passes?**
The LaTeX `songs` package creates index entries during compilation, but the formatted index must be available during the same compilation. Solution: compile twice.

### 6. Builder (`builder.py`)

**Purpose**: Orchestrate the entire build process.

**Key Class**: `SongBookBuilder`

**Workflow**:
```python
def build(self):
    """Build all enabled output formats."""
    
    # 1. Load configuration
    config = self._load_config()
    
    # 2. Parse all songs
    songs = self._parse_songs()
    
    # 3. For each output format:
    for format_name in enabled_formats:
        # a. Render songs with appropriate renderer
        renderer = self._get_renderer(format_name)
        output = renderer.render(songs)
        
        # b. Run compiler if needed (PDF)
        if needs_compilation:
            compiler = self._get_compiler(format_name)
            compiler.compile(output)
            
        # c. Copy assets (images, CSS)
        self._copy_assets()
```

**Format Detection**:
The builder detects format types by name:
- Names ending in `_pdf` → LaTeXRenderer + PDFCompiler
- Names starting with `html` → HTMLRenderer
- Names ending in `_epub` → EPUBRenderer + EPUBCompiler (future)

**Special Handling**:
- **eReader PDFs**: Detected by template name containing "ereader"
  - Disables column switching (single column mode)
  - Uses different section break logic
  - Adjusts `songpos` setting (allow page breaks in verses)

### 7. Configuration (`config.py`)

**Purpose**: Load and validate TOML configuration files.

**Key Functions**:
```python
def load_config(config_path: Path) -> dict:
    """Load TOML config file."""
    
def validate_config(config: dict) -> None:
    """Validate required fields exist."""
    
def get_enabled_formats(config: dict) -> list[str]:
    """Get list of enabled output formats."""
```

**Config Structure**:
```toml
[general]
title = "Songbook Title"
sections_file = "sections.toml"

[html]
enabled = true
template = "html/index.html.j2"

[bound_pdf]
enabled = true
template = "latex/songbook.tex.j2"
paper = "letterpaper"
columns = 2
```

## Data Flow Example

**Complete build of a PDF songbook:**

1. **CLI** (`cli.py`):
   ```python
   args = parser.parse_args()
   builder = SongBookBuilder(args.config, args.input, args.output)
   builder.build()
   ```

2. **Builder** loads config and sections:
   ```python
   config = load_config("book_config.toml")
   sections = load_config(config["general"]["sections_file"])
   ```

3. **Parser** converts XML → models:
   ```python
   parser = OpenLyricsParser()
   songs = [parser.parse(f) for f in xml_files]
   # Result: List[Song] with full metadata
   ```

4. **Renderer** generates LaTeX:
   ```python
   renderer = LaTeXRenderer()
   latex_content = renderer.render_songbook(songs, config)
   # Result: Complete .tex file as string
   ```

5. **Compiler** produces PDF:
   ```python
   compiler = PDFCompiler()
   # Pass 1: Create index files
   compiler._run_pdflatex(tex_file)
   compiler._generate_indices()
   # Pass 2: Final PDF with indices
   pdf_path = compiler._run_pdflatex(tex_file)
   ```

## Key Design Patterns

### 1. Template Method Pattern
`BaseRenderer` defines the structure, subclasses implement format-specific rendering.

### 2. Strategy Pattern
Different renderers and compilers can be swapped based on output format.

### 3. Pipeline Architecture
Each stage transforms data and passes it to the next stage.

### 4. Separation of Concerns
- Models: Data only, no logic
- Parsers: XML → Models
- Renderers: Models → Format
- Compilers: Format → Final output
- Builder: Orchestration only

## Testing Strategy

### Unit Tests
- **Parsers**: Test XML parsing with various song structures
- **Renderers**: Test template rendering with mock Song objects
- **Models**: Test data validation and edge cases

### Integration Tests
- **Full Build**: Test complete pipeline with sample songbook
- **Format Compatibility**: Verify all formats produce valid output

### Test Fixtures
- Sample XML files with various features (chords, alternate titles, recordings)
- Expected output snippets for comparison

## Future Enhancements

### EPUB Output
```
LaTeXRenderer → tex4ebook → EPUB
```
Already have LaTeX templates, just need EPUBCompiler wrapper around tex4ebook.

### Media Player
- HTML renderer already parses `recordings` metadata
- Need JavaScript player component in HTML template
- Support YouTube embeds, audio files, external links

### Performance
- Parallel song parsing (use `multiprocessing.Pool`)
- Template caching (Jinja2 already does this)
- Incremental builds (only rebuild changed songs)

## Maintenance Notes

### Adding a New Output Format

1. Create template in `templates/{format}/`
2. Create renderer in `renderers/{format}.py`
3. (Optional) Create compiler in `compilers/{format}.py`
4. Update `builder.py` to recognize format name
5. Add example config section

### Modifying Templates

LaTeX templates must:
- Use `namespace()` for any variable reassignment in loops
- Handle both column switching and environment restart for sections
- Use `\setcounter{songnum}{1}` to start numbering at 1

HTML templates should:
- Be mobile-responsive
- Support keyboard navigation
- Use semantic HTML5

### Debugging Tips

- Enable logging: `logging.basicConfig(level=logging.DEBUG)`
- Check intermediate files in `build/` directory
- LaTeX errors: Look at `.log` file in build directory
- Index issues: Check `.sxd` files (raw) and `.sbx` files (formatted)

## Dependencies

**Runtime**:
- `jinja2`: Template rendering
- `tomli`: TOML parsing (Python 3.11+ has built-in `tomllib`)

**External Tools**:
- `pdflatex`: PDF compilation
- LaTeX packages: `songs`, `geometry`, `fancyhdr`, `titleidx`, `multicol`

**Development**:
- `pytest`: Testing
- `mypy`: Type checking
- `black`: Code formatting

## Version History

- **v2.0.0** (2026-01-31): Complete rewrite with modern architecture
- **v1.0.0**: Original monolithic script
