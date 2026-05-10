"""Command line utility for creating and manipulating HROT PAK files.

Surface is identical to joshuaskelly/hrot-cli-tools `pak`:

    pak <file.pak> [list...] [-q] [-v]

If `list` is omitted, files are read (one per line) from stdin.

Run with:
    python3 pak.py <args>
"""

import argparse
import os
import re
import sys

# Sibling-module import. `format` shadows the Python builtin within this
# file, but nothing here calls the builtin format(), so the shadow is harmless.
import format as fmt

__version__ = "2.0.0"


# ---------------------------------------------------------------------------
# Argparse helpers
# ---------------------------------------------------------------------------
# Adapted from joshuaskelly/hrot-cli-tools `hcli/common.py` (MIT). See README.

_ANSI_ESCAPE = re.compile(r"\x1B\[[0-?]*[ -/]*[@-~]")


def read_from_stdin():
    """Read sanitized lines from stdin (non-tty only).

    Returns a list of stripped, ANSI-stripped, non-empty lines, or None
    if stdin is a tty (so the caller can fall back to its default).
    """
    if not sys.stdin.isatty():
        stdin = [t.strip("\n") for t in sys.stdin]
        stdin = [_ANSI_ESCAPE.sub("", t) for t in stdin]
        stdin = [t for t in stdin if t]
        return stdin
    return None


class ResolvePathAction(argparse.Action):
    """argparse action that expands `~` in path arguments."""

    def __call__(self, parser, namespace, values, option_string=None):
        if isinstance(values, list):
            fullpath = [os.path.expanduser(v) for v in values]
        else:
            fullpath = os.path.expanduser(values)
        setattr(namespace, self.dest, fullpath)


class _Parser(argparse.ArgumentParser):
    """ArgumentParser that prints help on error (matches the original CLI UX)."""

    def error(self, message):
        sys.stderr.write(f"{self.prog} error: {message}\n")
        self.print_help()
        sys.exit(1)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = _Parser(
        prog="pak",
        description=(
            "Default action is to add or replace pak file entries from list.\n"
            "If list is omitted, pak will use stdin."
        ),
        epilog="example: pak tex.pak image.png => adds image.png to tex.pak",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "file",
        metavar="file.pak",
        action=ResolvePathAction,
        help="pak file to create",
    )

    parser.add_argument(
        "list",
        nargs="*",
        action=ResolvePathAction,
        default=[],
    )

    parser.add_argument(
        "-q",
        dest="quiet",
        action="store_true",
        help="quiet mode",
    )

    parser.add_argument(
        "-v", "--version",
        dest="version",
        action="version",
        help=argparse.SUPPRESS,
        version=f"{parser.prog} version {__version__}",
    )

    args = parser.parse_args()

    # If `list` wasn't given on the command line, fall back to stdin (if not a tty).
    # This is done AFTER parse_args so that flags like --version short-circuit
    # before we ever touch stdin.
    if not args.list:
        from_stdin = read_from_stdin()
        if from_stdin:
            args.list = from_stdin

    if not args.list:
        parser.error("the following arguments are required: list")

    parent = os.path.dirname(args.file) or "."
    if not os.path.exists(parent):
        os.makedirs(parent)

    mode = "a" if os.path.isfile(args.file) else "w"

    # Resolve the input list into (source, archive_name) pairs.
    entries = []
    cwd = os.getcwd()
    for path in args.list:
        if os.path.isdir(path):
            for root, _dirs, files in os.walk(path):
                for name in files:
                    if name.startswith("."):
                        continue
                    full = os.path.join(root, name)
                    arc = os.path.relpath(full, cwd).replace(os.sep, "/")
                    entries.append((full, arc))
        elif os.path.isfile(path):
            arc = os.path.relpath(path, cwd).replace(os.sep, "/")
            entries.append((path, arc))
        else:
            print(f"{parser.prog}: warning: skipping {path}", file=sys.stderr)

    if not entries:
        parser.error("no valid input files found")

    if not args.quiet:
        print(f"Archive: {os.path.basename(args.file)}")

    def _progress(i, total, name):
        if not args.quiet:
            print(f"  adding: {name}")

    try:
        fmt.write_pak(args.file, entries, mode=mode, progress=_progress)
    except Exception as e:
        print(f"{parser.prog}: error: {e}", file=sys.stderr)
        sys.exit(1)

    sys.exit(0)


if __name__ == "__main__":
    main()
