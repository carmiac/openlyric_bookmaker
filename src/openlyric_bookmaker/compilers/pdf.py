"""PDF compiler using pdflatex."""

import logging
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)


class PDFCompiler:
    """Compiles LaTeX files to PDF using pdflatex."""

    def __init__(self, build_dir: Path) -> None:
        """Initialize the PDF compiler.

        Args:
            build_dir: Directory where LaTeX files are located
        """
        self.build_dir = build_dir

    def compile(self, main_tex_file: str, output_filename: str, runs: int = 2) -> Path:
        """Compile a LaTeX file to PDF.

        Args:
            main_tex_file: Name of the main .tex file to compile
            output_filename: Desired output filename (without .pdf extension)
            runs: Number of pdflatex runs (default 2 for resolving references)

        Returns:
            Path to the generated PDF file

        Raises:
            RuntimeError: If pdflatex compilation fails
        """
        logger.info("Compiling %s to PDF...", main_tex_file)

        # Check if pdflatex is available
        try:
            subprocess.run(
                ["pdflatex", "--version"],
                capture_output=True,
                check=True,
            )
        except (subprocess.CalledProcessError, FileNotFoundError):
            raise RuntimeError("pdflatex not found. Please install TeX Live, MacTeX, or MiKTeX.")

        # Run pdflatex
        for run_num in range(1, runs + 1):
            logger.info("Running pdflatex (pass %s/{runs})...", run_num)

            pdflatex_args = [
                "pdflatex",
                f"-jobname={output_filename}",
                "-halt-on-error",
                "-interaction=nonstopmode",
                main_tex_file,
            ]

            result = subprocess.run(
                pdflatex_args,
                cwd=self.build_dir,
                capture_output=True,
                text=True,
            )

            if result.returncode != 0:
                logger.error("pdflatex failed on pass %s", run_num)
                logger.error("stdout: %s", result.stdout[-2000:])  # Last 2000 chars
                logger.error("stderr: %s", result.stderr[-2000:])
                raise RuntimeError(
                    f"pdflatex failed with return code {result.returncode}. "
                    f"Check log file in {self.build_dir}"
                )

            # Generate indices after first pass if .sxd files exist
            if run_num == 1:
                self._generate_indices()

        pdf_path = self.build_dir / f"{output_filename}.pdf"
        if not pdf_path.exists():
            raise RuntimeError(f"PDF file not found: {pdf_path}")

        logger.info("✓ PDF compiled successfully: %s", pdf_path)
        return pdf_path

    def _generate_indices(self) -> None:
        """Generate song indices from .sxd files."""
        for sxd_file in self.build_dir.glob("*.sxd"):
            logger.debug("Generating index for %s", sxd_file)
            try:
                # Read the first line to determine index type
                with open(sxd_file, "r", encoding="latin-1") as f:
                    index_type = f.readline().strip()

                sbx_file = sxd_file.with_suffix(".sbx")

                if index_type.startswith("AUTHOR"):
                    self._generate_author_index(sxd_file, sbx_file)
                elif index_type.startswith("TITLE"):
                    self._generate_title_index(sxd_file, sbx_file)
                else:
                    logger.warning("Unknown index type '%s' in {sxd_file}", index_type)

            except Exception as e:
                logger.warning("Failed to generate index for %s: {e}", sxd_file)

    def _generate_author_index(self, sxd_file: Path, sbx_file: Path) -> None:
        """Generate author index from .sxd file."""
        import re

        authors = {}

        # Read the SXD file, creating a dictionary of authors and their songs
        with open(sxd_file, "r", encoding="latin-1") as sxd:
            sxd.readline()  # Skip header line
            while True:
                # Read 3 line song entry
                author = sxd.readline().strip()
                songnum = sxd.readline().strip()
                link = sxd.readline().strip()
                if not link:
                    break  # EOF

                # Process list of authors (may be ',' , 'and' and/or ';' delimited)
                # '~' or '\ ' may have been used to replace spaces to prevent name breaking
                for name in [
                    x
                    for x in re.split(r" and |[^a-zA-Z~. ]+", author.replace("\\ ", "~"))
                    if x != ""
                ]:
                    try:
                        first, last = name.rsplit(maxsplit=1)
                    except ValueError:  # only one name
                        entry = name.replace("~", " ").strip()
                    else:
                        entry = ", ".join([last.strip(), first.strip()]).replace("~", " ")

                    # Add to the dictionary
                    if entry not in authors:
                        authors[entry] = []
                    authors[entry].append({"songnum": songnum, "link": link})

        # Write the .sbx file
        with open(sbx_file, "w", encoding="latin-1") as sbx:
            sbx.write("\\begin{idxblock}{}\n")
            for author in sorted(authors, key=str.casefold):
                # Write author entry
                sbx.write(f"\\idxentry{{{author}}}{{")

                # Sort songs by number
                songs = authors[author]
                songs.sort(key=lambda k: int(k["songnum"]))

                # Write first song entry
                sbx.write(f"\\songlink{{{songs[0]['link']}}}{{{songs[0]['songnum']}}}")

                # Write subsequent song entries
                for song in songs[1:]:
                    sbx.write("\\\\")
                    sbx.write(f"\\songlink{{{song['link']}}}{{{song['songnum']}}}")

                sbx.write("}\n")
            sbx.write("\\end{idxblock}\n")

        logger.debug("Generated author index: %s", sbx_file)

    def _generate_title_index(self, sxd_file: Path, sbx_file: Path) -> None:
        """Generate title index from .sxd file."""
        titles = []

        with open(sxd_file, "r", encoding="latin-1") as f:
            f.readline()  # Skip header line
            while True:
                # Read 3 line song entry
                title = f.readline().strip()
                songnum = f.readline().strip()
                link = f.readline().strip()
                if not link:
                    break  # EOF

                # If the song title begins with a '*', remove it and set 'alt' = True
                alt = False
                if title.startswith("*"):
                    title = title.lstrip("*")
                    alt = True

                # Move beginning 'a', 'an', and 'the' to the end of the title
                try:
                    begin, end = title.split(maxsplit=1)
                except ValueError:  # only one word in title
                    pass
                else:
                    if begin in ("a", "an", "the", "A", "An", "The"):
                        title = ", ".join([end, begin])

                # Capitalize just the first letter of the first word
                if title:
                    title = title[0].upper() + title[1:]

                titles.append({"title": title, "songnum": songnum, "link": link, "alt": alt})

        # Sort titles
        titles.sort(key=lambda k: k["title"].casefold())

        # Write the .sbx file
        with open(sbx_file, "w", encoding="latin-1") as f:
            # Group by first letter
            if titles:
                section = titles[0]["title"][0].upper()
                f.write(f"\\begin{{idxblock}}{{{section}}}\n")

                for song in titles:
                    # Check for a new index section
                    if song["title"][0].upper() != section:
                        f.write("\\end{idxblock}\n")
                        section = song["title"][0].upper()
                        f.write(f"\\begin{{idxblock}}{{{section}}}\n")

                    # Write entry
                    linktype = "idxaltentry" if song["alt"] else "idxentry"
                    f.write(
                        f"\\{linktype}{{{song['title']}}}"
                        f"{{\\songlink{{{song['link']}}}{{{song['songnum']}}}}}\n"
                    )

                f.write("\\end{idxblock}\n")

        logger.debug("Generated title index: %s", sbx_file)
