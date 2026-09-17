#!/usr/bin/env python3
"""acs-tray — a system-tray icon for the leased root shell (agent-control-shell).

    ○  grey   no lease                 left-click  -> menu (grant / end / status / journal)
    ●  amber  t1 or t2 live            middle-click -> END the lease, no menu, no dialog
    ●  red    SHELL live               tooltip: scope · time left · who · note
    blinks during the last 60 s

The tray holds NO privilege: granting runs `acs grant` (polkit dialog), ending runs
`acs end` (the delete-only NOPASSWD kill helper). It reads one file at 1 Hz and nothing
else -- no subprocess on the tick, nothing that can block.

Gtk.StatusIcon is deprecated, but it is the only X11 API that delivers per-button tray
clicks and it works on Cinnamon, XFCE, MATE, LXQt and any bar with an XEmbed tray. On a
StatusNotifier-only desktop the "activate" / "popup-menu" fallbacks still give a menu.
"""
import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk, GLib
import cairo, json, os, sys, subprocess, time, signal, warnings

warnings.filterwarnings("ignore", category=DeprecationWarning)

HERE = os.path.dirname(os.path.abspath(__file__))
ACS = os.environ.get("ACS_BIN", os.path.join(HERE, "acs"))
LEASE = os.environ.get("ACS_LEASE", "/run/mrog/lease.json")
JOURNAL_TERM = os.environ.get("ACS_TERMINAL", "x-terminal-emulator")
ICON_PX = 22
GRANTS = [("t1", (10, 20, 60)), ("t2", (10, 20, 60)), ("shell", (15, 30))]

COL = {"none": (0.48, 0.50, 0.55), "t1": (0.90, 0.63, 0.18), "t2": (0.90, 0.63, 0.18),
       "shell": (0.88, 0.29, 0.29)}


def read_lease():
    """-> dict(state, left, by, note) ; never raises, never blocks."""
    try:
        with open(LEASE) as f:
            d = json.load(f)
        left = int(d.get("expires_at", 0) - time.time())
        if left <= 0:
            return {"state": "none", "left": 0}
        return {"state": d.get("scope", "?"), "left": left,
                "by": d.get("granted_by", "?"), "note": d.get("note") or ""}
    except Exception:
        return {"state": "none", "left": 0}


def draw(px, state, dim=False):
    """Filled dot with a dark hairline so it reads on light and dark panels alike."""
    s = cairo.ImageSurface(cairo.FORMAT_ARGB32, px, px)
    cr = cairo.Context(s)
    r = px * 0.34
    cx = cy = px / 2
    col = COL.get(state, COL["none"])
    if dim:
        col = tuple(c * 0.45 for c in col)
    if state == "none":
        # Hollow: a dark ring with the grey ring inside it. (A filled dark disc under a
        # hollow ring rendered as a solid black dot on light panels -- measured.)
        cr.new_sub_path(); cr.arc(cx, cy, r, 0, 6.2832)
        cr.set_source_rgb(0.08, 0.09, 0.11); cr.set_line_width(3.4); cr.stroke()
        cr.new_sub_path(); cr.arc(cx, cy, r, 0, 6.2832)
        cr.set_source_rgb(*col); cr.set_line_width(1.6); cr.stroke()
        return Gdk.pixbuf_get_from_surface(s, 0, 0, px, px)
    cr.new_sub_path(); cr.arc(cx, cy, r + 1.2, 0, 6.2832)
    cr.set_source_rgb(0.08, 0.09, 0.11); cr.fill()
    cr.new_sub_path(); cr.arc(cx, cy, r, 0, 6.2832)
    cr.set_source_rgb(*col); cr.fill()
    if state == "shell":                       # a bar across the dot: "open shell"
        cr.set_source_rgb(0.08, 0.09, 0.11); cr.set_line_width(1.8)
        cr.move_to(cx - r * 0.55, cy); cr.line_to(cx + r * 0.55, cy); cr.stroke()
    return Gdk.pixbuf_get_from_surface(s, 0, 0, px, px)


