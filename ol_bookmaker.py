#!/usr/bin/env python3
"""Tool for creating lyric books from OpenLyrics XML files."""

import argparse
import tomli
from pathlib import Path
import logging
import shutil
from os import listdir
import subprocess
import jinja2
import xml.etree.ElementTree as ET
import re


class SongBookMaker:
    def __init__(
        self,
        songbook_config: dict,
        output_formats: list[dict] = [],
        output_dir: Path = "output",
        sections: dict[str, dict] = None,
        base_path: Path = None,  # base path for input files that are not absolute
        clean: bool = False,
    ) -> None:
        self.songbook_config = songbook_config
        self.output_dir = output_dir
        self.output_formats = output_formats
        self.base_path = base_path
        self.sections = sections
        self.clean = clean
        self.songfile = "songfile.sbd"
        self.build_root = base_path.joinpath(Path("build"))

        # Sort the sections by the order field, if present.
        if self.sections is not None:
            for name, section in self.sections.items():
                sort = section.get("sort", None)
                if not sort:
                    logging.debug(f"Not sorting section {name}")
                    continue
                if section["sort"] == "filename":
                    logging.debug(f"Sorting section {name} by filename")
                    section["files"].sort(key=lambda f: f.name)
                else:
                    logging.error(
                        f"Unknown sort method for section {name}: {section['sort']}"
                    )

        logging.debug(f"Songbook Config")
        for k, v in self.songbook_config.items():
            if k not in ["files", "sections"]:
                logging.debug(f"  {k}: {v}")
        logging.debug(f"Output Directory: {self.output_dir}")
        logging.debug(f"Base Path: {self.base_path}")
        logging.debug(f"Sections")
        for name, settings in self.sections.items():
            logging.debug(f"  {name}:")
            for k, v in settings.items():
                logging.debug(f"    {k}: {v}")

        logging.debug(f"Output Formats")
        for name, settings in self.output_formats.items():
            logging.debug(f"  {name}:")
            for k, v in settings.items():
                logging.debug(f"    {k}: {v}")

    def make_output(self):
        # Clean output directory
        if self.clean:
            logging.info(
                f"Cleaning build and output directories: {self.build_root} {self.output_dir}"
            )
            shutil.rmtree(self.build_root, ignore_errors=True)
            shutil.rmtree(self.output_dir, ignore_errors=True)
        # Create output directory
        logging.info(f"Creating output directory {self.output_dir}")
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Create output for each format
        for format_name, format_config in self.output_formats.items():
            logging.info(f"Creating output for format {format_name}")
            if format_config["type"] == "html":
                self.make_html_output(format_config)
            elif format_config["type"] == "pdf":
                self.make_pdf_output(format_config)
            elif format_config["type"] == "epub":
                self.make_epub_output(format_config)
            else:
                raise ValueError(f"Invalid output format: {format_config['type']}")

    def make_html_output(self, html_config: dict):
        """Create HTML output."""
        # Create output directory
        output_dir = self.output_dir.joinpath(html_config["output_dir"])
        output_dir.mkdir(parents=True, exist_ok=True)
        logging.info(
            f"Creating HTML output for directory {output_dir}. This may take a while..."
        )

        # Copy stylesheets. These are optional, and are a list of files and directories.
        # Directories are copied recursively, preserving the directory structure.

        if "stylesheets" in html_config:
            for stylesheet in html_config["stylesheets"]:
                logging.debug(f"Copying stylesheet {stylesheet}")
                stylesheet = Path(stylesheet)
                if self.base_path and not stylesheet.is_absolute():
                    stylesheet = self.base_path.joinpath(stylesheet)
                if stylesheet.is_dir():
                    shutil.copytree(
                        stylesheet,
                        output_dir.joinpath(stylesheet.name),
                        dirs_exist_ok=True,
                    )
                else:
                    shutil.copy(stylesheet, output_dir)

        # Copy images. These are optional, and are a list of files and directories.
        # Directories are copied recursively, preserving the directory structure.
        if "image_dir" in html_config:
            for image in html_config["image_dir"]:
                logging.debug(f"Copying image {image}")
                image = Path(image)
                if self.base_path and not image.is_absolute():
                    image = self.base_path.joinpath(image)
                if image.is_dir():
                    shutil.copytree(
                        image,
                        output_dir.joinpath(image.name),
                        dirs_exist_ok=True,
                    )
                else:
                    shutil.copy(image, output_dir)
        # Create HTML files from input files for each section using xsltproc
        for section_name, section in self.sections.items():
            logging.debug(f"Creating HTML files for section {section_name}")
            section_output_dir = output_dir.joinpath(section_name)
            section_output_dir.mkdir(parents=True, exist_ok=True)
            for song_file in section["files"]:
                logging.debug(f"Creating HTML file for {song_file}")
                output_file = section_output_dir.joinpath(song_file.stem + ".html")
                xsltproc_args = [
                    "xsltproc",
                    "--output",
                    output_file,
                    self.base_path.joinpath(html_config["song_xslt"]),
                    song_file,
                ]
                logging.debug(f"Running xsltproc with args: {xsltproc_args}")
                xsltproc_result = subprocess.run(xsltproc_args)
                if xsltproc_result.returncode != 0:
                    raise RuntimeError(
                        f"xsltproc failed with return code {xsltproc_result.returncode}"
                    )

    def make_pdf_output(self, pdf_config: dict):
        """Create PDF output.
        This is done by formatting and joining several LaTeX files and then
        running pdflatex on the result."""

        # Create the output and build directories
        output_dir = self.output_dir.joinpath(pdf_config["output_dir"])
        output_dir.mkdir(parents=True, exist_ok=True)
        build_dir = self.build_root.joinpath(pdf_config["output_dir"])
        build_dir.mkdir(parents=True, exist_ok=True)

        # Render the template files and copy the result to the build directory.
        template_vars = (
            pdf_config
            | pdf_config.get("render_variables", {})
            | self.songbook_config
            | {"sections": self.sections}
        )
        for var in template_vars:
            logging.debug(f"Template variable {var}: {template_vars[var]}")

        # Render all the templates from the template directory to the build directory.
        # Get a list of all of the files in the template directory, excluding the
        # style file.
        template_dir = self.base_path.joinpath(pdf_config["template_dir"])
        template_files = listdir(template_dir)
        logging.debug(f"Template files: {template_files}")
        template_files = [
            Path(template_dir).joinpath(f)
            for f in template_files
            if Path(f).name != Path(pdf_config["songbook_style"]).name
        ]
        for template in template_files:
            self._render_template(
                template,
                build_dir,
                template_vars,
            )

        # Copy the songs.sty file to the build directory
        shutil.copy(
            self.base_path.joinpath(pdf_config["songbook_style"]),
            build_dir,
        )

        # Copy the images directory to the build directory, if present.
        if "image_dir" in pdf_config:
            shutil.copytree(
                self.base_path.joinpath(pdf_config["image_dir"]),
                build_dir.joinpath(pdf_config["image_dir"]),
                dirs_exist_ok=True,
            )

        # Create the SBD file from the input files.
        self._make_songfile(build_dir, pdf_config)
        # Get the output filename
        output_filename = (
            (pdf_config["output_file"])
            if "output_file" in pdf_config
            else pdf_config["songbook_template"]
        )

        # Run pdflatex on the main file.
        pdflatex_args = [
            "pdflatex",
            f"-jobname={output_filename}",
            "-halt-on-error",
            Path(pdf_config["songbook_template"]).name,
        ]
        logging.debug(f"Running pdflatex with args: {pdflatex_args}")
        pdflatex_result = subprocess.run(pdflatex_args, cwd=build_dir)
        if pdflatex_result.returncode != 0:
            raise RuntimeError(
                f"pdflatex failed with return code {pdflatex_result.returncode}"
            )

        # Create the index files.
        for sxd in Path.glob(build_dir, "*.sxd"):
            logging.debug(f"Creating index file for {sxd}")
            self._make_latex_index(sxd)

        # Rerun pdflatex now that we have indices
        pdflatex_result = subprocess.run(pdflatex_args, cwd=build_dir)
        if pdflatex_result.returncode != 0:
            raise RuntimeError(
                f"pdflatex rerun failed with return code {pdflatex_result.returncode}"
            )

        # Copy the output file to the output directory
        shutil.copy(
            build_dir.joinpath(Path(output_filename).stem + ".pdf"),
            output_dir,
        )

    def _render_template(self, template: str, build_dir: Path, variables: dict = None):
        """Render the given template and copy the result to the build directory."""
        # Load the template
        template = Path(template)
        output_file = build_dir.joinpath(template.name)
        logging.debug(f"Rendering template {template} to {output_file}")
        with open(template, "r") as template_file:
            template = jinja2.Template(template_file.read())

        # Render the template
        try:
            rendered = template.render(variables)
        except jinja2.exceptions.UndefinedError as e:
            # Either there is a real problem, or the variable isn't defined for
            # a template we aren't using. Log a warning and continue.
            logging.warning(f"Undefined variable in template {template}: {e}")
            return

        # Write the rendered template to the build directory
        with open(output_file, "w") as output:
            output.write(rendered)

    def make_epub_output(self, epub_config: dict):
        """Create EPUB output, using tex4ebook to convert the LaTeX to HTML."""
        # Create the output and build directories
        output_dir = self.output_dir.joinpath(epub_config["output_dir"])
        output_dir.mkdir(parents=True, exist_ok=True)
        build_dir = self.build_root.joinpath(epub_config["output_dir"])
        build_dir.mkdir(parents=True, exist_ok=True)

        # Render the template files and copy the result to the build directory.
        template_vars = (
            epub_config
            | epub_config.get("render_variables", {})
            | self.songbook_config
            | {"sections": self.sections}
        )
        for var in template_vars:
            logging.debug(f"Template variable {var}: {template_vars[var]}")

        # Render all the templates from the template directory to the build directory.
        # Get a list of all of the files in the template directory, excluding the
        # style file.
        template_dir = self.base_path.joinpath(epub_config["template_dir"])
        template_files = listdir(template_dir)
        logging.debug(f"Template files: {template_files}")
        template_files = [
            Path(template_dir).joinpath(f)
            for f in template_files
            if Path(f).name != Path(epub_config["songbook_style"]).name
        ]
        for template in template_files:
            self._render_template(
                template,
                build_dir,
                template_vars,
            )

        # Copy the songs.sty file to the build directory
        shutil.copy(
            self.base_path.joinpath(epub_config["songbook_style"]),
            build_dir,
        )

        # Copy the images directory to the build directory, if present.
        if "image_dir" in epub_config:
            shutil.copytree(
                self.base_path.joinpath(epub_config["image_dir"]),
                build_dir.joinpath(epub_config["image_dir"]),
                dirs_exist_ok=True,
            )

        # Create the SBD file from the input files.
        self._make_songfile(build_dir, epub_config)
        # Get the output filename, without the extension.
        output_filename = (
            (epub_config["output_file"])
            if "output_file" in epub_config
            else epub_config["songbook_template"]
        ).split(".")[0]

        # Run pdflatex on the main file to create the sxd files.
        pdflatex_args = [
            "pdflatex",
            f"-jobname={output_filename}",
            "-halt-on-error",
            Path(epub_config["songbook_template"]).name,
        ]
        logging.debug(f"Running pdflatex with args: {pdflatex_args}")
        pdflatex_result = subprocess.run(pdflatex_args, cwd=build_dir)
        if pdflatex_result.returncode != 0:
            raise RuntimeError(
                f"pdflatex failed with return code {pdflatex_result.returncode}"
            )

        # Create the index files.
        for sxd in Path.glob(build_dir, "*.sxd"):
            logging.debug(f"Creating index file for {sxd}")
            self._make_latex_index(sxd)

        latex_args = [
            "tex4ebook",
            "--output-dir",
            build_dir,
            "--format",
            "epub",
            "--jobname",
            output_filename,
            Path(epub_config["songbook_template"]).name,
        ]
        # Run tex4ebook  now that we have indices
        latex_result = subprocess.run(latex_args, cwd=build_dir)
        if latex_result.returncode != 0:
            raise RuntimeError(
                f"tex4ebook run failed with return code {latex_result.returncode}"
            )

        # Copy the output file to the output directory
        shutil.copy(
            build_dir.joinpath(
                Path(output_filename).stem + "-epub",
                output_filename + ".epub",
            ),
            output_dir,
        )

    def _make_songfile(self, build_dir: Path, config: dict):
        """Create the SBD file from the input files."""
        logging.debug(f"Creating SBD file in {build_dir}")
        # Create the SBD file from the input files.
        songfile = build_dir.joinpath(self.songfile)
        with open(songfile, "w") as output:
            # Add the sbd header from the render_variables, if present
            if "sbd_header" in config:
                output.write(config["sbd_header"])

            # Add the section input files
            for section_name, section in self.sections.items():
                output.write(
                    r"\begin{songs}{"
                    + section_name.replace(" ", "_")
                    + "_idx"
                    + ","
                    + r"authoridx}"
                    + "\n"
                )
                output.write(f"\\songchapter{{{section_name}}}\n")
                for input_file in section["files"]:
                    logging.debug(f"Adding {input_file} to SBD file.")
                    xml = Path(input_file).read_text()
                    text = self._xml_to_sbd(xml)
                    if not text:
                        logging.error(f"Failed to convert {input_file} to SBD.")
                        continue
                    output.write(text)
                output.write(r"\end{songs}")

    def _xml_to_sbd(self, xml_string: str) -> str:
        """Convert an XML string to an LaTeX songs entry.
        This is done by parsing the XML and then converting it to LaTeX tags."""

        # First, parse the XML string into an XML tree.
        # This is done by converting the string to bytes and then parsing it.
        # This is necessary because the XML parser expects bytes, not a string.
        xml_bytes = xml_string.encode("utf-8")
        xml_tree = ET.fromstring(xml_bytes)

        # Get the properties from the XML tree.
        ns = {"ol": "http://openlyrics.info/namespace/2009/song"}
        song_header = {}
        properties = xml_tree.find(".//ol:properties", ns)
        if properties is not None:
            # Walk the song header, getting the known tags
            multitags = {"titles", "authors", "keywords", "themes"}
            single_tags = {"ccliNo", "verseOrder", "copyright", "tune"}
            for child in properties:
                # Check if the tag is a known tag, removing the namespace, if present.
                if "}" in child.tag:
                    child.tag = child.tag.split("}")[1]
                if child.tag in multitags:
                    if child.tag not in song_header:
                        song_header[child.tag] = []
                    for grandchild in child:
                        song_header[child.tag].append(grandchild.text)
                elif child.tag in single_tags:
                    song_header[child.tag] = child.text
                else:
                    logging.debug(f"Unknown tag {child.tag} in song header.")
        else:
            logging.error(f"No properties found for XML {xml_string}.")
            return ""
        if "titles" not in song_header:
            logging.error(f"No title found for XML {xml_string}.")
            return ""

        # Create the LaTeX entry
        entry = "\\beginsong{" + song_header["titles"][0] + "}[\n"
        if "authors" in song_header:
            entry += "by={" + ", ".join(song_header["authors"]) + "},\n"
        if "keywords" in song_header:
            entry += "index={" + ", ".join(song_header["keywords"]) + "},\n"
        if "copyright" in song_header:
            entry += "cr={" + song_header["copyright"] + "},\n"
        if "tune" in song_header:
            entry += "tune={" + song_header["tune"] + "},\n"
        entry += "]\n\n"

        # Check if there is a comment element before the first verse and add it.
        # Walk the tree until we find the first verse.
        # If we find a comment element, add it to the entry.
        for child in xml_tree:
            if "}" in child.tag:
                child.tag = child.tag.split("}")[1]
            if child.tag == "verse":
                break
            if child.tag == "comment":
                entry += f"\\textnote{{{child.text}}}\n\n"

        # Add the verses and choruses, in verseOrder is present.
        # Otherwise add them in XML order.
        if "verseOrder" in song_header:
            verse_order = song_header["verseOrder"].split()
        else:
            # Get all verse numbers
            verse_order = []
            for verse in xml_tree.findall(".//ol:verse", ns):
                verse_order.append(verse.attrib["name"])
        for verse_number in verse_order:
            if verse_number.lower().startswith("c"):
                entry += f"\\beginchorus\n"
            else:
                entry += f"\\beginverse\n"
            verse = xml_tree.find(f".//ol:verse[@name='{verse_number}']", ns)
            # Each verse consists of one or more lines of text, which may be
            # interspersed with chords and other tags.
            lines = verse.findall(".//ol:lines", ns)
            for line in lines:
                # Each line consists of one or more text elements, which may be
                # interspersed with chords and other tags.
                # The text elements are joined together, and then the chords are
                # interspersed.
                line_text = line.text.strip() if line.text else ""
                for item in line:
                    # Remove the namespace from the tag, if present
                    if "}" in item.tag:
                        item.tag = item.tag.split("}")[1]
                    if item.tag == "comment":
                        line_text += f"\\textnote{{{item.text}}}"
                    if item.tag == "chord":
                        # Add the chord, if present. OpenLyrics uses the root attribute
                        # for the chord, plus on optional structure attribute for the chord type.
                        chord = item.attrib["root"].replace("&", "b")
                        if "structure" in item.attrib:
                            chord += item.attrib["structure"]
                        line_text += f" \\[{chord}]"
                    if item.tag == "br":
                        line_text += "\n"
                    if item.tail:
                        if "\n" in item.tail:
                            text = "\n" + item.tail.strip() + "\n"
                        else:
                            text = item.tail.strip()
                        line_text += text.rstrip()

                entry += line_text
            if verse_number.lower().startswith("c"):
                entry += "\n\\endchorus\n"
            else:
                entry += "\n\\endverse\n"
        entry += "\\endsong\n\n"
        return entry

    def _make_latex_index(self, sxd_file: Path | str):
        """Create an index file for the given SXD file."""
        index_file = sxd_file.with_suffix(".sbx")
        logging.debug(f"Creating index file for {sxd_file} to {index_file}")
        with open(sxd_file, "r") as sxd:
            type = sxd.readline().strip()
        if type.startswith("AUTHOR"):
            self._make_latex_author_index(sxd_file, index_file)
        elif type.startswith("TITLE"):
            self._make_latex_title_index(sxd_file, index_file)
        else:
            logging.error(f"Unknown index type {type} in {sxd_file}.")

    def _make_latex_author_index(self, sxd_file: str, sbx_file: str):
        """Create an author index file (sbx_file) for the given SXD file."""
        authors = {}
        # Read the SXD file, creating a dictionary of authors and their songs.
        with open(sxd_file, "r") as sxd:
            sxd.readline()
            while True:
                # read 3 line song entry, stripping excess whitespace
                author = sxd.readline().strip()
                songnum = sxd.readline().strip()
                link = sxd.readline().strip()
                if not link:
                    break  # EOF
                # process list of authors into entry format
                # this may be ',' , 'and' and/or ';' delimited
                # '~' or '\ ' may have been used to replace spaces to prevent name breaking
                for name in [
                    x
                    for x in re.split(" and |[^a-zA-Z~. ]+", author.replace("\\ ", "~"))
                    if x != ""
                ]:
                    try:
                        first, last = name.rsplit(maxsplit=1)
                    except:  # only one word in name
                        entry = name.replace("~", " ").strip()
                    else:
                        entry = ", ".join([last.strip(), first.strip()]).replace(
                            "~", " "
                        )
                    # add to the dictionary
                    # {'Doe, John': [{'num': '1', 'link': 'song1-1.1'}, etc...]}
                    try:
                        authors[entry].append({"songnum": songnum, "link": link})
                    except KeyError:
                        authors[entry] = [{"songnum": songnum, "link": link}]
        with open(sbx_file, "w") as sbx:
            # setup some formatting string constants
            beginsection = "\\begin{{idxblock}}{{}}\n"
            endsection = "\\end{{idxblock}}\n"
            auth_entry = "\\idxentry{{{author}}}{{"
            song_entry = "\\songlink{{{link}}}{{{songnum}}}"
            sbx.write(beginsection.format())
            for author in sorted(authors, key=str.casefold):
                # write author entry
                sbx.write(auth_entry.format(author=author))
                # write first song entry
                songs = authors[author]
                songs.sort(key=lambda k: int(k["songnum"]))
                sbx.write(
                    song_entry.format(
                        songnum=songs[0]["songnum"], link=songs[0]["link"]
                    )
                )
                # write subsequent song entries
                for song in songs[1:]:
                    sbx.write("\\\\")
                    sbx.write(
                        song_entry.format(songnum=song["songnum"], link=song["link"])
                    )
                # and end the line
                sbx.write("}\n")
            sbx.write(endsection.format())

    def _make_latex_title_index(
        self, sxd_file: str, sbx_file: str, letterblock: bool = True
    ):
        titles = []
        with open(sxd_file, "r") as f:
            _ = f.readline()  # skip the first line that is just used for file typing
            while True:
                # read 3 line song entry, stripping excess whitespace
                title = f.readline().strip()
                songnum = f.readline().strip()
                link = f.readline().strip()
                if not link:
                    break  # EOF
                # if the song title begins with a '*', remove it and set 'alt' = True
                if title.startswith("*"):
                    title = title.lstrip("*")
                    alt = True
                else:
                    alt = False
                # move beginning 'a', 'an', and 'the' to the end of the title and remove leading whitespace
                try:
                    begin, end = title.split(maxsplit=1)
                except ValueError:  # only one word in title
                    pass
                else:
                    if begin in ["a", "an", "the", "A", "An", "The"]:
                        title = ", ".join([end, begin])
                # capitalize just the first letter of the first word
                title = title[0].upper() + title[1:]
                # make into a dictionary and add the song to the song list
                titles.append(
                    {"title": title, "songnum": songnum, "link": link, "alt": alt}
                )
        titles.sort(key=lambda k: k["title"].casefold())

        # setup some formatting string constants
        beginsection = "\\begin{{idxblock}}{{{}}}\n"
        endsection = "\\end{{idxblock}}\n"
        entry = "\\{linktype}{{{title}}}{{\\songlink{{{link}}}{{{songnum}}}}}\n"

        # write out the index file
        with open(sbx_file, "w") as f:
            if letterblock:
                section = titles[0]["title"][0]
                f.write(beginsection.format(section))
            for song in titles:
                if letterblock:  # check for a new index section
                    if song["title"][0].casefold() != section.casefold():
                        f.write(endsection.format())  # close out old block
                        section = song["title"][0].upper()
                        f.write(beginsection.format(section))
                if song["alt"]:  # check for alternate title
                    linktype = "idxaltentry"
                else:
                    linktype = "idxentry"
                f.write(
                    entry.format(
                        linktype=linktype,
                        title=song["title"],
                        link=song["link"],
                        songnum=song["songnum"],
                    )
                )
            if letterblock:
                f.write(endsection.format())  # close out final block


