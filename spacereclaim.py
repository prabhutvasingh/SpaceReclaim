#!/usr/bin/env python3
"""SpaceReclaim — find and trash duplicate files.

A GTK3 GUI duplicate-file finder. Files are grouped by size, then by a fast
partial hash, then confirmed with a full content hash. Checked duplicates are
moved to the trash (via Gio), never deleted permanently.

Zero dependencies beyond PyGObject (GTK3).
"""

import hashlib
import json
import os
import threading

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gio, GLib, Pango

APP_NAME = "SpaceReclaim"
CHUNK = 1 << 16  # 64 KB read chunks
QUICK_BYTES = 1 << 16  # partial-hash window (first 64 KB)

COL_CHECKED, COL_PATH, COL_SIZE, COL_BYTES, COL_SET = range(5)

LIGHT_PALETTE = {
    "window_bg": "#ffffff", "sidebar": "#f4f4f6", "card": "#ffffff",
    "card_border": "#e6e6e8", "text": "#222222", "text_dim": "#707579",
    "text_faint": "#9a9aa2", "header": "#ffffff", "header_border": "#e6e6e8",
    "btn_bg": "#ffffff", "btn_border": "#dcdce0", "btn_hover": "#f2f2f4",
    "btn_active": "#e6e6ea", "btn_disabled_bg": "#f5f5f7",
    "btn_disabled_text": "#b0b0b5", "accent": "#3390ec",
    "accent_hover": "#2b86dd", "accent_active": "#287cd0",
    "accent_disabled": "#a9ccf3", "danger": "#e53935", "danger_hover": "#d9302c",
    "danger_active": "#cc2b27", "danger_disabled": "#f0b3b1",
    "col_header": "#fafafa", "row_sel": "#e8f2fd", "row_sel_focus": "#dbeafe",
    "trough": "#ececef", "scroll": "#c9c9cf", "scroll_hover": "#b5b5bc",
    "reclaim": "#1f9e5b",
}

DARK_PALETTE = {
    "window_bg": "#1e1f21", "sidebar": "#26272a", "card": "#1e1f21",
    "card_border": "#36373b", "text": "#e8e8ea", "text_dim": "#9a9ba1",
    "text_faint": "#7b7c82", "header": "#26272a", "header_border": "#36373b",
    "btn_bg": "#303136", "btn_border": "#45464b", "btn_hover": "#3a3b40",
    "btn_active": "#45464b", "btn_disabled_bg": "#2a2b2e",
    "btn_disabled_text": "#6f7075", "accent": "#3390ec",
    "accent_hover": "#4a9ef0", "accent_active": "#2b86dd",
    "accent_disabled": "#2c5f8f", "danger": "#e5533f", "danger_hover": "#ef634f",
    "danger_active": "#d34a37", "danger_disabled": "#6b3f3a",
    "col_header": "#2a2b2e", "row_sel": "#2b3b52", "row_sel_focus": "#2f4460",
    "trough": "#36373b", "scroll": "#4a4b50", "scroll_hover": "#5a5b60",
    "reclaim": "#4cc38a",
}

