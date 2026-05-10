"""HROT .pak archive format — pure-stdlib reader/writer.

The HROT .pak format is the same shape as the classic Quake PAK format,
with two differences:

    - magic is b"HROT" instead of b"PACK"
    - filename field is 120 bytes instead of 56

Layout::

    Header (12 bytes)
        char    magic[4]            // b"HROT"
        int32   directory_offset    // little-endian, byte offset of directory
        int32   directory_size      // little-endian, byte length of directory

    File data
        Raw bytes for each archived file, packed back-to-back. Order is
        irrelevant; the directory points to each file by absolute offset.

    Directory (one entry per file, 128 bytes each)
        char    filename[120]       // null-padded ASCII path (forward slashes)
        int32   file_offset         // little-endian
        int32   file_size           // little-endian

This module has no dependencies outside the Python standard library, and
no GUI or CLI imports — it can be embedded in any tool.
"""

from __future__ import annotations

import os
import struct
from typing import Callable, Iterable, List, Optional, Tuple

PAK_MAGIC = b"HROT"
HEADER_FMT = "<4sii"
HEADER_SIZE = struct.calcsize(HEADER_FMT)   # 12
ENTRY_FMT = "<120sii"
ENTRY_SIZE = struct.calcsize(ENTRY_FMT)     # 128
MAX_NAME = 120

ProgressCB = Callable[[int, int, str], None]


class BadPakFile(Exception):
    """Raised when a file is not a valid HROT .pak archive."""


class PakEntry:
    """A single file inside a .pak archive (filename + offset + size)."""

    __slots__ = ("filename", "offset", "size")

    def __init__(self, filename: str, offset: int, size: int):
        self.filename = filename
        self.offset = offset
        self.size = size

    # vgio compatibility shim
    @property
    def file_size(self) -> int:
        return self.size

    @property
    def file_offset(self) -> int:
        return self.offset

    def __repr__(self) -> str:
        return f"PakEntry({self.filename!r}, offset={self.offset}, size={self.size})"


def is_pakfile(path: str) -> bool:
    """Return True iff `path` exists and starts with the HROT magic."""
    try:
        with open(path, "rb") as fp:
            return fp.read(4) == PAK_MAGIC
    except OSError:
        return False


def read_pak(path: str) -> List[PakEntry]:
    """Open `path`, parse the header + directory, return list[PakEntry].

    Raises:
        BadPakFile: if the magic, header, or directory is invalid.
    """
    size = os.path.getsize(path)
    with open(path, "rb") as fp:
        head = fp.read(HEADER_SIZE)
        if len(head) < HEADER_SIZE:
            raise BadPakFile("File too small to be a PAK archive.")
        magic, dir_off, dir_size = struct.unpack(HEADER_FMT, head)
        if magic != PAK_MAGIC:
            raise BadPakFile(
                f"Bad magic: {magic!r} (expected {PAK_MAGIC!r})"
            )
        if dir_off < 0 or dir_size < 0 or dir_off + dir_size > size:
            raise BadPakFile("Directory offset/size out of range.")
        if dir_size % ENTRY_SIZE != 0:
            raise BadPakFile(
                f"Directory size {dir_size} not a multiple of {ENTRY_SIZE}."
            )
        fp.seek(dir_off)
        dir_data = fp.read(dir_size)

    entries: List[PakEntry] = []
    for raw_name, off, sz in struct.iter_unpack(ENTRY_FMT, dir_data):
        name = raw_name.split(b"\x00", 1)[0].decode("ascii", errors="replace")
        entries.append(PakEntry(name, off, sz))
    return entries


def extract_entry(pak_path: str, entry: PakEntry, dest_root: str) -> str:
    """Extract a single entry to `dest_root`, with zip-slip protection.

    Returns the absolute path of the extracted file.
    """
    rel = entry.filename.replace("\\", "/").lstrip("/")
    if not rel:
        raise ValueError("Empty filename in archive.")
    target = os.path.realpath(os.path.join(dest_root, rel))
    root = os.path.realpath(dest_root)
    if not (target == root or target.startswith(root + os.sep)):
        raise ValueError(f"Unsafe path in archive: {entry.filename!r}")

    parent = os.path.dirname(target)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(pak_path, "rb") as src, open(target, "wb") as dst:
        src.seek(entry.offset)
        remaining = entry.size
        while remaining > 0:
            chunk = src.read(min(1 << 20, remaining))
            if not chunk:
                raise BadPakFile(
                    f"Unexpected EOF reading {entry.filename!r}"
                )
            dst.write(chunk)
            remaining -= len(chunk)
    return target


