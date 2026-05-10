# HROT-GUI-Tools

> A modern, dark-themed GUI plus drop-in CLI tools for HROT `.pak` archives.
> Pure Python — no third-party dependencies, no install step.

`HROT-GUI-Tools` lets you inspect, extract, and create the `.pak` archives used by
[HROT](https://store.steampowered.com/app/824600/HROT/) (the retro-FPS by
Spytihněv).

## Files

Just four `.py` files plus this README. Drop them in a folder, run them.

| File         | What it is                                                                |
| ------------ | ------------------------------------------------------------------------- |
| `format.py`  | The `.pak` reader/writer — pure stdlib, used by everything else.          |
| `pak.py`     | CLI: add files to (or create) a `.pak`.                                   |
| `unpak.py`   | CLI: list or extract files from a `.pak`.                                 |
| `main.py`    | The GUI — theme, embedded logo, main window. All in one file.             |

`pak.py`, `unpak.py`, and `main.py` each `import format`, so all four
files need to live in the same directory.

## Credits & lineage

The `pak` and `unpak` CLI surface — flag names, semantics, help text, and
stdin behaviour — is preserved verbatim from
**[joshuaskelly/hrot-cli-tools](https://github.com/joshuaskelly/hrot-cli-tools)**
by Joshua Skelly (MIT, 2020). If all you need is the original CLI, install
his package directly with `pip install hrot-cli-tools`.

This project re-implements that surface on a self-contained pure-stdlib
`.pak` reader/writer (no `vgio` runtime dependency) and adds a graphical
interface plus a few quality-of-life fixes.

## Run it

Requires Python 3.7+. Tkinter ships with Python on Windows and macOS; on
Debian/Ubuntu Linux install it once with `sudo apt install python3-tk`.

```sh
python3 main.py                    # GUI
python3 main.py PAK0.PAK           # GUI, pre-loaded with an archive

python3 unpak.py PAK0.PAK -l                # list contents
python3 unpak.py PAK0.PAK -d ./out          # extract to ./out
python3 pak.py mymod.pak file1.png file2    # add files
find ./mod -type f | python3 pak.py mymod.pak   # add via stdin pipe
```

No `pip install` step. No `setup.py`. If you want shorter command names,
either `chmod +x` the files and add a shebang, or alias them in your shell:

```sh
alias pak='python3 /path/to/pak.py'
alias unpak='python3 /path/to/unpak.py'
```

### Linux file-dialog tip

The GUI uses native file dialogs through `kdialog` (KDE) or `zenity`
(GNOME/GTK) when one is available, and falls back to Tk's built-in file
picker otherwise. CachyOS, Arch with KDE, Fedora KDE, and most mainstream
distros ship one of these by default. If file pickers misbehave, install
one and restart the app:

```sh
sudo pacman -S kdialog        # Arch / CachyOS / KDE
sudo apt install kdialog      # Debian / Ubuntu / KDE
sudo apt install zenity       # Debian / Ubuntu / GNOME
```

A startup line on stderr tells you which backend was picked and why,
which helps diagnose dialog issues:

```
[hrot-pak] using native dialogs: kdialog (KDE detected (XDG_CURRENT_DESKTOP='KDE'))
```

## Features inherited from joshuaskelly/hrot-cli-tools

These are the original tool's features, kept exactly as they were:

- **`pak <file.pak> [list...]`** — add files to (or create) a `.pak` archive.
- **`pak <file.pak>` with no list** — read filenames from `stdin`, one per
  line, ANSI-stripped. Lets you pipe in `find` output:
  `find ./mod -type f | python3 pak.py mymod.pak`
- **`unpak <file.pak>`** — extract every file to the current directory.
- **`unpak <file.pak> -d <xdir>`** — extract to `<xdir>` instead.
- **`unpak <file.pak> -l`** — list the archive's contents in a fixed-width
  table with sizes and a row total.
- **`-q` / `--quiet`** on both tools — silence per-file progress output.
- **`-v` / `--version`** — print the tool name and version.
- Helpful error reporting (the parser prints help on misuse rather than
  just a one-line `usage:` message).

## New features in this version

### Graphical interface (`main.py`)

#### Look and feel

- **Custom dark sepia theme** with a warm-brown palette derived from the
  project logo (no generic slate-grey "VS Code dark" defaults). Every
  text element passes WCAG AA contrast or better; most score AAA.
- **Sidebar layout** with the project logo, wordmark, version, and
  one-click action buttons grouped into Read, Create, and Add sections.
- **Hover hints on every sidebar button.** A small tooltip appears after a
  short hover, describing what the button does. Themed to match the rest
  of the UI.
- **Live stat strip** in the header showing archive name, file count, and
  total uncompressed size.
- **Sortable file table** with zebra striping, monospaced filenames for
  readability, and click-to-sort on Name / Size headers.
- **Live filter** input that narrows the visible file list as you type.

#### Reading and extracting

- **Multi-select extraction** — pick any subset of files and extract just
  those, or use Extract All.
- **Extracts into a pak-named subfolder.** Extracting `PAK0.PAK` to
  `~/Downloads` creates `~/Downloads/PAK0/` rather than spraying files
  directly into the destination. Re-extracting the same archive produces
  `PAK0 (2)/`, `PAK0 (3)/`, browser-download style.
- **Threaded extraction and packing** — large archives don't freeze the
  window; a progress bar and live status line track per-file work.
- **Double-click a row** to extract the selection straight away.
- **Pre-load an archive on launch** — `python3 main.py PAK0.PAK` opens
  with that archive already loaded.

#### Creating and editing

The Create/Add operations are split into four explicit buttons so you
always know what each one does at a glance:

| Button             | What it does                                                          |
| ------------------ | --------------------------------------------------------------------- |
| **From Files…**    | Build a new `.pak` from individual files you pick.                    |
| **From Folder…**   | Build a new `.pak` containing every file in a folder, recursively.    |
| **Add Files…**     | Append individual files to the currently-open `.pak`.                 |
| **Add Folder…**    | Append every file in a folder, recursively, to the open archive.      |

- **Sensible workflow order.** Create flows ask "what to include" before
  "where to save," matching the natural way you'd think about packing:
  pick what's going in, *then* pick a name and home for it.
- **Folder name suggested as the archive name.** Pick a folder called
  `mymod`, and the save dialog opens with `mymod.pak` already filled in.
- **Pre-pack confirmation.** Before any pack runs, a summary modal shows
  what's about to happen: file count, total size, and a preview of the
  first six entries. Cancel to back out without writing anything.
- **Skip-and-warn for over-long names.** HROT's `.pak` format limits
  archive names to 119 bytes. Files whose internal path exceeds that
  (rare, but possible with deeply-nested folders like `~/.cache/`) are
  flagged in the confirmation dialog and skipped from the pack rather
  than aborting the whole operation. You see exactly which files will
  be left out before committing.
- **Path validation on new archives.** The save path is normalized
  (`~` expanded, relative paths resolved), the extension fixed up
  (typed `mymod` becomes `mymod.pak`; typed `mymod.zip` prompts to
  rename), parent directory writability checked, and overwrite
  confirmed explicitly — all before the worker thread starts.
- **Append-mode packing** with same-name replacement. Adding a file
  whose archive name already exists in the open `.pak` replaces the
  older entry instead of leaving an orphan.

#### Errors, friendly

- **In-window error reporting.** Corrupt or non-HROT files give a clear
  modal instead of a stack trace. The "Packing failed" dialog shows just
  the user-relevant message; full tracebacks go to stderr where developers
  can find them.

### Quality-of-life CLI improvements

- **Atomic writes.** New archives are written to a `.tmp` sibling and
  renamed into place at the end. If the process crashes mid-write
  (Ctrl-C, OOM, power loss, an I/O error), the original archive is left
  byte-for-byte intact — there is no half-written state to recover from.
- **Streaming append.** Adding files to an existing archive copies the
  existing payloads through chunk-by-chunk; memory use stays bounded
  regardless of how large the original archive is.
- **No `vgio` runtime dependency.** The format is implemented in
  `format.py` (≈260 lines, stdlib only) and is byte-for-byte
  cross-compatible with `vgio.hrot.pak` in both directions — paks written
  by one tool are valid for the other.
- **No `tabulate` runtime dependency** — `unpak -l` renders its table
  from scratch in pure Python.
- **Streaming I/O** in 1 MiB chunks for both reading and writing, so
  multi-GB archives don't blow memory.
- **Validates the directory bounds on read** — corrupt headers fail with
  `BadPakFile` and a clear message, not an `IndexError` deep in `struct`.
- **Zip-slip protection** — archive entries with `..` traversal in the
  name are rejected before any bytes are written outside the destination
  directory.
- **`--version` works without a list argument.** In the original, calling
  `pak --version` or `pak --help` would block on stdin in non-tty contexts
  (because `read_from_stdin()` was eagerly evaluated when constructing the
  parser). This version reads stdin only after `parse_args()` returns and
  only when no `list` was provided on the command line.
- **Stricter exception handling** in `unpak`. The original used a bare
  `except:` around extraction, which silently swallowed `KeyboardInterrupt`
  and `SystemExit`. This version catches `Exception` only, and exits with
  status `2` if any file failed.
- **Append-mode safety** in `pak`. Adding a file under an existing archive
  name replaces the older entry instead of leaving an orphaned blob.

### Programmatic API

`format.py` is importable on its own:

```python
import format as fmt

if fmt.is_pakfile("PAK0.PAK"):
    for entry in fmt.read_pak("PAK0.PAK"):
        print(entry.filename, entry.size)
```

(Note: `format` shadows the Python builtin `format()` only within files
that import it this way. Rename the import if you need the builtin in the
same scope.)

## File format reference

```
Header (12 bytes)
    char    magic[4]            // b"HROT"
    int32   directory_offset    // little-endian
    int32   directory_size      // little-endian

File data
    Raw bytes for each archived file, packed back-to-back.

Directory (one entry per file, 128 bytes each)
    char    filename[120]       // null-padded ASCII path, '/' separator
    int32   file_offset
    int32   file_size
```

This is the classic Quake PAK layout with the magic changed from
`b"PACK"` to `b"HROT"` and the filename field widened from 56 to 120
bytes.

## License

MIT, matching joshuaskelly/hrot-cli-tools.
