"""HROT PAK Tool — dark-themed GUI for inspecting, extracting, and creating
HROT .pak archives.

Run with:
    python3 hrotpak.py [path/to/file.pak]

This file bundles three things that were previously separate modules:
the version string, the embedded brand logo, and the theme + window code.
The pak format reader/writer lives next to this file in `format.py`; the
two CLIs `pak.py` and `unpak.py` import the same format module.

Public surface, if importing this as a library:
    main()              — launch the application
    PakGUI              — the Tk window class
    apply_theme(root)   — apply the dark theme to any Tk root
    COLORS              — palette dict
    load_logo(master)   — return a Tk PhotoImage of the embedded logo
"""

from __future__ import annotations

import base64
import os
import shutil
import subprocess
import sys
import threading
import traceback
from typing import List, Optional

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from tkinter import font as tkfont

# Sibling-module import. `format` shadows the Python builtin within this
# file, but nothing here calls the builtin format(), so the shadow is harmless.
import format as fmt


__version__ = "1.0"


# ===========================================================================
# Embedded logo
# ===========================================================================
#
# The logo is bundled as a base64 PNG so this file is self-contained.
# Tk's built-in PhotoImage reads PNG since Python 3.4 — no Pillow needed.
# Source: cropped, rasterized from the project's logo.svg via rsvg-convert
# at 96 px tall.

_LOGO_PNG_B64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAGkAAABgCAYAAAAejVzyAAAABmJLR0QA/wD/AP+gvaeTAAAF"
    "RElEQVR4nO3dW0xbdRwH8O/pOS29MVpKx/YizDF2Q4gaQ7YZTRYTH4wxMcYH4/tMSObDEh90"
    "MVvExL2YLEpQmJuwRtyI29yGwU3cshgvWUBAou7CZQPigJKNAe3h9Fx82KjUnt5Yzyn/8vu80"
    "Pb8z+//gy/n9JzTpgUIIYQQQgghhBBCCCGEEEIIIYQYiwOA3TVl+wtt/L5cN0NizUmo7eobu"
    "i4AgABscNoET66bIrHui2IhAFiSDZIVDfOSDFXTX65BQ1hSIMkJBgCIKCpCkpKwBklNSLTg9t"
    "0wJmcXAAA8x6HM50Cx0xZdPr+gYDA4D0lRAQAeh4ANPhd4CwcA0DTg1t0QgnPSg4ksHMp9Lng"
    "cCackCehuScE5KRoQACiahpHpUDQQTQMGp+ei9wHgXljG+IwYvT85txANCABkVcPw9DwiS9Yh"
    "6dEN6Z4YiXtM1YCZsAwACEX0d3Ez4Yju7UWKqmF2QVl2s6uVbkg8x+kO5i2xP+OKWTjd27G1M"
    "+iOAEgQkt9tw///ljbegiK7FQBgF3gU2uOfW9a6/3vO8i+5vajAyqPwYQ2SPt2Q3AUCNvrdcN"
    "kECBYOHoeAzaXu6EEBAFSUuFDissHKW2AXeJR5HfC7C6LLi+xWbPQ74bTxEHgOXqcVlWtdSLC"
    "BkSQSHmp5HAI8DnfCFXkLh3KfM2lxr8MGryN+iyKZSXqeRFYGAQBmRXUkLIupxhKTLSjKLPAw"
    "pGBIHEPcoQLJNU5T5gHa3TGBQmIAhcQACokBFBIDKCQGUEgMoJAYQCExgEJiQMZvOHisrBw1T"
    "z6FkhI/rFbjrnBHIhKmp4MY6O/H0OANw+ZhQdohVW7Ziv0H6lG7Y5eR/ega6O/DR/UHcPW3X0"
    "yfeyVIa3e389nncOLU+ZwEBABV1TVoaWvH62+8mZP5cy1lSKXr1uNwYzOcLpcZ/STE8wIO1h9"
    "C7Y6dOe0jF1KG9FbdXqxZU2RGLylZeB7vvv9BrtswXdKQOI7Diy+9bFYvadmybTu2bq/KdRum"
    "ShqSx+uFz1diVi9pq6quyXULpkoakttdaFYfGVmJ/zhGYvJk1mJhsu1lW12/LaMoJAYkveKgq"
    "iruz8xkVlAQMj6nEsNhSJKUeuDieHF1vf0saUjjY6N4pnpzRgWf3/0Cmo4FMlrn0IcH8dXxLz"
    "NaZzWh3R0DKCQGUEgMoJAYQCExgEJiAIXEAAqJARQSAygkBlBIDKCQGEAhMYBCYkDWQxq6eQO"
    "qSp/ElU1ZD2n09i1c+uFCRutoGn1iYTKG7O5ajx1Je6wsy7hy+Ucj2sgbhoT0688/4dpff6Y1"
    "9nT7CYyPjRrRRt4w7MDheMsXKceoioIjnzcY1ULeMOwDUc+d/gb73nkP3uLihGPOnGrHyPBQ2"
    "jUrNlXi8YpN2WhPlyiKuHKpy7D6y2VYSKIo4mRbAHvq9uouVxUFTY2fZlTzlVdfw566t7PRnq"
    "6pqUnsevoJw+ovl6HnSYGWo5BlWXfZ+bNnMDx408jp84ahIU1O3MHFzu/iHldVFc2Nnxg5dV4"
    "x/IpD69HmuMc6O87h+rW/jZ46bxgeUk/3VfT3/h69r2kaPms4bPS0ecWUa3eBJYfjFzo70j6H"
    "Ig+YElLH2W8xcecfAEBTAz0XZcqUL46Q5QhOtgWwraoaA3/0LbtO18XvMTExkcXOYoVDIcNqP"
    "wrTvt3j60ArStetf6QavT3d6O3pzlJH7DAtpGBwCsHglFnT5RV60Y8BFBIDKCQGUEgMoJAYQC"
    "ExgEJiAIXEAAqJARQSAygkBggAwIEfUKF+nOtmSCzNrs0CwL/yW2fGnkt96wAAAABJRU5ErkJ"
    "ggg=="
)


def logo_bytes() -> bytes:
    """Return the raw PNG bytes of the bundled logo."""
    return base64.b64decode(_LOGO_PNG_B64)


def load_logo(master: Optional[tk.Misc] = None,
              subsample: int = 1) -> tk.PhotoImage:
    """Return a Tk PhotoImage of the logo, optionally subsampled (2 = half)."""
    img = tk.PhotoImage(master=master, data=_LOGO_PNG_B64)
    if subsample > 1:
        img = img.subsample(subsample, subsample)
    return img


# ===========================================================================
# Theme
# ===========================================================================
#
# The palette is taken directly from the project logo:
#
#     #0f0a07  void          deepest background
#     #1a120c  surface       main panel background
#     #251d16  surface_2     raised surfaces; logo dark brown
#     #322419  surface_3     hover / selected row
#     #593b26  accent        logo light brown — primary brand
#     #8a6a4f  accent_2      warm secondary
#     #d9c8b4  text          warm off-white, easier on the eyes than #fff
#     #8c7e6d  text_dim      muted
#     #f0c674  highlight     sepia gold — focus rings, headings, progress
#
# The aesthetic direction is intentional: warm, dark-brown / sepia-modern,
# not the generic slate-gray that every "VS Code dark" UI defaults to.

COLORS = {
    "void":       "#0f0a07",
    "surface":    "#1a120c",
    "surface_2":  "#251d16",
    "surface_3":  "#322419",
    "accent":     "#593b26",
    "accent_2":   "#8a6a4f",
    "text":       "#d9c8b4",
    "text_dim":   "#9d8d7a",
    "highlight":  "#f0c674",
    "danger":     "#d97a5b",
    "border":     "#2d2118",
}

