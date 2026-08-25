# SpaceReclaim

**SpaceReclaim** finds duplicate files on your disk and helps you trash them — safely.

A clean, flat GTK3 desktop app (Telegram-style UI) with **light and dark themes**.
Built in a single pure-Python file on top of PyGObject. No web frameworks, no
databases, no bloat — just a smart duplicate scanner with a nice face.

## What it does

Point it at one or more folders, hit **Scan**, and SpaceReclaim:

1. Walks the folders and groups files by **size** (most duplicates share a size).
2. Clusters each group by a **fast partial hash** (first 64 KB).
3. Confirms real duplicates with a **full content hash** — byte-for-byte identical
   files are grouped into "sets".

You then choose what to delete. Checked files are moved to the **trash** (via the
desktop's trash system, with a safe local fallback), so nothing is ever lost.

## Features

- **Content hashing, not name matching** — catches duplicates even with different
  filenames, in different folders.
- **Fast** — size grouping skips most files; partial hashing skips most reads;
  full hashing confirms only candidates.
- **Safe** — every delete goes to the trash, never `rm`. A local `.trash` folder
  is used if the desktop trash is unavailable.
- **"Keep one per set"** — one click checks every duplicate except a single copy
  per set.
- **Live space countdown** — the "Will free" counter updates as you tick boxes.
- **Light & dark themes** with a headerbar toggle — your choice is remembered.
- **Runs anywhere GTK3 does** — Linux, BSD, and beyond.

## Requirements

- Python 3.8+
- PyGObject with GTK 3 (on Debian/Ubuntu: `python3-gi gir1.2-gtk-3.0`)

## Usage

```bash
python3 spacereclaim.py
```

1. Click **Add Folders** to pick the folders to scan.
2. Press **Scan** (cancel any time).
3. Tick the duplicates you want gone — or hit **Keep one per set**.
4. Press **Delete checked**. Done.

## How it finds duplicates

```
walk folders  ->  group by file size  ->  partial-hash clusters  ->  full-hash confirm
```

Only files whose size matches at least one other file are ever hashed, and only
partial-hash matches get the full treatment — so large trees scan quickly.

## Theming

Toggle light/dark with the sun/moon button in the headerbar. The choice is stored
in `~/.config/spacereclaim/config.json`.

## Layout

- **Sidebar** — the folders you're scanning, with Add / Remove.
- **Main panel** — status, progress bar, and the results table.
- **Action bar** — summary, reclaimable-space counter, and the delete controls.

## License

GNU GPL v3 — see [LICENSE](LICENSE).
