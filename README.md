<h1 align="center">🗑️ SpaceReclaim</h1>

<p align="center">
  <b>Find duplicate files. Reclaim your disk.</b><br>
  A clean, flat GTK3 desktop app with a Telegram-style UI — dark &amp; light themes.
  One pure-Python file. No bloat, no databases, no web frameworks.
</p>

<p align="center">
  <img src="https://img.shields.io/badge/GTK3-46a52a?style=for-the-badge&logo=gtk&logoColor=white" alt="GTK3">
  <img src="https://img.shields.io/badge/python-3.8%2B-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python 3.8+">
  <img src="https://img.shields.io/badge/dependencies-PyGObject-2ea44f?style=for-the-badge" alt="Only PyGObject">
  <img src="https://img.shields.io/badge/license-GPLv3-8b0000?style=for-the-badge" alt="GPLv3">
  <img src="https://img.shields.io/badge/PRs-welcome-brightgreen?style=for-the-badge" alt="PRs welcome">
</p>

<p align="center">
  <b>🟦 light</b> &nbsp;·&nbsp; <b>⬛ dark</b> &nbsp;·&nbsp; one click to switch
</p>

---

## 💡 What it does

Point it at one or more folders, hit **Scan**, and SpaceReclaim finds files that
are **byte-for-byte identical** — even when they have different names and live in
different folders.

Then you decide what to keep. Checked duplicates are moved to the **trash**, never
deleted permanently.

---

## ✨ Features

| Feature                    | Benefit                                                                  |
|----------------------------|--------------------------------------------------------------------------|
| 🔍 **Content hashing**     | Catches duplicates by content, not filename — different names, any folder |
| ⚡ **Blazing fast**         | Size grouping + partial hashing skip most reads; full hash confirms only candidates |
| 🛡️ **100% safe**           | Deletes go to the desktop trash, never `rm`; local `.trash` fallback      |
| 🎯 **"Keep one per set"**  | One click checks every duplicate except a single survivor per set         |
| 📉 **Live space countdown**| The *Will free* counter updates as you tick boxes                         |
| 🌗 **Dark & light themes**  | Headerbar toggle, remembered across launches                              |
| 🖥️ **Runs anywhere GTK3 does** | Linux, BSD, and beyond — not just your laptop                          |

---

## 🚀 Getting started

### Requirements

- Python 3.8+
- PyGObject with GTK 3 — Debian/Ubuntu:

  ```bash
  sudo apt install python3-gi gir1.2-gtk-3.0
  ```

### Run it

```bash
python3 spacereclaim.py
```

### Usage in four steps

1. **Add Folders** — pick the folders to scan.
2. **Scan** — cancel any time.
3. **Select** — tick duplicates, or hit *Keep one per set*.
4. **Delete checked** — done. They land in the trash.

---

## ⚙️ How it finds duplicates

```
walk folders  →  group by file size  →  partial-hash clusters  →  full-hash confirm
```

Only files whose size matches at least one other file are ever hashed, and only
partial-hash matches get the full treatment — so large trees scan quickly.

---

## 🎨 Theming

Toggle **dark** / **light** with the sun/moon button in the headerbar. Your
choice is stored in `~/.config/spacereclaim/config.json` and restored on launch.

---

## 🖥️ Layout

| Region        | What lives there                                             |
|---------------|---------------------------------------------------------------|
| **Sidebar**   | the folders you're scanning, with Add / Remove               |
| **Main panel**| status, progress bar, and the results table                  |
| **Action bar**| summary, reclaimable-space counter, and delete controls      |

---

## 📄 License

**GNU GPL v3** — see [LICENSE](LICENSE).