def mmss(left):
    return "%d:%02d" % (left // 60, left % 60)


class Tray:
    def __init__(self):
        signal.signal(signal.SIGTERM, lambda *_: Gtk.main_quit())
        signal.signal(signal.SIGINT, lambda *_: Gtk.main_quit())
        self.icon = Gtk.StatusIcon()
        self.icon.set_title("agent-control-shell")
        self._painted = None
        self._blink = False
        self.icon.connect("button-press-event", self._press)
        self.icon.connect("activate", lambda *_: self._menu(1, Gtk.get_current_event_time()))
        self.icon.connect("popup-menu", lambda _i, b, t: self._menu(b, t))
        self._tick()
        GLib.timeout_add(1000, self._tick)

    # ---- state -> pixels, once a second, one file read ------------------------
    def _tick(self):
        d = read_lease()
        st, left = d["state"], d["left"]
        blink = st != "none" and left <= 60
        self._blink = (not self._blink) if blink else False
        key = (st, self._blink)
        if key != self._painted:
            self._painted = key
            self.icon.set_from_pixbuf(draw(ICON_PX, st, dim=self._blink))
        if st == "none":
            tip = "agent-control-shell: no lease\nleft-click: grant · middle-click: end"
        else:
            tip = "agent-control-shell: %s lease · %s left · by %s%s\nmiddle-click ends it" % (
                st.upper() if st == "shell" else st, mmss(left), d.get("by", "?"),
                (" · " + d["note"]) if d.get("note") else "")
        self.icon.set_tooltip_text(tip)
        return True

    # ---- clicks ------------------------------------------------------------------
    def _press(self, _icon, ev):
        if ev.button == 2:
            self._run("end"); return True
        if ev.button in (1, 3):
            self._menu(ev.button, ev.time); return True
        return False

    def _menu(self, button, when):
        m = Gtk.Menu()
        st = read_lease()["state"]
        for scope, minutes in GRANTS:
            sub = Gtk.Menu()
            for mins in minutes:
                it = Gtk.MenuItem(label="%d min" % mins)
                it.connect("activate", lambda _w, s=scope, n=mins: self._run("grant", s, str(n)))
                sub.append(it)
            top = Gtk.MenuItem(label="Grant %s" % ("SHELL (arbitrary root)" if scope == "shell" else scope))
            top.set_submenu(sub); m.append(top)
        m.append(Gtk.SeparatorMenuItem())
        end = Gtk.MenuItem(label="End lease  (no password)")
        end.set_sensitive(st != "none")
        end.connect("activate", lambda *_: self._run("end")); m.append(end)
        m.append(Gtk.SeparatorMenuItem())
        for label, verb in (("Status", "status"), ("Journal (last 20)", "journal")):
            it = Gtk.MenuItem(label=label)
            it.connect("activate", lambda _w, v=verb: self._terminal(v)); m.append(it)
        m.append(Gtk.SeparatorMenuItem())
        q = Gtk.MenuItem(label="Quit tray"); q.connect("activate", lambda *_: Gtk.main_quit()); m.append(q)
        m.show_all()
        m.popup(None, None, Gtk.StatusIcon.position_menu, self.icon, button, when)

    # ---- actions: always a child, never on the tick ------------------------------
    def _run(self, *argv):
        try:
            subprocess.Popen([ACS, *argv], stdin=subprocess.DEVNULL,
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass

    def _terminal(self, verb):
        cmd = "%s %s; echo; read -rp 'enter to close '" % (ACS, verb)
        try:
            subprocess.Popen([JOURNAL_TERM, "-e", "bash", "-c", cmd],
                             stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass


if __name__ == "__main__":
    if "--glyphs" in sys.argv:          # write the four states as PNGs, for docs/tests
        out = sys.argv[sys.argv.index("--glyphs") + 1]
        for st in ("none", "t1", "t2", "shell"):
            draw(48, st).savev(os.path.join(out, "acs-%s.png" % st), "png", [], [])
        print("wrote", out); sys.exit(0)
    Tray()
    Gtk.main()