def get_file_list(input: list[str | Path], base_path: Path = None) -> list[Path]:
    """Given a list of files and directories, return a list of files.
    If a directory is given, all files in that directory are returned.
    If base_path is given, all input paths that are not absolute are
    interpreted as relative to base_path."""
    # Convert input to list of Path objects
    input = [Path(f) for f in input]
    if base_path is not None:
        input = [base_path.joinpath(f) if not f.is_absolute() else f for f in input]
    files = []
    for f in input:
        if f.is_dir():
            files.extend([f.joinpath(file) for file in listdir(f)])
        else:
            files.append(f)
    return files


def load_config(config_file: str) -> dict:
    """Load config file and verify that all required fields are present."""
    with open(config_file, "rb") as config_file:
        config = tomli.load(config_file)

    # Check that all required fields are present
    required_fields = [
        "songbook",
        "output_formats",
    ]
    for field in required_fields:
        if field not in config:
            raise ValueError(f"Missing required field in config file: {field}")

    # Check that all output formats are valid
    format_type_options = {
        "html": ["template", "output_dir", "output_file"],
        "pdf": ["output_dir", "output_file"],
        "epub": ["output_dir", "output_file"],
    }
    for format_name, settings in config["output_formats"].items():
        if settings["type"] not in format_type_options:
            raise ValueError(f"Invalid output format: {settings['type']}")
        for field in format_type_options[settings["type"]]:
            if field not in settings:
                raise ValueError(
                    f"Missing required field for format_name: {settings['type']}: {field}"
                )

    return config


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("config", type=str, default="config.toml", help="Config file.")
    parser.add_argument(
        "--output",
        type=str,
        default="output",
        help="Top level output directory. (default: %(default)s))",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print verbose output.",
    )
    parser.add_argument(
        "--clean",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Clean output directory before creating output. (default: %(default)s)",
    )
    args = parser.parse_args()

    # Set up logging
    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)

    # Parse config file
    config = load_config(args.config)

    # Get base path for input files
    base_path = Path(args.config).parent

    # Get the list of sections to include.
    sections = {}
    if "sections" in config:
        for section, settings in config["sections"].items():
            logging.debug(f"Section {section}: {settings}")
            sections[section] = {}
            if "intro_file" in settings and settings["intro_file"] is not None:
                sections[section]["intro_file"] = Path(settings["intro_file"])
            sections[section]["files"] = get_file_list(settings["files"], base_path)
            sections[section]["sort"] = settings.get("sort", None)
            # Check that all input files exist
            for f in sections[section]["files"]:
                if not f.exists():
                    raise FileNotFoundError(f"Input file not found: {f}")

    maker = SongBookMaker(
        songbook_config=config["songbook"],
        sections=sections,
        output_dir=base_path.joinpath(args.output),
        output_formats=config["output_formats"],
        base_path=base_path,
        clean=args.clean,
    )

    maker.make_output()
