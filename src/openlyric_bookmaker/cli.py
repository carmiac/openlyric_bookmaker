"""Command-line interface for openlyric_bookmaker."""

import argparse
import logging
import sys
from pathlib import Path

from openlyric_bookmaker.builder import SongBookBuilder

logger = logging.getLogger(__name__)


def setup_logging(verbose: bool = False) -> None:
    """Configure logging.

    Args:
        verbose: Enable debug logging if True
    """
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def main() -> int:
    """Main entry point for the CLI.

    Returns:
        Exit code (0 for success, non-zero for failure)
    """
    parser = argparse.ArgumentParser(
        description="Tool for creating songbooks from OpenLyrics XML files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "config",
        type=Path,
        help="Path to TOML configuration file",
    )

    parser.add_argument(
        "--output",
        type=Path,
        help="Output directory (overrides config default: output/)",
    )

    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose (debug) logging",
    )

    parser.add_argument(
        "--clean",
        action="store_true",
        default=False,
        help="Clean output directory before building",
    )

    args = parser.parse_args()

    # Setup logging
    setup_logging(args.verbose)

    # Validate config file exists
    if not args.config.exists():
        logger.error(f"Config file not found: {args.config}")
        return 1

    try:
        # Create builder and build
        builder = SongBookBuilder(
            config_path=args.config,
            output_dir=args.output,
            clean=args.clean,
        )
        builder.build()
        
        logger.info("✓ Songbook build completed successfully")
        return 0

    except Exception as e:
        logger.error(f"Build failed: {e}", exc_info=args.verbose)
        return 1


if __name__ == "__main__":
    sys.exit(main())