CSS_TEMPLATE = """
.sr-window {{
    background-color: {window_bg};
    color: {text};
}}
window {{
    font-family: "Noto Sans", sans-serif;
}}

headerbar {{
    background-color: {header};
    background-image: none;
    border: none;
    border-bottom: 1px solid {header_border};
    min-height: 54px;
    padding: 0 10px;
}}
headerbar .title {{
    font-weight: 700;
    font-size: 15px;
    color: {text};
}}
headerbar .subtitle {{
    font-size: 11.5px;
    color: {text_dim};
}}

.sr-sidebar {{
    background-color: {sidebar};
    border-radius: 14px;
}}
.sidebar-label {{
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 1px;
    color: {text_faint};
}}
.sidebar-hint {{
    font-size: 11px;
    color: {text_faint};
}}
.sr-roots {{
    background-color: transparent;
}}

.sr-main {{
    background-color: {window_bg};
}}
.status-label {{
    font-size: 12.5px;
    color: {text_dim};
}}

.sr-card {{
    border: 1px solid {card_border};
    border-radius: 12px;
    background-color: {card};
}}

button {{
    border-radius: 8px;
    border: 1px solid {btn_border};
    background-image: none;
    background-color: {btn_bg};
    color: {text};
    font-weight: 500;
    font-size: 12.5px;
    padding: 6px 14px;
}}
button:hover {{
    background-color: {btn_hover};
    border-color: {btn_border};
}}
button:active {{
    background-color: {btn_active};
}}
button:disabled {{
    background-color: {btn_disabled_bg};
    color: {btn_disabled_text};
    border-color: {card_border};
}}

button.accent {{
    background-color: {accent};
    border: none;
    color: #ffffff;
}}
button.accent:hover {{ background-color: {accent_hover}; }}
button.accent:active {{ background-color: {accent_active}; }}
button.accent:disabled {{
    background-color: {accent_disabled};
    color: #ffffff;
}}

button.danger {{
    background-color: {danger};
    border: none;
    color: #ffffff;
}}
button.danger:hover {{ background-color: {danger_hover}; }}
button.danger:active {{ background-color: {danger_active}; }}
button.danger:disabled {{
    background-color: {danger_disabled};
    color: #ffffff;
}}

treeview.view {{
    background-color: {card};
    color: {text};
    font-size: 12.5px;
}}
treeview.view header button {{
    background-image: none;
    background-color: {col_header};
    border: none;
    border-bottom: 1px solid {card_border};
    color: {text_dim};
    font-weight: 600;
    font-size: 11px;
    padding: 5px 8px;
}}
treeview.view:selected {{
    background-color: {row_sel};
    color: {text};
}}
treeview.view:selected:focus {{
    background-color: {row_sel_focus};
    color: {text};
}}

progressbar {{ min-height: 8px; }}
progressbar trough {{
    background-color: {trough};
    border: none;
    border-radius: 4px;
    min-height: 8px;
}}
progressbar progress {{
    background-color: {accent};
    border: none;
    border-radius: 4px;
    min-height: 8px;
}}

.sr-actionbar {{
    background-color: {window_bg};
    border: none;
    border-top: 1px solid {header_border};
    padding: 6px 2px;
}}
.reclaim-label {{
    color: {reclaim};
    font-weight: 700;
    font-size: 13px;
}}

scrollbar {{
    background-color: transparent;
    border: none;
}}
scrollbar trough {{ background-color: transparent; border: none; }}
scrollbar slider {{
    background-color: {scroll};
    border-radius: 4px;
    min-width: 8px;
    min-height: 8px;
}}
scrollbar slider:hover {{ background-color: {scroll_hover}; }}
"""


def build_css(palette):
    return CSS_TEMPLATE.format(**palette).encode()


CONFIG_DIR = os.path.expanduser("~/.config/spacereclaim")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")


def load_config():
    try:
        with open(CONFIG_FILE) as f:
            return json.load(f)
    except Exception:
        return {}


def save_config(data):
    try:
        os.makedirs(CONFIG_DIR, exist_ok=True)
        with open(CONFIG_FILE, "w") as f:
            json.dump(data, f)
    except OSError:
        pass


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------

def fmt(n):
    if n is None:
        return "?"
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024 or unit == "TB":
            if unit == "B":
                return f"{n} B"
            return f"{n / 1024:.1f} {unit}"
        n /= 1024
    return f"{n} {unit}"


def quick_hash(path):
    try:
        h = hashlib.sha1()
        with open(path, "rb") as f:
            h.update(f.read(QUICK_BYTES))
        return h.hexdigest()
    except OSError:
        return None


def full_hash(path):
    try:
        h = hashlib.sha1()
        with open(path, "rb") as f:
            while True:
                block = f.read(CHUNK)
                if not block:
                    break
                h.update(block)
        return h.hexdigest()
    except OSError:
        return None