def write_pak(
    pak_path: str,
    files: Iterable[Tuple[str, str]],
    mode: str = "w",
    progress: Optional[ProgressCB] = None,
) -> List[PakEntry]:
    """Create or append-to a .pak archive.

    Args:
        pak_path: Output path.
        files: Iterable of (source_path, archive_name) pairs.
        mode: "w" overwrite, "a" append (preserves existing entries; if a
            new entry duplicates an existing archive name, the new one
            replaces it).
        progress: Optional callable(i, total, name) called per file written.
            For append mode, only the *new* files trigger progress (existing
            entries are copied through silently).

    Returns:
        The final list of PakEntry objects in the resulting archive.

    Implementation notes:
        - The output is written to a sibling temp file and renamed into
          place at the end. A crash mid-write leaves the original archive
          (if any) untouched.
        - Append mode streams existing payloads chunk-by-chunk through to
          the new file; memory use stays bounded regardless of archive size.
    """
    files = list(files)

    # In append mode, capture the existing entry list (offsets into the OLD
    # file) up front. We'll stream their bytes during write.
    existing_entries: List[PakEntry] = []
    if mode == "a" and os.path.exists(pak_path):
        existing_entries = read_pak(pak_path)

    # Drop any existing entries whose archive name is being overwritten by a
    # new file in this call. Last-write-wins for duplicates among `files`
    # themselves is handled later inside the write loop.
    new_names = {arc.replace("\\", "/") for _, arc in files}
    existing_entries = [e for e in existing_entries if e.filename not in new_names]

    out_dir = os.path.dirname(os.path.abspath(pak_path)) or "."
    if not os.path.exists(out_dir):
        os.makedirs(out_dir)
    tmp_path = pak_path + ".tmp"

    new_entries: List[PakEntry] = []
    total_new = len(files)
    written_new = 0

    try:
        # When appending, we read from the original pak while writing to
        # tmp_path; both file handles are needed simultaneously.
        src_for_existing = open(pak_path, "rb") if existing_entries else None
        try:
            with open(tmp_path, "wb") as out:
                out.write(b"\x00" * HEADER_SIZE)  # reserve header space

                # Stream existing payloads through (no progress reported).
                for entry in existing_entries:
                    offset = out.tell()
                    src_for_existing.seek(entry.offset)
                    remaining = entry.size
                    while remaining > 0:
                        chunk = src_for_existing.read(min(1 << 20, remaining))
                        if not chunk:
                            raise BadPakFile(
                                f"Unexpected EOF while copying {entry.filename!r}"
                            )
                        out.write(chunk)
                        remaining -= len(chunk)
                    new_entries.append(PakEntry(entry.filename, offset, entry.size))

                # Write new files. Last-write-wins for duplicates among `files`.
                for src_path, arc_name in files:
                    arc_name = arc_name.replace("\\", "/")
                    encoded = arc_name.encode("ascii", errors="strict")
                    if len(encoded) > MAX_NAME - 1:  # leave room for null terminator
                        raise ValueError(
                            f"Archive name too long ({len(encoded)} > {MAX_NAME - 1}): "
                            f"{arc_name!r}"
                        )
                    offset = out.tell()
                    size = 0
                    with open(src_path, "rb") as sfp:
                        while True:
                            chunk = sfp.read(1 << 20)
                            if not chunk:
                                break
                            out.write(chunk)
                            size += len(chunk)
                    new_entries = [e for e in new_entries if e.filename != arc_name]
                    new_entries.append(PakEntry(arc_name, offset, size))
                    written_new += 1
                    if progress:
                        progress(written_new, total_new, arc_name)

                # Write the directory.
                dir_offset = out.tell()
                for e in new_entries:
                    name_bytes = e.filename.encode("ascii", errors="strict")
                    padded = name_bytes + b"\x00" * (MAX_NAME - len(name_bytes))
                    out.write(struct.pack(ENTRY_FMT, padded, e.offset, e.size))
                dir_size = len(new_entries) * ENTRY_SIZE

                # Backfill the header.
                out.seek(0)
                out.write(struct.pack(HEADER_FMT, PAK_MAGIC, dir_offset, dir_size))
        finally:
            if src_for_existing is not None:
                src_for_existing.close()

        # Atomic swap. os.replace overwrites on both POSIX and Windows.
        os.replace(tmp_path, pak_path)
    except BaseException:
        # Clean up the temp file on any failure (including KeyboardInterrupt).
        try:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
        except OSError:
            pass
        raise

    return new_entries