# Distinctive font candidates — fall back gracefully across platforms.
TITLE_FONT_CANDIDATES = ("Iosevka", "JetBrains Mono", "IBM Plex Mono",
                          "SF Mono", "Menlo", "Consolas", "Courier")
BODY_FONT_CANDIDATES = ("SF Pro Text", "Segoe UI Variable", "Segoe UI",
                         "Inter", "Helvetica Neue", "Helvetica", "Arial")


def _pick_font(root: tk.Misc, candidates) -> str:
    available = set(tkfont.families(root))
    for name in candidates:
        if name in available:
            return name
    return candidates[-1]


def apply_theme(root: tk.Tk) -> dict:
    """Apply the dark theme to `root`. Return {'colors': ..., 'fonts': ...}."""
    title_face = _pick_font(root, TITLE_FONT_CANDIDATES)
    body_face = _pick_font(root, BODY_FONT_CANDIDATES)

    fonts = {
        "title":   (title_face, 16, "bold"),
        "h2":      (title_face, 11, "bold"),
        "body":    (body_face, 10),
        "body_b":  (body_face, 10, "bold"),
        "small":   (body_face, 9),
        "mono":    (title_face, 10),
    }

    root.configure(bg=COLORS["surface"])

    # Tk-level palette so native widgets (menus, dialogs) pick up dark colours.
    root.tk_setPalette(
        background=COLORS["surface"],
        foreground=COLORS["text"],
        activeBackground=COLORS["surface_3"],
        activeForeground=COLORS["text"],
        highlightBackground=COLORS["accent"],
        highlightColor=COLORS["highlight"],
        selectBackground=COLORS["accent"],
        selectForeground=COLORS["text"],
    )

    style = ttk.Style(root)
    # 'clam' is the only built-in theme that fully respects custom
    # background/foreground colours on every platform.
    style.theme_use("clam")

    style.configure(".",
                    background=COLORS["surface"],
                    foreground=COLORS["text"],
                    fieldbackground=COLORS["surface_2"],
                    bordercolor=COLORS["border"],
                    lightcolor=COLORS["surface_2"],
                    darkcolor=COLORS["surface"],
                    troughcolor=COLORS["surface_2"],
                    selectbackground=COLORS["accent"],
                    selectforeground=COLORS["text"],
                    font=fonts["body"])

    # Frames & labels
    style.configure("TFrame", background=COLORS["surface"])
    style.configure("Surface.TFrame", background=COLORS["surface_2"])
    style.configure("Sidebar.TFrame", background=COLORS["void"])
    style.configure("TLabel", background=COLORS["surface"], foreground=COLORS["text"])
    style.configure("Sidebar.TLabel", background=COLORS["void"], foreground=COLORS["text"])
    style.configure("Brand.TLabel", background=COLORS["void"],
                    foreground=COLORS["highlight"], font=fonts["title"])
    style.configure("Tagline.TLabel", background=COLORS["void"],
                    foreground=COLORS["text_dim"], font=fonts["small"])
    style.configure("Status.TLabel", background=COLORS["surface_2"],
                    foreground=COLORS["text_dim"], font=fonts["small"],
                    padding=(10, 4))
    style.configure("StatPrimary.TLabel", background=COLORS["surface_2"],
                    foreground=COLORS["highlight"], font=fonts["h2"])
    style.configure("StatSecondary.TLabel", background=COLORS["surface_2"],
                    foreground=COLORS["text_dim"], font=fonts["small"])

    # Buttons
    style.configure("TButton",
                    background=COLORS["surface_2"],
                    foreground=COLORS["text"],
                    borderwidth=1,
                    focusthickness=1,
                    focuscolor=COLORS["highlight"],
                    padding=(12, 7),
                    font=fonts["body"])
    style.map("TButton",
              background=[("active", COLORS["surface_3"]),
                          ("pressed", COLORS["accent"])],
              foreground=[("active", COLORS["text"])],
              bordercolor=[("active", COLORS["accent_2"])])

    style.configure("Accent.TButton",
                    background=COLORS["accent"],
                    foreground=COLORS["text"],
                    padding=(14, 8),
                    font=fonts["body_b"])
    style.map("Accent.TButton",
              background=[("active", COLORS["accent_2"]),
                          ("pressed", COLORS["highlight"])],
              foreground=[("pressed", COLORS["surface"])])

    style.configure("Sidebar.TButton",
                    background=COLORS["void"],
                    foreground=COLORS["text"],
                    borderwidth=0,
                    padding=(14, 9),
                    anchor="w",
                    font=fonts["body"])
    style.map("Sidebar.TButton",
              background=[("active", COLORS["surface_2"]),
                          ("pressed", COLORS["accent"])])

    # Entry — explicit field+text+highlight thickness so clam doesn't override
    # the field background to the OS default light colour.
    style.configure("TEntry",
                    fieldbackground=COLORS["surface_2"],
                    foreground=COLORS["text"],
                    background=COLORS["surface_2"],
                    bordercolor=COLORS["border"],
                    lightcolor=COLORS["border"],
                    darkcolor=COLORS["border"],
                    insertcolor=COLORS["highlight"],
                    padding=8,
                    relief="flat")
    style.map("TEntry",
              fieldbackground=[("readonly", COLORS["surface_2"]),
                               ("focus", COLORS["surface_3"])],
              bordercolor=[("focus", COLORS["accent_2"])],
              lightcolor=[("focus", COLORS["accent_2"])],
              darkcolor=[("focus", COLORS["accent_2"])])

    # Combobox — used by Tk's pure-Tcl file dialog (the directory picker).
    # The text-entry portion is a ttk widget and styles like TEntry, but the
    # popdown is a classic Listbox that ttk::style cannot reach; that one is
    # handled via option_add further down.
    style.configure("TCombobox",
                    fieldbackground=COLORS["surface_2"],
                    foreground=COLORS["text"],
                    background=COLORS["surface_2"],
                    bordercolor=COLORS["border"],
                    lightcolor=COLORS["border"],
                    darkcolor=COLORS["border"],
                    arrowcolor=COLORS["text"],
                    selectbackground=COLORS["accent"],
                    selectforeground=COLORS["text"],
                    insertcolor=COLORS["highlight"],
                    padding=6)
    style.map("TCombobox",
              fieldbackground=[("readonly", COLORS["surface_2"]),
                               ("focus", COLORS["surface_3"])],
              foreground=[("readonly", COLORS["text"]),
                          ("disabled", COLORS["text_dim"])],
              bordercolor=[("focus", COLORS["accent_2"])],
              arrowcolor=[("active", COLORS["highlight"])])

    # Spinbox — defence in depth; not used by our own UI but the file dialog
    # may use one in some Tk builds.
    style.configure("TSpinbox",
                    fieldbackground=COLORS["surface_2"],
                    foreground=COLORS["text"],
                    background=COLORS["surface_2"],
                    bordercolor=COLORS["border"],
                    arrowcolor=COLORS["text"],
                    insertcolor=COLORS["highlight"],
                    padding=6)
    style.map("TSpinbox",
              fieldbackground=[("focus", COLORS["surface_3"])],
              bordercolor=[("focus", COLORS["accent_2"])],
              arrowcolor=[("active", COLORS["highlight"])])

    # Classic Tk widgets — option_add reaches widgets that ttk::style can't.
    # Tk's scripted file dialog (the Linux fallback) builds its directory
    # listing from a classic Listbox, its filename field from a classic
    # Entry, and the combobox dropdown is also a classic Listbox. None of
    # those inherit ttk styling, so without these option_add calls they
    # render with clam's default light grey on white — a clash against the
    # surrounding dark theme.
    root.option_add("*TCombobox*Listbox.background", COLORS["surface_2"])
    root.option_add("*TCombobox*Listbox.foreground", COLORS["text"])
    root.option_add("*TCombobox*Listbox.selectBackground", COLORS["accent"])
    root.option_add("*TCombobox*Listbox.selectForeground", COLORS["text"])
    root.option_add("*TCombobox*Listbox.borderWidth", 0)
    root.option_add("*TCombobox*Listbox.relief", "flat")
    root.option_add("*Listbox.background", COLORS["surface_2"])
    root.option_add("*Listbox.foreground", COLORS["text"])
    root.option_add("*Listbox.selectBackground", COLORS["accent"])
    root.option_add("*Listbox.selectForeground", COLORS["text"])
    root.option_add("*Listbox.highlightBackground", COLORS["border"])
    root.option_add("*Listbox.highlightColor", COLORS["accent_2"])
    root.option_add("*Listbox.borderWidth", 0)
    root.option_add("*Entry.background", COLORS["surface_2"])
    root.option_add("*Entry.foreground", COLORS["text"])
    root.option_add("*Entry.insertBackground", COLORS["highlight"])
    root.option_add("*Entry.selectBackground", COLORS["accent"])
    root.option_add("*Entry.selectForeground", COLORS["text"])
    root.option_add("*Entry.highlightBackground", COLORS["border"])
    root.option_add("*Entry.highlightColor", COLORS["accent_2"])

    # Treeview — the file list
    style.configure("Treeview",
                    background=COLORS["surface_2"],
                    foreground=COLORS["text"],
                    fieldbackground=COLORS["surface_2"],
                    bordercolor=COLORS["border"],
                    rowheight=26,
                    font=fonts["mono"])
    style.map("Treeview",
              background=[("selected", COLORS["accent"])],
              foreground=[("selected", COLORS["text"])])
    style.configure("Treeview.Heading",
                    background=COLORS["surface_2"],
                    foreground=COLORS["highlight"],
                    bordercolor=COLORS["border"],
                    relief="flat",
                    padding=(10, 8),
                    font=fonts["small"])
    style.map("Treeview.Heading",
              background=[("active", COLORS["surface_3"])],
              foreground=[("active", COLORS["text"])])

    # Scrollbar
    style.configure("Vertical.TScrollbar",
                    background=COLORS["surface_2"],
                    troughcolor=COLORS["surface"],
                    bordercolor=COLORS["surface"],
                    arrowcolor=COLORS["text_dim"],
                    gripcount=0)
    style.map("Vertical.TScrollbar",
              background=[("active", COLORS["accent"])])

    # Progressbar
    style.configure("Horizontal.TProgressbar",
                    background=COLORS["highlight"],
                    troughcolor=COLORS["surface"],
                    bordercolor=COLORS["surface"],
                    lightcolor=COLORS["highlight"],
                    darkcolor=COLORS["highlight"])

    style.configure("TSeparator", background=COLORS["border"])

    return {"colors": COLORS, "fonts": fonts}