def safe_trash(path):
    """Move a file to the trash; fall back to a local .trash folder."""
    g = Gio.File.new_for_path(path)
    try:
        if g.trash(None):
            return True
    except Exception:
        pass
    try:
        tdir = os.path.join(os.path.dirname(path), ".spacereclaim-trash")
        os.makedirs(tdir, exist_ok=True)
        dest = os.path.join(tdir, os.path.basename(path))
        i = 1
        while os.path.exists(dest):
            dest = os.path.join(tdir, f"{i}_{os.path.basename(path)}")
            i += 1
        os.rename(path, dest)
        return True
    except OSError:
        return False


# --------------------------------------------------------------------------
# scanner (runs off the UI thread)
# --------------------------------------------------------------------------

class Scanner:
    def __init__(self, roots, on_progress, on_status, on_done, cancel_test):
        self.roots = roots
        self.on_progress = on_progress
        self.on_status = on_status
        self.on_done = on_done
        self.cancel_test = cancel_test

    def run(self):
        try:
            groups = self._scan()
        except Exception:
            import traceback
            traceback.print_exc()
            groups = None
        self.on_done(groups)

    def _scan(self):
        # phase 1: walk folders, group by size
        self.on_status("Scanning folders...")
        size_map = {}
        for root in self.roots:
            for dirpath, dirnames, filenames in os.walk(root):
                if self.cancel_test():
                    return None
                for name in filenames:
                    p = os.path.join(dirpath, name)
                    try:
                        st = os.lstat(p)
                    except OSError:
                        continue
                    if not os.path.isfile(p) or st.st_size == 0:
                        continue
                    size_map.setdefault(st.st_size, []).append(p)

        candidates = {s: v for s, v in size_map.items() if len(v) > 1}
        total_files = sum(len(v) for v in candidates.values())
        total_bytes = sum(s * len(v) for s, v in candidates.items())
        if total_files == 0:
            return []

        # phase 2: cluster by partial hash
        self.on_status("Comparing file contents...")
        done_files = 0
        quick = {}
        for size, paths in candidates.items():
            if self.cancel_test():
                return None
            for p in paths:
                if self.cancel_test():
                    return None
                qh = quick_hash(p)
                if qh is not None:
                    quick.setdefault((size, qh), []).append(p)
                done_files += 1
                self.on_progress(done_files, total_files, total_bytes)

        # phase 3: confirm with full hash
        groups = []
        for (size, _qh), paths in quick.items():
            if len(paths) < 2:
                continue
            if self.cancel_test():
                return None
            full = {}
            for p in paths:
                if self.cancel_test():
                    return None
                fh = full_hash(p)
                if fh is not None:
                    full.setdefault(fh, []).append(p)
            for fh, group in full.items():
                if len(group) > 1:
                    groups.append([(p, size) for p in group])
        return groups


# --------------------------------------------------------------------------
# main window
# --------------------------------------------------------------------------

