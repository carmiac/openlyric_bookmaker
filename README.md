Open Lyric Book Maker
=====================

This is a tool to create lyric books in several formats from a series of song files in the [Open Lyrics](https://github.com/openlyrics/openlyrics/) format, which is an XML format for storing lyrics and metadata about songs.

The tool is written in Python 3 and uses [Jinja2](http://jinja.pocoo.org/docs/2.10/) for templating.

## Open Lyric Format Extensions

The Open Lyric format has been extended to include some additional metadata fields. These are:

* `recordings` - a list of recordings of the song.
  * `recording` - a recording of the song.
    * `title` - the title of the recording
    * `artist` - the artist of the recording
    * `url` - a URL to the recording. This can be a YouTube URL, a SoundCloud URL, or any other URL that points to a recording of the song, including a URL to a file in a given directory.

## Usage

The tool is run from the command line.  Due to the number of options for each output format, the tool uses a configuration file to specify the options for each output format.  The configuration file is a TOML file, and the default configuration file is `config.yaml`.  The configuration file can be specified using the `-c` option.

The main command line options are:
* `--config` - the configuration file to use.  The default is `config.yaml`.
* `--input` - the input directory containing the song files.  The default is `songs`.
* `--output` - the output directory.  The default is `output`.
* `--formats` - the output format(s). The default is `all`.  This can be a list of formats, or `all` to output all formats.

## Configuration File

The configuration file is a TOML file.  The default configuration file is `config.toml`.  The configuration file contains a list of general options, output formats, and the options for each output format. A configuration file can have multiple output formats, including multiple output formats of the same type.  For example, you can have both HTML and PDF output formats.

An example configuration file is available in [examples/example_config.toml](examples/example_config.toml).


## Generating HTML

Step 1: modify `examples/stylesheets.openlyrics.xsl`, adding any songs into the `<ul>` list within the `<nav>` element.

Step 2: run this from the command line:

```bash
./build-html.sh
```

Step 3: open any of the `.html` files in `examples/songs/`