# ===========================================================================
# Helpers
# ===========================================================================

def _human_size(n: int) -> str:
    """Format a byte count as a short human string (e.g. '4.0 KB')."""
    if n < 1024:
        return f"{n:,d} B"
    units = ("KB", "MB", "GB", "TB")
    val = float(n)
    for unit in units:
        val /= 1024
        if val < 1024 or unit == units[-1]:
            return f"{val:,.1f} {unit}"
    return f"{val:,.1f} TB"  # unreachable; appeases the type checker


# ===========================================================================
# Native-dialog fallback (Linux only)
# ===========================================================================
#
# Tk has no native file picker on Linux X11 — it uses a pure-Tcl scripted
# dialog whose directory-selector combobox has a popup that vanishes on
# certain window managers (KDE/Plasma in particular). The popup's overlay
# toplevel races with focus events from its parent and dismisses itself.
#
# This isn't fixable from the application side: the bug lives in the Tcl
# bindings of `ttk::combobox::Post`, which makes the popdown a `wm transient`
# of the file dialog toplevel. So instead, on Linux we shell out to a real
# native dialog tool (kdialog on KDE, zenity on GNOME/GTK) and only fall back
# to Tk's scripted dialog if neither is installed.
#
# Windows and macOS use truly native dialogs through Tk itself, so this
# module does nothing there.

def _detect_native_dialog():
    """Return ('kdialog' | 'zenity' | None, reason_string).

    Picked once at import. The reason string explains *why* this backend
    was chosen, so the startup diagnostic can show it on stderr — useful
    when 'nothing happens' bug reports come in.
    """
    if sys.platform != "linux":
        return None, "not Linux"

    has_kdialog = bool(shutil.which("kdialog"))
    has_zenity = bool(shutil.which("zenity"))

    # Read every signal that might indicate a KDE session. KDE_FULL_SESSION
    # is the legacy X11-era marker (often unset on Plasma 6 / Wayland).
    # XDG_CURRENT_DESKTOP is the modern cross-DE standard. We treat any
    # of them as "this is KDE, prefer kdialog if installed."
    desktop = (os.environ.get("XDG_CURRENT_DESKTOP") or "").lower()
    is_kde = (
        os.environ.get("KDE_FULL_SESSION") == "true"
        or "kde" in desktop
        or os.environ.get("DESKTOP_SESSION", "").lower().startswith("plasma")
    )

    if is_kde and has_kdialog:
        return "kdialog", f"KDE detected (XDG_CURRENT_DESKTOP={desktop!r})"

    if has_zenity:
        return "zenity", f"zenity available, KDE not detected (XDG_CURRENT_DESKTOP={desktop!r})"

    if has_kdialog:
        return "kdialog", "only kdialog available"

    return None, "no kdialog or zenity in PATH"


_NATIVE_DIALOG, _NATIVE_DIALOG_REASON = _detect_native_dialog()


def _print_dialog_diagnostic():
    """Print a one-liner to stderr at startup describing the dialog backend.
    Visible only when the app is launched from a terminal — silent otherwise.
    Helps diagnose 'nothing happens when I click a button' reports.
    """
    if sys.platform != "linux":
        return  # Windows/macOS use OS-native dialogs through Tk; nothing to report
    if _NATIVE_DIALOG:
        print(f"[hrot-pak] using native dialogs: {_NATIVE_DIALOG} "
              f"({_NATIVE_DIALOG_REASON})",
              file=sys.stderr)
    else:
        print(
            f"[hrot-pak] no native dialog tool: {_NATIVE_DIALOG_REASON}. "
            "Falling back to Tk's scripted file dialog. "
            "If file pickers misbehave on your desktop, install kdialog "
            "(KDE) or zenity (GNOME/GTK).",
            file=sys.stderr,
        )


_print_dialog_diagnostic()


def _filetypes_to_kdialog(filetypes):
    """Convert Tk filetypes into kdialog's `'NAME (*.ext1 *.ext2)|...'` form."""
    if not filetypes:
        return None
    parts = []
    for name, patterns in filetypes:
        if isinstance(patterns, str):
            patterns = patterns.split()
        parts.append(f"{name} ({' '.join(patterns)})")
    return "|".join(parts)


def _filetypes_to_zenity(filetypes):
    """Yield zenity --file-filter= arguments for each Tk filetype entry."""
    args = []
    for name, patterns in filetypes or []:
        if isinstance(patterns, str):
            patterns = patterns.split()
        args.append(f"--file-filter={name} | {' '.join(patterns)}")
    return args


