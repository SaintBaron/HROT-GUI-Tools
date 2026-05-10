"""Command line utility for extracting files from HROT PAK files.

Surface is identical to joshuaskelly/hrot-cli-tools `unpak`:

    unpak <file.pak> [-l] [-d xdir] [-q] [-v]

Run with:
    python3 unpak.py <args>
"""

import argparse
import os
import sys

# Sibling-module import. `format` shadows the Python builtin within this
# file, but nothing here calls the builtin format(), so the shadow is harmless.
import format as fmt

__version__ = "2.0.0"


# ---------------------------------------------------------------------------
# Argparse helpers
# ---------------------------------------------------------------------------
# Adapted from joshuaskelly/hrot-cli-tools `hcli/common.py` (MIT). See README.

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
# Listing
# ---------------------------------------------------------------------------

def _print_listing(pak_path, entries):
    """Render the `unpak -l` table without the `tabulate` dependency."""
    entries = sorted(entries, key=lambda e: e.filename)
    headers = ("Length", "Name")
    total_len = sum(e.size for e in entries)
    count = len(entries)
    summary_name = f"{count} file{'' if count == 1 else 's'}"

    data_rows = [(str(e.size), e.filename) for e in entries]

    col0 = max(len(headers[0]), len(str(total_len)),
               *(len(r[0]) for r in data_rows)) if data_rows else len(headers[0])
    col1 = max(len(headers[1]), len(summary_name),
               *(len(r[1]) for r in data_rows)) if data_rows else len(headers[1])

    sep = f"  {'-' * col0}  {'-' * col1}"

    print(f"Archive: {os.path.basename(pak_path)}")
    print(f"  {headers[0]:>{col0}}  {headers[1]:<{col1}}")
    print(sep)
    for size, name in data_rows:
        print(f"  {size:>{col0}}  {name:<{col1}}")
    print(sep)
    print(f"  {str(total_len):>{col0}}  {summary_name:<{col1}}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = _Parser(
        prog="unpak",
        description="Default action is to extract files to xdir.",
        epilog="example: unpak PAK0.PAK -d ./out => extract all files to ./out",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "file",
        metavar="file.pak",
        action=ResolvePathAction,
    )

    parser.add_argument(
        "-l", "--list",
        action="store_true",
        help="list files",
    )

    parser.add_argument(
        "-d",
        metavar="xdir",
        dest="dest",
        default=os.getcwd(),
        action=ResolvePathAction,
        help="extract files into xdir",
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

    if not fmt.is_pakfile(args.file):
        print(f"{parser.prog}: cannot find or open {args.file}", file=sys.stderr)
        sys.exit(1)

    try:
        entries = fmt.read_pak(args.file)
    except fmt.BadPakFile as e:
        print(f"{parser.prog}: bad pak file: {e}", file=sys.stderr)
        sys.exit(1)

    if args.list:
        _print_listing(args.file, entries)
        sys.exit(0)

    errors = 0
    for entry in sorted(entries, key=lambda e: e.filename):
        target = os.path.join(args.dest, entry.filename)
        if not args.quiet:
            print(f" extracting: {target}")
        try:
            fmt.extract_entry(args.file, entry, args.dest)
        except Exception as e:
            print(f"{parser.prog}: error: {e}", file=sys.stderr)
            errors += 1

    sys.exit(0 if errors == 0 else 2)


if __name__ == "__main__":
    main()
