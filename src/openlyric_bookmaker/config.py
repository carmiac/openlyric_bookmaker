"""Configuration loading and validation."""

import logging
import sys
from pathlib import Path

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

logger = logging.getLogger(__name__)


def load_config(config_path: Path) -> dict:
    """Load a TOML configuration file.

    Args:
        config_path: Path to the TOML config file

    Returns:
        Dictionary containing the configuration

    Raises:
        FileNotFoundError: If config file doesn't exist
        ValueError: If config is invalid
    """
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with open(config_path, "rb") as f:
        config = tomllib.load(f)

    validate_config(config)
    return config


def validate_config(config: dict) -> None:
    """Validate configuration structure.

    Args:
        config: Configuration dictionary

    Raises:
        ValueError: If configuration is invalid
    """
    # Check for required sections
    if "songbook" not in config:
        raise ValueError("Config must have 'songbook' section")

    if "sections" not in config:
        raise ValueError("Config must have 'sections' section")

    if "output_formats" not in config:
        raise ValueError("Config must have 'output_formats' section")

    # Validate songbook section
    songbook = config["songbook"]
    if "title" not in songbook:
        raise ValueError("songbook.title is required")

    # Validate sections
    sections = config["sections"]
    if not sections:
        raise ValueError("At least one section must be defined")

    for section_name, section_config in sections.items():
        if "files" not in section_config:
            raise ValueError(f"Section '{section_name}' must have 'files' list")

    # Validate output formats
    output_formats = config["output_formats"]
    if not output_formats:
        raise ValueError("At least one output format must be defined")

    for format_name, format_config in output_formats.items():
        if "type" not in format_config:
            raise ValueError(f"Output format '{format_name}' must have 'type'")

        format_type = format_config["type"]
        if format_type not in ["html", "pdf", "epub"]:
            raise ValueError(
                f"Output format '{format_name}' has invalid type: {format_type}. "
                "Must be one of: html, pdf, epub"
            )

        # Validate format-specific requirements
        if format_type == "html":
            if "output_dir" not in format_config:
                raise ValueError(f"HTML output format '{format_name}' must have 'output_dir'")

    logger.info("Configuration validated successfully")


def get_file_list(file_patterns: list[str | Path], base_path: Path) -> list[Path]:
    """Expand file patterns into a list of song files.

    Args:
        file_patterns: List of file paths or directory paths
        base_path: Base path for resolving relative paths

    Returns:
        List of resolved file paths
    """
    files = []

    for pattern in file_patterns:
        path = Path(pattern)
        if not path.is_absolute():
            path = base_path / path

        if path.is_file():
            files.append(path)
        elif path.is_dir():
            # Get all .xml files in directory
            xml_files = sorted(path.glob("*.xml"))
            files.extend(xml_files)
        else:
            logger.warning(f"Path not found: {path}")

    return files