def _run_native(argv):
    """Run a native-dialog command. Returns:

    - the stdout string (possibly '') on success or user-cancel
    - None if the tool failed in a way that suggests we should fall back
      to the Tk dialog (e.g. command vanished from PATH between detection
      and use, or it crashed/segfaulted).

    The kdialog/zenity convention: exit 0 = picked something (or empty for
    nothing), exit 1 = user cancelled (clean), other non-zero = tool error.
    """
    try:
        result = subprocess.run(
            argv,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        # FileNotFoundError (binary disappeared), permission, etc.
        return None
    if result.returncode == 0:
        return result.stdout.strip()
    if result.returncode == 1:
        # Exit 1 is the documented "user cancelled" code, but if stderr
        # has content, the tool may actually have failed silently — surface
        # it so a developer running from a terminal can see what happened.
        if result.stderr.strip():
            sys.stderr.write(
                f"[{argv[0]}] exited 1 with stderr: {result.stderr.strip()}\n"
            )
        return ""  # treat as cancel; propagate as empty selection
    # Any other non-zero exit code is a tool error. Print stderr to console
    # so a developer running from a terminal can see what went wrong, then
    # fall through to Tk.
    if result.stderr:
        sys.stderr.write(
            f"[{argv[0]}] exited {result.returncode}: {result.stderr.strip()}\n"
        )
    return None


def _native_open(title=None, filetypes=None, initialdir=None, **_ignored):
    if _NATIVE_DIALOG == "kdialog":
        argv = ["kdialog", "--getopenfilename", initialdir or os.path.expanduser("~")]
        f = _filetypes_to_kdialog(filetypes)
        if f:
            argv.append(f)
        if title:
            argv += ["--title", title]
        return _run_native(argv)
    if _NATIVE_DIALOG == "zenity":
        argv = ["zenity", "--file-selection"]
        if title:
            argv.append(f"--title={title}")
        if initialdir:
            argv.append(f"--filename={os.path.join(initialdir, '')}")
        argv += _filetypes_to_zenity(filetypes)
        return _run_native(argv)
    return None  # signal "not handled, fall back to Tk"


def _native_open_many(title=None, filetypes=None, initialdir=None, **_ignored):
    if _NATIVE_DIALOG == "kdialog":
        argv = ["kdialog", "--multiple", "--separate-output",
                "--getopenfilename",
                initialdir or os.path.expanduser("~")]
        f = _filetypes_to_kdialog(filetypes)
        if f:
            argv.append(f)
        if title:
            argv += ["--title", title]
        out = _run_native(argv)
        if out is None:        # tool failure → fall through to Tk
            return None
        return tuple(line for line in out.splitlines() if line)
    if _NATIVE_DIALOG == "zenity":
        argv = ["zenity", "--file-selection", "--multiple", "--separator=\n"]
        if title:
            argv.append(f"--title={title}")
        if initialdir:
            argv.append(f"--filename={os.path.join(initialdir, '')}")
        argv += _filetypes_to_zenity(filetypes)
        out = _run_native(argv)
        if out is None:
            return None
        return tuple(line for line in out.splitlines() if line)
    return None


def _native_save(title=None, filetypes=None, initialdir=None,
                 initialfile=None, defaultextension=None, **_ignored):
    if _NATIVE_DIALOG == "kdialog":
        start = initialdir or os.path.expanduser("~")
        if initialfile:
            start = os.path.join(start, initialfile)
        argv = ["kdialog", "--getsavefilename", start]
        f = _filetypes_to_kdialog(filetypes)
        if f:
            argv.append(f)
        if title:
            argv += ["--title", title]
        path = _run_native(argv)
        if path and defaultextension and not os.path.splitext(path)[1]:
            path += defaultextension
        return path
    if _NATIVE_DIALOG == "zenity":
        argv = ["zenity", "--file-selection", "--save"]
        if title:
            argv.append(f"--title={title}")
        if initialdir or initialfile:
            start = os.path.join(initialdir or "", initialfile or "")
            argv.append(f"--filename={start}")
        argv += _filetypes_to_zenity(filetypes)
        path = _run_native(argv)
        if path and defaultextension and not os.path.splitext(path)[1]:
            path += defaultextension
        return path
    return None


def _native_dir(title=None, initialdir=None, **_ignored):
    if _NATIVE_DIALOG == "kdialog":
        argv = ["kdialog", "--getexistingdirectory",
                initialdir or os.path.expanduser("~")]
        if title:
            argv += ["--title", title]
        return _run_native(argv)
    if _NATIVE_DIALOG == "zenity":
        argv = ["zenity", "--file-selection", "--directory"]
        if title:
            argv.append(f"--title={title}")
        if initialdir:
            argv.append(f"--filename={os.path.join(initialdir, '')}")
        return _run_native(argv)
    return None


# ===========================================================================
# Tooltip
# ===========================================================================
#
# Lightweight hover hint. Used on the sidebar buttons so the action a button
# performs is visible before clicking. Pure Tk, no dependencies.
#
# The tooltip is an `overrideredirect` Toplevel that appears after a short
# delay (so casual mouse passes don't trigger it), follows the widget rather
# than the cursor, and disappears when the mouse leaves the widget OR when
# the widget is clicked (so the tooltip doesn't linger over the action it
# was describing).

class Tooltip:
    """Attach to any widget. Shows `text` after `delay_ms` of hover."""

    DELAY_MS = 500

    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self._after_id = None
        self._tip = None
        widget.bind("<Enter>", self._on_enter, add="+")
        widget.bind("<Leave>", self._on_leave, add="+")
        widget.bind("<ButtonPress>", self._on_leave, add="+")

    def _on_enter(self, _event=None):
        self._cancel()
        self._after_id = self.widget.after(self.DELAY_MS, self._show)

    def _on_leave(self, _event=None):
        self._cancel()
        self._hide()

    def _cancel(self):
        if self._after_id is not None:
            try:
                self.widget.after_cancel(self._after_id)
            except Exception:
                pass
            self._after_id = None

    def _show(self):
        if self._tip is not None:
            return
        # Anchor to the right edge of the widget, vertically centered with
        # the button. Falls back gracefully if winfo_* fails (widget gone).
        try:
            x = self.widget.winfo_rootx() + self.widget.winfo_width() + 8
            y = (self.widget.winfo_rooty()
                 + self.widget.winfo_height() // 2)
        except tk.TclError:
            return

        tip = tk.Toplevel(self.widget)
        tip.wm_overrideredirect(True)
        # Some WMs need this to keep the tooltip above other windows.
        try:
            tip.wm_attributes("-topmost", True)
        except tk.TclError:
            pass

        frame = tk.Frame(
            tip,
            background=COLORS["surface_3"],
            highlightthickness=1,
            highlightbackground=COLORS["accent_2"],
            bd=0,
        )
        frame.pack()
        tk.Label(
            frame,
            text=self.text,
            background=COLORS["surface_3"],
            foreground=COLORS["text"],
            font=("TkDefaultFont", 9),
            padx=10,
            pady=6,
            justify="left",
        ).pack()

        # We placed the tooltip at button's right edge; nudge it down by half
        # its own height so it's vertically centered.
        tip.update_idletasks()
        y -= tip.winfo_height() // 2
        tip.wm_geometry(f"+{x}+{y}")
        self._tip = tip

    def _hide(self):
        if self._tip is not None:
            try:
                self._tip.destroy()
            except Exception:
                pass
            self._tip = None


# ===========================================================================
# Main window
# ===========================================================================

class PakGUI(tk.Tk):
    """Top-level window: sidebar (logo + actions) + main panel (file table)."""

    def __init__(self):
        super().__init__()
        self.title("HROT PAK Tool")
        self.geometry("960x620")
        self.minsize(760, 480)

        ctx = apply_theme(self)
        self.colors = ctx["colors"]
        self.fonts = ctx["fonts"]

        # Window icon — uses the embedded logo.
        try:
            self._icon_img = load_logo(self, subsample=2)
            self.iconphoto(True, self._icon_img)
        except Exception:
            self._icon_img = None

        self.current_pak: Optional[str] = None
        self._all_entries: List[fmt.PakEntry] = []

        self._build_menu()
        self._build_layout()
        self._set_status("Open a .pak file to begin.")

    # ----- menu -----------------------------------------------------------

    def _build_menu(self):
        menubar = tk.Menu(self,
                          background=self.colors["surface_2"],
                          foreground=self.colors["text"],
                          activebackground=self.colors["accent"],
                          activeforeground=self.colors["text"],
                          borderwidth=0)

        def submenu():
            return tk.Menu(menubar, tearoff=0,
                           background=self.colors["surface_2"],
                           foreground=self.colors["text"],
                           activebackground=self.colors["accent"],
                           activeforeground=self.colors["text"],
                           borderwidth=0)

        filemenu = submenu()
        filemenu.add_command(label="Open .pak…", accelerator="Ctrl+O",
                             command=self.action_open)
        filemenu.add_separator()
        filemenu.add_command(label="Extract All…", command=self.action_extract_all)
        filemenu.add_command(label="Extract Selected…",
                             command=self.action_extract_selected)
        filemenu.add_separator()
        filemenu.add_command(label="Create New PAK from Files…",
                             command=self.action_create_pak_from_files)
        filemenu.add_command(label="Create New PAK from Folder…",
                             command=self.action_create_pak_from_folder)
        filemenu.add_separator()
        filemenu.add_command(label="Add Files to Open PAK…",
                             command=self.action_add_files)
        filemenu.add_command(label="Add Folder to Open PAK…",
                             command=self.action_add_folder)
        filemenu.add_separator()
        filemenu.add_command(label="Quit", command=self.destroy)
        menubar.add_cascade(label="File", menu=filemenu)

        helpmenu = submenu()
        helpmenu.add_command(label="About", command=self._about)
        menubar.add_cascade(label="Help", menu=helpmenu)

        self.config(menu=menubar)
        self.bind_all("<Control-o>", lambda e: self.action_open())

    # ----- layout ---------------------------------------------------------

    def _build_layout(self):
        self.columnconfigure(0, weight=0)
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)

        sidebar = ttk.Frame(self, style="Sidebar.TFrame", width=220)
        sidebar.grid(row=0, column=0, sticky="ns")
        sidebar.grid_propagate(False)

        main = ttk.Frame(self, style="TFrame")
        main.grid(row=0, column=1, sticky="nsew")

        self._build_sidebar(sidebar)
        self._build_main(main)

    def _build_sidebar(self, parent: ttk.Frame):
        # Brand block: logo + wordmark
        brand = ttk.Frame(parent, style="Sidebar.TFrame", padding=(18, 22, 18, 18))
        brand.pack(fill=tk.X)

        try:
            self._sidebar_logo = load_logo(self)
            ttk.Label(brand, image=self._sidebar_logo,
                      style="Sidebar.TLabel").pack(anchor="w")
        except Exception:
            pass

        ttk.Label(brand, text="HROT PAK",
                  style="Brand.TLabel").pack(anchor="w", pady=(10, 0))
        ttk.Label(brand, text=f"v{__version__}",
                  style="Tagline.TLabel").pack(anchor="w")

        ttk.Separator(parent, orient="horizontal").pack(fill=tk.X, padx=18, pady=4)

        # Sidebar action buttons
        actions = ttk.Frame(parent, style="Sidebar.TFrame", padding=(10, 8))
        actions.pack(fill=tk.X)

        def add(parent_frame, label, cmd, hint):
            btn = ttk.Button(parent_frame, text=label, style="Sidebar.TButton",
                             command=cmd)
            btn.pack(fill=tk.X, pady=1)
            Tooltip(btn, hint)
            return btn

        add(actions, "Open .pak", self.action_open,
            "Open an existing .pak archive to inspect or extract.")
        add(actions, "Extract All", self.action_extract_all,
            "Extract every file in the open archive into a folder of your choice.")
        add(actions, "Extract Selected", self.action_extract_selected,
            "Extract only the files you've selected in the table.\n"
            "Tip: Ctrl/Shift-click to multi-select.")

        ttk.Separator(parent, orient="horizontal").pack(fill=tk.X, padx=18, pady=8)

        actions2 = ttk.Frame(parent, style="Sidebar.TFrame", padding=(10, 0))
        actions2.pack(fill=tk.X)
        ttk.Label(actions2, text="CREATE NEW PAK",
                  style="Tagline.TLabel").pack(anchor="w", padx=4, pady=(4, 2))
        add(actions2, "From Files…", self.action_create_pak_from_files,
            "Build a new .pak from individual files you pick.\n"
            "You'll choose the files first, then the save location.")
        add(actions2, "From Folder…", self.action_create_pak_from_folder,
            "Build a new .pak containing every file in a folder (recursively).\n"
            "The folder's name is used as the default archive name.")

        ttk.Label(actions2, text="ADD TO OPEN PAK",
                  style="Tagline.TLabel").pack(anchor="w", padx=4, pady=(10, 2))
        add(actions2, "Add Files…", self.action_add_files,
            "Append individual files to the currently-open .pak archive.")
        add(actions2, "Add Folder…", self.action_add_folder,
            "Append every file in a folder (recursively) to the open archive.")

        # Footer hint
        footer = ttk.Frame(parent, style="Sidebar.TFrame", padding=(18, 12))
        footer.pack(side=tk.BOTTOM, fill=tk.X)
        ttk.Label(footer,
                  text="Pass a .pak path on the\ncommand line, or use\nthe Open button.",
                  style="Tagline.TLabel", justify="left").pack(anchor="w")

    def _build_main(self, parent: ttk.Frame):
        parent.rowconfigure(2, weight=1)
        parent.columnconfigure(0, weight=1)

        # Header / stat strip
        header = ttk.Frame(parent, style="Surface.TFrame", padding=(20, 14))
        header.grid(row=0, column=0, sticky="ew")
        header.columnconfigure(0, weight=1)

        self.archive_label_var = tk.StringVar(value="No archive loaded")
        ttk.Label(header, textvariable=self.archive_label_var,
                  style="StatPrimary.TLabel").grid(row=0, column=0, sticky="w")

        stats = ttk.Frame(header, style="Surface.TFrame")
        stats.grid(row=0, column=1, sticky="e")

        self.stat_count_var = tk.StringVar(value="—")
        self.stat_size_var = tk.StringVar(value="—")
        for col, (label, var) in enumerate([("FILES", self.stat_count_var),
                                            ("TOTAL", self.stat_size_var)]):
            cell = ttk.Frame(stats, style="Surface.TFrame", padding=(18, 0, 0, 0))
            cell.grid(row=0, column=col, sticky="ns")
            ttk.Label(cell, text=label,
                      style="StatSecondary.TLabel").pack(anchor="e")
            ttk.Label(cell, textvariable=var,
                      style="StatPrimary.TLabel").pack(anchor="e")

        # Filter row
        filter_row = ttk.Frame(parent, style="TFrame", padding=(20, 12, 20, 6))
        filter_row.grid(row=1, column=0, sticky="ew")
        filter_row.columnconfigure(1, weight=1)
        ttk.Label(filter_row, text="Filter").grid(row=0, column=0, padx=(0, 10))
        self.filter_var = tk.StringVar()
        self.filter_var.trace_add("write", lambda *_: self._apply_filter())
        ttk.Entry(filter_row, textvariable=self.filter_var).grid(row=0, column=1,
                                                                  sticky="ew")

        # File table
        body = ttk.Frame(parent, style="TFrame", padding=(20, 0, 20, 0))
        body.grid(row=2, column=0, sticky="nsew")
        body.rowconfigure(0, weight=1)
        body.columnconfigure(0, weight=1)

        cols = ("name", "size")
        self.tree = ttk.Treeview(body, columns=cols, show="headings",
                                 selectmode="extended")
        self.tree.heading("name", text="NAME",
                          command=lambda: self._sort_by("name", False))
        self.tree.heading("size", text="SIZE",
                          command=lambda: self._sort_by("size", False))
        self.tree.column("name", width=600, anchor="w")
        self.tree.column("size", width=110, anchor="e")

        # Zebra striping
        self.tree.tag_configure("odd", background=self.colors["surface_2"])
        self.tree.tag_configure("even", background=self.colors["surface_3"])

        vsb = ttk.Scrollbar(body, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")

        self.tree.bind("<Double-1>", lambda e: self.action_extract_selected())

        # Status / progress bar
        statusbar = ttk.Frame(parent, style="Surface.TFrame")
        statusbar.grid(row=3, column=0, sticky="ew")
        statusbar.columnconfigure(0, weight=1)
        self.status_var = tk.StringVar()
        ttk.Label(statusbar, textvariable=self.status_var,
                  style="Status.TLabel").grid(row=0, column=0, sticky="ew")
        self.progress = ttk.Progressbar(statusbar, mode="determinate",
                                        length=200,
                                        style="Horizontal.TProgressbar")
        self.progress.grid(row=0, column=1, padx=(0, 14), pady=4)

    # ----- status helpers -------------------------------------------------

    def _set_status(self, text: str):
        self.status_var.set(text)
        self.update_idletasks()

    # ----- file list ------------------------------------------------------

    def _apply_filter(self):
        needle = self.filter_var.get().lower().strip()
        self.tree.delete(*self.tree.get_children())
        i = 0
        for entry in self._all_entries:
            if needle and needle not in entry.filename.lower():
                continue
            tag = "even" if i % 2 == 0 else "odd"
            self.tree.insert("", tk.END,
                             values=(entry.filename, _human_size(entry.size)),
                             tags=(tag,))
            i += 1

    def _sort_by(self, col: str, reverse: bool):
        if col == "size":
            self._all_entries.sort(key=lambda e: e.size, reverse=reverse)
        else:
            self._all_entries.sort(key=lambda e: e.filename.lower(), reverse=reverse)
        self._apply_filter()
        self.tree.heading(col, command=lambda: self._sort_by(col, not reverse))

    # ----- dialog helpers -------------------------------------------------
    #
    # On Linux, file dialogs route through native tools (kdialog/zenity) when
    # available. This sidesteps a Tk bug where the directory-picker combobox
    # popup vanishes the moment it opens on KDE/Plasma — the popup's overlay
    # toplevel races with focus events from the file dialog parent. The bug
    # is in Tk's Tcl bindings and isn't fixable from Python.
    #
    # Fallback chain for filedialogs:
    #   1. kdialog or zenity (native, no bug) — when on Linux + tool present
    #   2. Tk's filedialog (bug present, but at least functional) — otherwise
    #
    # Messageboxes always use Tk: they're simple modal alerts with no
    # comboboxes or other interactive widgets that hit the bug, and they
    # need parent=self so they stay anchored to this window.

    def _ask_open(self, **kw):
        if _NATIVE_DIALOG:
            res = _native_open(**kw)
            if res is not None:
                return res
        return filedialog.askopenfilename(**self._tk_kwargs(kw))

    def _ask_open_many(self, **kw):
        if _NATIVE_DIALOG:
            res = _native_open_many(**kw)
            if res is not None:
                return res
        return filedialog.askopenfilenames(**self._tk_kwargs(kw))

    def _ask_save(self, **kw):
        if _NATIVE_DIALOG:
            res = _native_save(**kw)
            if res is not None:
                return res
        return filedialog.asksaveasfilename(**self._tk_kwargs(kw))

    def _ask_dir(self, **kw):
        if _NATIVE_DIALOG:
            res = _native_dir(**kw)
            if res is not None:
                return res
        return filedialog.askdirectory(**self._tk_kwargs(kw))

    def _tk_kwargs(self, kw):
        """Add parent=self for Tk filedialogs on non-Linux only.

        On Windows/macOS, parent= keeps the dialog from drifting behind the
        main window. On Linux, the only way we'd reach the Tk fallback is
        if neither kdialog nor zenity is installed; in that case we still
        omit parent= because the combobox-popup-vanishing bug from earlier
        rounds is triggered by transient relationships.
        """
        if sys.platform != "linux":
            kw.setdefault("parent", self)
        return kw

    def _info(self, title, message, **kw):
        return messagebox.showinfo(title, message, parent=self, **kw)

    def _warn(self, title, message, **kw):
        return messagebox.showwarning(title, message, parent=self, **kw)

    def _error(self, title, message, **kw):
        return messagebox.showerror(title, message, parent=self, **kw)

    def _ask_yn(self, title, message, **kw):
        return messagebox.askyesno(title, message, parent=self, **kw)

    def _ask_ync(self, title, message, **kw):
        return messagebox.askyesnocancel(title, message, parent=self, **kw)

    # ----- open & load ----------------------------------------------------

    def action_open(self):
        path = self._ask_open(
            title="Open PAK file",
            filetypes=[("PAK archives", "*.pak *.PAK"), ("All files", "*.*")],
        )
        if path:
            self.load_pak(path)

    def load_pak(self, path: str):
        if not os.path.isfile(path):
            self._error("Error", f"File not found:\n{path}")
            return
        if not fmt.is_pakfile(path):
            self._error(
                "Not a PAK file",
                f"{os.path.basename(path)} does not look like a valid HROT .pak file."
            )
            return
        try:
            entries = fmt.read_pak(path)
        except fmt.BadPakFile as exc:
            self._error("Bad PAK file", str(exc))
            return
        except Exception as exc:
            self._error("Error reading PAK", str(exc))
            return

        self._all_entries = sorted(entries, key=lambda e: e.filename.lower())
        self.current_pak = path
        self.title(f"HROT PAK Tool — {os.path.basename(path)}")
        self.archive_label_var.set(os.path.basename(path))
        self.stat_count_var.set(f"{len(self._all_entries):,}")
        self.stat_size_var.set(_human_size(sum(e.size for e in self._all_entries)))
        self._apply_filter()
        self._set_status(f"Loaded {os.path.basename(path)}")

    # ----- extraction -----------------------------------------------------

    def _selected_filenames(self) -> List[str]:
        names = []
        for iid in self.tree.selection():
            vals = self.tree.item(iid, "values")
            if vals:
                names.append(vals[0])
        return names

    def action_extract_selected(self):
        if not self.current_pak:
            self._info("No archive", "Open a .pak file first.")
            return
        names = self._selected_filenames()
        if not names:
            self._info("No selection",
                       "Select one or more files in the list, "
                       "or use Extract All.")
            return
        dest = self._ask_dir(title="Extract selected files to…")
        if not dest:
            return
        wanted = set(names)
        entries = [e for e in self._all_entries if e.filename in wanted]
        # Wrap the extraction in a folder named after the .pak (same as
        # Extract All), so partial extracts don't clutter the destination
        # and re-extracting bumps to "name (2)", "name (3)", etc.
        wrapped = self._unique_dir(dest, self._wrapper_name(self.current_pak))
        self._run_extract(entries, wrapped)

    def action_extract_all(self):
        if not self.current_pak:
            self._info("No archive", "Open a .pak file first.")
            return
        if not self._all_entries:
            self._info("Empty archive", "Nothing to extract.")
            return
        dest = self._ask_dir(title="Extract all files to…")
        if not dest:
            return
        # Wrap the extracted files in a folder named after the .pak, so the
        # destination doesn't get sprayed with archive contents. If a folder
        # of that name already exists, append " (2)", " (3)", … until we find
        # an unused name — same convention browsers use for duplicate
        # downloads.
        wrapped = self._unique_dir(dest, self._wrapper_name(self.current_pak))
        self._run_extract(list(self._all_entries), wrapped)

    @staticmethod
    def _wrapper_name(pak_path: str) -> str:
        """Pick a folder name based on the pak's basename (no extension)."""
        base = os.path.basename(pak_path)
        stem, _ = os.path.splitext(base)
        return stem or base  # fall back to full name if there's no extension

    @staticmethod
    def _unique_dir(parent: str, name: str) -> str:
        """Return an absolute path under `parent` that doesn't yet exist.

        If `parent/name` is free, returns that. Otherwise tries
        `parent/name (2)`, `parent/name (3)`, etc. The directory is NOT
        created here — `extract_entry` makes intermediate dirs as it goes.
        """
        candidate = os.path.join(parent, name)
        if not os.path.exists(candidate):
            return candidate
        i = 2
        while True:
            candidate = os.path.join(parent, f"{name} ({i})")
            if not os.path.exists(candidate):
                return candidate
            i += 1

    def _run_extract(self, entries: List[fmt.PakEntry], dest: str):
        self.progress.configure(maximum=len(entries), value=0)
        self._set_status(f"Extracting 0 / {len(entries)}…")
        pak_path = self.current_pak

        def worker():
            errors = []
            extracted = 0
            for i, entry in enumerate(entries, 1):
                try:
                    fmt.extract_entry(pak_path, entry, dest)
                    extracted += 1
                except Exception as e:
                    errors.append((entry.filename, str(e)))
                self.after(0, self._update_progress, i, len(entries), entry.filename)

            def done():
                self.progress.configure(value=0)
                msg = f"Extracted {extracted} / {len(entries)} files to {dest}"
                if errors:
                    msg += f"  ({len(errors)} errors)"
                    detail = "\n".join(f"{n}: {e}" for n, e in errors[:20])
                    if len(errors) > 20:
                        detail += f"\n… and {len(errors) - 20} more"
                    self._warn("Some files failed", detail)
                else:
                    self._info("Done", msg)
                self._set_status(msg)
            self.after(0, done)

        threading.Thread(target=worker, daemon=True).start()

    def _update_progress(self, i: int, total: int, name: str):
        self.progress.configure(value=i)
        short = name if len(name) < 70 else "…" + name[-67:]
        self._set_status(f"Working {i} / {total}: {short}")

    # ----- packing --------------------------------------------------------
    #
    # Four entry points instead of two. The previous "New .pak…" button used
    # a Yes/No/Cancel prompt mid-flow to ask whether the user wanted to add
    # files or a folder; that's confusing because Yes/No don't naturally
    # mean "files"/"folder". Splitting into four named actions removes that
    # prompt and makes each dialog's purpose unambiguous from the button
    # label alone.

    def action_create_pak_from_files(self):
        """New PAK ← multiple files."""
        print("[hrot-pak] From Files: opening file picker...", file=sys.stderr)
        files = self._ask_open_many(
            title="New PAK — pick files to include",
        )
        if not files:
            print("[hrot-pak] From Files: cancelled or no files picked.",
                  file=sys.stderr)
            return
        print(f"[hrot-pak] From Files: {len(files)} file(s) picked.",
              file=sys.stderr)
        out = self._ask_new_pak_destination()
        if not out:
            print("[hrot-pak] From Files: cancelled at save dialog.",
                  file=sys.stderr)
            return
        if not self._confirm_pack(out, list(files), mode="w"):
            return
        self._run_pack(out, list(files), mode="w")

    def action_create_pak_from_folder(self):
        """New PAK ← every file under one folder."""
        print("[hrot-pak] From Folder: opening folder picker...",
              file=sys.stderr)
        folder = self._ask_dir(
            title="New PAK — pick folder to include",
        )
        if not folder:
            print("[hrot-pak] From Folder: cancelled or no folder picked.",
                  file=sys.stderr)
            return
        # Default the new pak's filename to the folder's basename, so the save
        # dialog opens already pointed at e.g. "mymod.pak" when the user
        # picked a folder named "mymod".
        suggested = os.path.basename(folder.rstrip(os.sep)) + ".pak"
        out = self._ask_new_pak_destination(suggested_name=suggested)
        if not out:
            print("[hrot-pak] From Folder: cancelled at save dialog.",
                  file=sys.stderr)
            return
        if not self._confirm_pack(out, [folder], mode="w"):
            return
        self._run_pack(out, [folder], mode="w")

    def action_add_files(self):
        """Append individual files to the currently-open PAK."""
        if not self.current_pak:
            self._info("No archive",
                       "Open a .pak file first, then add files to it.")
            return
        base = os.path.basename(self.current_pak)
        files = self._ask_open_many(
            title=f"Add to ‘{base}’ — pick files to add",
        )
        if not files:
            return
        if not self._confirm_pack(self.current_pak, list(files), mode="a"):
            return
        self._run_pack(self.current_pak, list(files), mode="a")

    def action_add_folder(self):
        """Append every file under a folder to the currently-open PAK."""
        if not self.current_pak:
            self._info("No archive",
                       "Open a .pak file first, then add a folder to it.")
            return
        base = os.path.basename(self.current_pak)
        folder = self._ask_dir(
            title=f"Add to ‘{base}’ — pick folder to add",
        )
        if not folder:
            return
        if not self._confirm_pack(self.current_pak, [folder], mode="a"):
            return
        self._run_pack(self.current_pak, [folder], mode="a")

    def _ask_new_pak_destination(self,
                                 suggested_name: Optional[str] = None) -> Optional[str]:
        """Save dialog + validation for a new pak's output path. Returns the
        normalized path on success, or None on cancel/invalid input.

        If `suggested_name` is given, it pre-fills the dialog's filename
        field — useful for the folder→pak flow where the folder's name is
        the natural default."""
        kwargs = {
            "title": "New PAK — pick where to save the archive",
            "defaultextension": ".pak",
            "filetypes": [("PAK archives", "*.pak"), ("All files", "*.*")],
        }
        if suggested_name:
            kwargs["initialfile"] = suggested_name
        out = self._ask_save(**kwargs)
        if not out:
            return None
        return self._validate_new_pak_path(out)

    def _confirm_pack(self, pak_path: str, sources: list, mode: str) -> bool:
        """Show a final 'about to do this' summary before kicking off the
        pack. Returns True if the user wants to proceed."""
        valid, skipped = self._resolve_sources(sources)
        if not valid and not skipped:
            self._info("Nothing to add",
                       "No files were found in your selection.")
            return False

        if not valid and skipped:
            # Every file's archive name is too long — there's nothing we can
            # actually pack. Tell them why, with examples.
            preview = "\n".join(f"  • {a}" for _, a, _ in skipped[:5])
            extra = f"\n  • … and {len(skipped) - 5} more" if len(skipped) > 5 else ""
            self._error(
                "Can't pack any of these",
                f"All {len(skipped)} file{'' if len(skipped) == 1 else 's'} you "
                f"selected have archive names longer than 119 characters, "
                f"which is the maximum the HROT pak format supports.\n\n"
                f"Examples:\n{preview}{extra}\n\n"
                f"Try picking a folder closer to the files, or rename the "
                f"deeply-nested ones first.",
            )
            return False

        total_bytes = sum(sz for _, _, sz in valid)
        verb = "Create" if mode == "w" else "Add to"
        n = len(valid)
        msg = (
            f"{verb} {os.path.basename(pak_path)} with "
            f"{n} file{'' if n == 1 else 's'} "
            f"({_human_size(total_bytes)})?\n\n"
        )

        # Preview up to 6 valid entries so the user can spot a wrong selection.
        preview_count = 6
        previews = [arc for _, arc, _ in valid[:preview_count]]
        msg += "\n".join(f"  • {p}" for p in previews)
        if n > preview_count:
            msg += f"\n  • … and {n - preview_count} more"

        # If anything was skipped, surface it. The user almost certainly wants
        # to know rather than discover after the fact that their archive is
        # missing files.
        if skipped:
            msg += (
                f"\n\n⚠ {len(skipped)} file{'' if len(skipped) == 1 else 's'} "
                f"will be skipped — name too long for pak format (>119 chars):\n"
            )
            skip_preview = [arc for _, arc, _ in skipped[:3]]
            msg += "\n".join(f"  • …{a[-60:]}" if len(a) > 60 else f"  • {a}"
                             for a in skip_preview)
            if len(skipped) > 3:
                msg += f"\n  • … and {len(skipped) - 3} more"

        return bool(self._ask_yn(f"Confirm — {verb.lower()} archive", msg))

    @staticmethod
    def _resolve_sources(sources: list) -> tuple:
        """Walk the user's selection (mix of files and folders) into two flat
        lists of (source_path, archive_name, size_bytes) tuples:

            (valid_entries, skipped_too_long)

        Names with an ASCII-encoded length > 119 cannot fit the HROT pak
        format's 120-byte filename field (with null terminator), so they're
        separated here for the confirmation dialog rather than failing mid
        pack."""
        valid = []
        skipped = []
        for src in sources:
            if os.path.isdir(src):
                src_abs = os.path.abspath(src.rstrip(os.sep))
                base_parent = os.path.dirname(src_abs)
                for root, _, files in os.walk(src_abs):
                    for name in files:
                        if name.startswith("."):
                            continue
                        full = os.path.join(root, name)
                        arc = os.path.relpath(full, base_parent).replace(os.sep, "/")
                        try:
                            size = os.path.getsize(full)
                        except OSError:
                            size = 0
                        # 119 = 120-byte field minus 1 byte for the null terminator
                        if len(arc.encode("ascii", errors="replace")) > 119:
                            skipped.append((full, arc, size))
                        else:
                            valid.append((full, arc, size))
            elif os.path.isfile(src):
                arc = os.path.basename(src)
                try:
                    size = os.path.getsize(src)
                except OSError:
                    size = 0
                if len(arc.encode("ascii", errors="replace")) > 119:
                    skipped.append((src, arc, size))
                else:
                    valid.append((src, arc, size))
        return valid, skipped

    def _validate_new_pak_path(self, path: str) -> Optional[str]:
        """Sanity-check a user-typed path for a new .pak file.

        Returns a normalized absolute path on success, or None if the user
        bailed out at any prompt or the path is unusable. All failure modes
        surface as friendly modals rather than tracebacks from write_pak.
        """
        # Normalize first so subsequent checks see one canonical form.
        path = os.path.abspath(os.path.expanduser(path.strip()))

        # If the user picked an existing directory (e.g. typed "Downloads"
        # in the save dialog and the dialog accepted it), there's nothing
        # we can do — we'd clobber a folder. Reject hard.
        if os.path.isdir(path):
            self._error(
                "Can't write there",
                f"That path is a directory, not a file:\n{path}",
            )
            return None

        # Extension check. We append .pak if they typed nothing, and warn
        # but offer to fix if they typed a non-pak extension. (defaultextension
        # in the dialog usually handles the empty case, but kdialog/zenity
        # don't honour it the same way.)
        stem, ext = os.path.splitext(path)
        if not ext:
            path = stem + ".pak"
        elif ext.lower() != ".pak":
            if not self._ask_yn(
                "Unusual extension",
                f"The file you named ends in '{ext}', not '.pak'.\n\n"
                f"HROT only loads files named *.pak. Save as\n"
                f"{stem}.pak instead?",
            ):
                # User said "no, keep my weird extension" — let them.
                pass
            else:
                path = stem + ".pak"

        # Parent directory must exist OR be creatable. write_pak makes the
        # parent if missing; we just need to verify we have permission.
        parent = os.path.dirname(path) or "."
        if os.path.exists(parent):
            if not os.path.isdir(parent):
                self._error(
                    "Can't write there",
                    f"The parent path is not a directory:\n{parent}",
                )
                return None
            if not os.access(parent, os.W_OK):
                self._error(
                    "Can't write there",
                    f"You don't have permission to write to:\n{parent}",
                )
                return None
        else:
            # Parent doesn't exist. We can usually create it, but verify the
            # nearest existing ancestor is writable so we fail cleanly here
            # rather than mid-pack.
            ancestor = parent
            while ancestor and not os.path.exists(ancestor):
                new_ancestor = os.path.dirname(ancestor)
                if new_ancestor == ancestor:
                    break  # reached filesystem root that doesn't exist (?!)
                ancestor = new_ancestor
            if ancestor and not os.access(ancestor, os.W_OK):
                self._error(
                    "Can't create folder there",
                    f"You don't have permission to create:\n{parent}",
                )
                return None

        # Overwrite confirmation. The save dialog *might* have asked already,
        # but coverage is inconsistent across Tk / kdialog / zenity, and a
        # second confirmation for destructive overwrite is cheap insurance.
        if os.path.isfile(path):
            if not self._ask_yn(
                "Replace file?",
                f"{os.path.basename(path)} already exists in\n"
                f"{os.path.dirname(path)}.\n\n"
                f"Replace it? The existing file will be overwritten.",
            ):
                return None

        return path

    def _run_pack(self, pak_path: str, sources: list, mode: str):
        # _confirm_pack has already walked sources via _resolve_sources, but
        # we re-walk here so this method stays usable in isolation (e.g. if
        # a future caller skips the confirm step).
        valid, _skipped = self._resolve_sources(sources)

        if not valid:
            self._info("Nothing to add", "No valid files found in the selection.")
            return

        # write_pak takes (source_path, archive_name) pairs; strip our size hint.
        entries = [(src, arc) for src, arc, _sz in valid]

        self.progress.configure(maximum=len(entries), value=0)
        self._set_status(f"Packing 0 / {len(entries)}…")

        def worker():
            try:
                def cb(i, total, name):
                    self.after(0, self._update_progress, i, total, name)
                fmt.write_pak(pak_path, entries, mode=mode, progress=cb)
            except Exception as e:
                # User-facing message stays clean: just the error, no traceback.
                # The traceback goes to stderr for developers running from a
                # console.
                traceback.print_exc()
                self.after(0, self._error, "Packing failed", str(e))
                self.after(0, self._set_status, "Packing failed.")
                return

            def done():
                self.progress.configure(value=0)
                msg = f"Wrote {len(entries)} files to {os.path.basename(pak_path)}"
                self._info("Done", msg)
                self._set_status(msg)
                if self.current_pak and \
                        os.path.abspath(pak_path) == os.path.abspath(self.current_pak):
                    self.load_pak(pak_path)
                elif mode == "w":
                    if self._ask_yn("Open new archive?",
                                    "Open the newly created .pak now?"):
                        self.load_pak(pak_path)
            self.after(0, done)

        threading.Thread(target=worker, daemon=True).start()

    # ----- about ----------------------------------------------------------

    def _about(self):
        self._info(
            "About HROT PAK Tool",
            f"HROT PAK Tool v{__version__}\n\n"
            "A modern dark-themed GUI for inspecting, extracting, and creating\n"
            "HROT .pak archives.\n\n"
            "GUI Tool and additional features by Saint Baron.\n"
            "CLI commands `pak` and `unpak` originally by joshuaskelly/hrot-cli-tools.",
        )


def main():
    """Launch the GUI. Optional sys.argv[1] is a .pak path to pre-open."""
    app = PakGUI()
    if len(sys.argv) > 1 and os.path.isfile(sys.argv[1]):
        app.after(100, lambda: app.load_pak(sys.argv[1]))
    app.mainloop()


if __name__ == "__main__":
    main()