class SpaceReclaimWindow(Gtk.Window):
    def __init__(self):
        super().__init__(title=APP_NAME, default_width=960,
                         default_height=620)
        self.set_position(Gtk.WindowPosition.CENTER)
        self.get_style_context().add_class("sr-window")
        self.scanner = None
        self.deleting = False
        self.sets_total = 0
        self.rows_total = 0
        self.bytes_wasted = 0
        self.css_provider = Gtk.CssProvider()
        self.theme = self._initial_theme()

        self._build_headerbar()
        self._build_body()
        self._apply_theme()
        self._refresh_stats()

    # -- construction -----------------------------------------------------

    def _build_headerbar(self):
        hb = Gtk.HeaderBar()
        hb.set_show_close_button(True)
        hb.set_title(APP_NAME)
        hb.set_subtitle("find and trash duplicate files")
        self.set_titlebar(hb)

        self.btn_scan = Gtk.Button(label="Scan")
        self.btn_scan.connect("clicked", self.on_scan_clicked)
        self.btn_scan.get_style_context().add_class("accent")
        hb.pack_end(self.btn_scan)

        self.btn_theme = Gtk.Button()
        self.btn_theme.set_tooltip_text("Toggle dark / light theme")
        self.btn_theme.set_relief(Gtk.ReliefStyle.NONE)
        self.btn_theme.connect("clicked", self.on_toggle_theme)
        hb.pack_end(self.btn_theme)
        self._update_theme_icon()

    def _build_body(self):
        root = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        self.add(root)

        # -- sidebar: folders to scan -------------------------------
        sidebar = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        sidebar.get_style_context().add_class("sr-sidebar")
        sidebar.set_size_request(280, -1)
        sidebar.set_margin_top(16)
        sidebar.set_margin_bottom(16)
        sidebar.set_margin_start(16)
        sidebar.set_margin_end(8)
        root.pack_start(sidebar, False, False, 0)

        lbl = Gtk.Label(label="FOLDERS TO SCAN", xalign=0.0)
        lbl.get_style_context().add_class("sidebar-label")
        sidebar.pack_start(lbl, False, False, 0)

        scroller = Gtk.ScrolledWindow()
        scroller.get_style_context().add_class("sr-card")
        scroller.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroller.set_vexpand(True)
        self.roots_store = Gtk.ListStore(str)
        self.roots_view = Gtk.TreeView(model=self.roots_store)
        self.roots_view.get_style_context().add_class("sr-roots")
        self.roots_view.set_headers_visible(False)
        self.roots_view.set_show_expanders(False)
        self.roots_view.get_selection().set_mode(Gtk.SelectionMode.SINGLE)
        col = Gtk.TreeViewColumn("Path", Gtk.CellRendererText(), text=0)
        self.roots_view.append_column(col)
        scroller.add(self.roots_view)
        sidebar.pack_start(scroller, True, True, 0)

        self.btn_add = Gtk.Button(label="Add Folders")
        self.btn_add.connect("clicked", self.on_add_folders)
        self.btn_add.get_style_context().add_class("accent")
        sidebar.pack_start(self.btn_add, False, False, 0)

        self.btn_remove = Gtk.Button(label="Remove Selected")
        self.btn_remove.connect("clicked", self.on_remove_root)
        sidebar.pack_start(self.btn_remove, False, False, 0)

        hint = Gtk.Label(
            label="Tip: select all but one copy per set,\nthen press Delete.",
            xalign=0.0, justify=Gtk.Justification.LEFT)
        hint.get_style_context().add_class("sidebar-hint")
        sidebar.pack_start(hint, False, False, 0)

        # -- main panel ---------------------------------------------
        main = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        main.get_style_context().add_class("sr-main")
        main.set_margin_top(16)
        main.set_margin_bottom(16)
        main.set_margin_start(8)
        main.set_margin_end(16)
        root.pack_start(main, True, True, 0)

        self.status_label = Gtk.Label(
            label="Add folders to scan, then press Scan.", xalign=0.0)
        self.status_label.get_style_context().add_class("status-label")
        main.pack_start(self.status_label, False, False, 0)

        self.progress_bar = Gtk.ProgressBar()
        self.progress_bar.set_show_text(True)
        self.progress_bar.set_no_show_all(True)
        main.pack_start(self.progress_bar, False, False, 0)

        self.store = Gtk.ListStore(bool, str, str, int, str)
        self.store.set_sort_func(COL_SET, self._sort_set, None)
        self.view = Gtk.TreeView(model=self.store)
        self.view.set_headers_clickable(True)
        self.view.set_show_expanders(False)

        rend = Gtk.CellRendererToggle()
        rend.set_property("activatable", True)
        rend.connect("toggled", self.on_row_toggled)
        col_del = Gtk.TreeViewColumn("Delete")
        col_del.pack_start(rend, False)
        col_del.add_attribute(rend, "active", COL_CHECKED)
        col_del.set_sort_column_id(COL_CHECKED)
        self.view.append_column(col_del)

        cell_path = Gtk.CellRendererText()
        cell_path.set_property("ellipsize", Pango.EllipsizeMode.MIDDLE)
        col_path = Gtk.TreeViewColumn("Path", cell_path, text=COL_PATH)
        col_path.set_expand(True)
        col_path.set_sort_column_id(COL_PATH)
        self.view.append_column(col_path)

        cell_size = Gtk.CellRendererText()
        cell_size.set_property("xalign", 1.0)
        col_size = Gtk.TreeViewColumn("Size", cell_size, text=COL_SIZE)
        col_size.set_sort_column_id(COL_BYTES)
        self.view.append_column(col_size)

        cell_set = Gtk.CellRendererText()
        cell_set.set_property("xalign", 0.5)
        col_set = Gtk.TreeViewColumn("Set", cell_set, text=COL_SET)
        col_set.set_sort_column_id(COL_SET)
        self.view.append_column(col_set)

        self.store.set_sort_column_id(COL_SET, Gtk.SortType.ASCENDING)

        results_scroller = Gtk.ScrolledWindow()
        results_scroller.get_style_context().add_class("sr-card")
        results_scroller.set_policy(Gtk.PolicyType.AUTOMATIC,
                                    Gtk.PolicyType.AUTOMATIC)
        results_scroller.set_vexpand(True)
        results_scroller.add(self.view)
        main.pack_start(results_scroller, True, True, 0)

        ab = Gtk.ActionBar()
        ab.get_style_context().add_class("sr-actionbar")
        self.lbl_summary = Gtk.Label(label="")
        self.lbl_summary.set_xalign(0.0)
        self.lbl_summary.get_style_context().add_class("status-label")
        ab.pack_start(self.lbl_summary)

        self.lbl_reclaim = Gtk.Label(label="")
        self.lbl_reclaim.get_style_context().add_class("reclaim-label")
        ab.pack_start(self.lbl_reclaim)

        btn_keep = Gtk.Button(label="Keep one per set")
        btn_keep.connect("clicked", self.on_keep_one)
        ab.pack_end(btn_keep)

        btn_clear = Gtk.Button(label="Clear")
        btn_clear.connect("clicked", self.on_clear_selection)
        ab.pack_end(btn_clear)

        self.btn_delete = Gtk.Button(label="Delete checked")
        self.btn_delete.connect("clicked", self.on_delete_clicked)
        self.btn_delete.get_style_context().add_class("danger")
        ab.pack_end(self.btn_delete)

        main.pack_start(ab, False, False, 0)

    # -- theming ---------------------------------------------------------

    def _initial_theme(self):
        saved = load_config().get("theme")
        if saved in ("dark", "light"):
            return saved
        try:
            dark = bool(Gtk.Settings.get_default().get_property(
                "gtk-application-prefer-dark-theme"))
        except Exception:
            dark = False
        return "dark" if dark else "light"

    def _apply_theme(self):
        palette = DARK_PALETTE if self.theme == "dark" else LIGHT_PALETTE
        try:
            self.css_provider.load_from_data(build_css(palette))
        except Exception:
            return
        Gtk.StyleContext.add_provider_for_screen(
            self.get_screen(), self.css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

    def _update_theme_icon(self):
        icon = ("weather-clear-symbolic" if self.theme == "dark"
                else "weather-clear-night-symbolic")
        self.btn_theme.set_image(
            Gtk.Image.new_from_icon_name(icon, Gtk.IconSize.SMALL_TOOLBAR))

    def on_toggle_theme(self, _widget):
        self.theme = "dark" if self.theme == "light" else "light"
        save_config({"theme": self.theme})
        self._apply_theme()
        self._update_theme_icon()

    # -- ui thread helpers --------------------------------------------------

    def _post(self, fn):
        def _f(*_a):
            try:
                fn()
            except Exception:
                pass
            return False
        GLib.idle_add(_f)

    # -- roots --------------------------------------------------------------

    def on_add_folders(self, _widget):
        dlg = Gtk.FileChooserDialog(
            title="Select folders to scan", parent=self,
            action=Gtk.FileChooserAction.SELECT_FOLDER)
        dlg.set_select_multiple(True)
        dlg.set_modal(True)
        dlg.add_buttons("Cancel", Gtk.ResponseType.CANCEL,
                        "Add", Gtk.ResponseType.OK)
        if dlg.run() == Gtk.ResponseType.OK:
            for path in dlg.get_filenames():
                path = os.path.abspath(path)
                exists = any(
                    os.path.abspath(self.roots_store[r][0]) == path
                    for r in self.roots_store)
                if not exists:
                    self.roots_store.append([path])
        dlg.destroy()

    def on_remove_root(self, _widget):
        sel = self.roots_view.get_selection()
        _model, it = sel.get_selected()
        if it is not None:
            self.roots_store.remove(it)

    # -- scanning ------------------------------------------------------------

    def on_scan_clicked(self, _widget):
        if self.scanner is not None:
            self.scanner = None  # signals cancel (checked by the worker)
            self.btn_scan.set_sensitive(False)
            self.status_label.set_text("Cancelling...")
            return
        roots = [self.roots_store[r][0] for r in self.roots_store]
        if not roots:
            self._flash("Add at least one folder first.")
            return
        for root in roots:
            if not os.path.isdir(root):
                self._flash(f"Folder not found: {root}")
                return
        self.store.clear()
        self.sets_total = self.rows_total = self.bytes_wasted = 0
        self._refresh_stats()

        self.btn_scan.set_label("Cancel")
        self.btn_add.set_sensitive(False)
        self.btn_remove.set_sensitive(False)
        self.progress_bar.set_no_show_all(False)
        self.progress_bar.show()
        self.progress_bar.set_fraction(0.0)
        self.progress_bar.set_text("Scanning...")
        self.status_label.set_text("Scanning...")
        self.btn_delete.set_sensitive(False)

        scanner = Scanner(roots,
                          on_progress=self._on_progress,
                          on_status=self._on_status,
                          on_done=self._on_scan_done,
                          cancel_test=lambda: self.scanner is None)
        self.scanner = scanner
        threading.Thread(target=scanner.run, daemon=True).start()

    def _on_progress(self, files_done, files_total, done_bytes=None):
        def _f():
            frac = files_done / files_total if files_total else 1.0
            self.progress_bar.set_fraction(min(frac, 1.0))
            self.progress_bar.set_text(f"{files_done:,} of {files_total:,} files compared")
        self._post(_f)

    def _on_status(self, text):
        self._post(lambda: self.status_label.set_text(text))

    def _on_scan_done(self, groups):
        def _f():
            self.scanner = None
            self.btn_scan.set_label("Scan")
            self.btn_scan.set_sensitive(True)
            self.btn_add.set_sensitive(True)
            self.btn_remove.set_sensitive(True)
            self.progress_bar.hide()
            self.progress_bar.set_no_show_all(True)
            if groups is None:
                self.status_label.set_text("Scan cancelled.")
                return
            for gi, group in enumerate(groups, start=1):
                for path, size in group:
                    self.store.append([False, path, fmt(size), size, f"#{gi}"])
            self.sets_total = len(groups)
            self.rows_total = sum(len(g) for g in groups)
            self.bytes_wasted = sum(size for g in groups for _p, size in g)
            self._refresh_stats()
            if groups:
                self.status_label.set_text(
                    f"Found {self.rows_total} duplicate files in "
                    f"{self.sets_total} sets.")
            else:
                self.status_label.set_text("No duplicate files found.")
                self._flash("No duplicates found. Nothing to do!")
        self._post(_f)

    # -- selection & deletion --------------------------------------------------

    def on_row_toggled(self, _rend, path):
        it = self.store.get_iter(path)
        self.store.set_value(it, COL_CHECKED,
                             not self.store.get_value(it, COL_CHECKED))
        self._refresh_stats()

    def on_clear_selection(self, _widget):
        it = self.store.get_iter_first()
        while it is not None:
            self.store.set_value(it, COL_CHECKED, False)
            it = self.store.iter_next(it)
        self._refresh_stats()

    def on_keep_one(self, _widget):
        it = self.store.get_iter_first()
        prev_set = None
        first = True
        while it is not None:
            cur_set = self.store.get_value(it, COL_SET)
            if cur_set != prev_set:
                prev_set = cur_set
                first = True
            self.store.set_value(it, COL_CHECKED, not first)
            first = False
            it = self.store.iter_next(it)
        self._refresh_stats()

    def on_delete_clicked(self, _widget):
        paths = []
        total = 0
        it = self.store.get_iter_first()
        while it is not None:
            if self.store.get_value(it, COL_CHECKED):
                paths.append(self.store.get_value(it, COL_PATH))
                total += self.store.get_value(it, COL_BYTES)
            it = self.store.iter_next(it)
        if not paths:
            self._flash("Nothing is checked.")
            return
        dlg = Gtk.MessageDialog(
            parent=self, modal=True, message_type=Gtk.MessageType.QUESTION,
            buttons=Gtk.ButtonsType.OK_CANCEL,
            text=f"Move {len(paths)} file(s) to the trash?")
        dlg.format_secondary_text(
            f"This frees about {fmt(total)}. The files go to the trash, "
            f"so nothing is permanently lost.")
        if dlg.run() != Gtk.ResponseType.OK:
            dlg.destroy()
            return
        dlg.destroy()

        self.deleting = True
        self.btn_delete.set_sensitive(False)
        self.btn_scan.set_sensitive(False)
        self.status_label.set_text("Moving files to trash...")

        threading.Thread(
            target=self._delete_worker, args=(list(paths),), daemon=True).start()

    def _delete_worker(self, paths):
        failed = []
        for i, p in enumerate(paths):
            if not safe_trash(p):
                failed.append(p)
            self._post(lambda f=(i + 1): self.progress_bar.set_text(
                f"Trashing {f} of {len(paths)}..."))

        def _f():
            self.deleting = False
            self.btn_delete.set_sensitive(True)
            self.btn_scan.set_sensitive(True)
            trashed = set(paths) - set(failed)
            it = self.store.get_iter_first()
            while it is not None:
                if self.store.get_value(it, COL_PATH) in trashed:
                    nxt = self.store.iter_next(it)
                    self.store.remove(it)
                    it = nxt
                else:
                    it = self.store.iter_next(it)
            self._refresh_stats()
            if failed:
                self._flash(f"Could not trash {len(failed)} file(s):\n" +
                            "\n".join(failed[:5]))
            self.status_label.set_text(
                f"Trashed {len(trashed)} file(s)." if trashed
                else "Nothing was trashed.")
        self._post(_f)

    # -- stats ---------------------------------------------------------------

    def _refresh_stats(self):
        reclaim = 0
        it = self.store.get_iter_first()
        while it is not None:
            if self.store.get_value(it, COL_CHECKED):
                reclaim += self.store.get_value(it, COL_BYTES)
            it = self.store.iter_next(it)
        self.lbl_reclaim.set_text(f"Will free: {fmt(reclaim)}")
        self.lbl_summary.set_text(
            f"{self.rows_total} duplicate files in {self.sets_total} sets"
            f" ({fmt(self.bytes_wasted)} wasted)")
        self.btn_delete.set_sensitive(not self.deleting)

    def _sort_set(self, model, a, b, _data):
        # keep model iteration order stable: compare by row number
        ia = a.get_indices()[0]
        ib = b.get_indices()[0]
        return -1 if ia < ib else (1 if ia > ib else 0)

    def _flash(self, text):
        def _f():
            dlg = Gtk.MessageDialog(parent=self, modal=True,
                                    message_type=Gtk.MessageType.INFO,
                                    buttons=Gtk.ButtonsType.OK, text=text)
            dlg.run()
            dlg.destroy()
        self._post(_f)


def main():
    win = SpaceReclaimWindow()
    win.connect("destroy", Gtk.main_quit)
    win.show_all()
    win.present()
    Gtk.main()


if __name__ == "__main__":
    main()
