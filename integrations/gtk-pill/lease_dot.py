"""lease_dot — the lease indicator as a drop-in for a cairo-drawn panel or pill.

Reference for anyone building their own bar in GTK/cairo (this is how the notch-pills
system pill shows it). Read the lease once a second, draw a dot, hand clicks to `acs`.

    from lease_dot import LeaseDot
    dot = LeaseDot()                 # in your widget's tick():  dot.refresh()
    dot.draw(cr, x, y, r)            # in on_draw
    dot.click(button)                # 1 = grant (t1, 20 min), 2 = end

No privilege here. Grant goes through `acs grant` (polkit), end through `acs end`.
"""
import json, os, shutil, subprocess, time

LEASE = os.environ.get("ACS_LEASE", "/run/mrog/lease.json")
ACS = shutil.which("acs") or os.path.expanduser("~/.local/bin/acs")
COL = {"none": (0.48, 0.50, 0.55), "t1": (0.90, 0.63, 0.18), "t2": (0.90, 0.63, 0.18),
       "shell": (0.88, 0.29, 0.29)}


class LeaseDot:
    def __init__(self):
        self.state, self.left, self.by, self.note = "none", 0, "", ""

    def refresh(self):
        """One file read. Never raises, never blocks."""
        try:
            with open(LEASE) as f:
                d = json.load(f)
            left = int(d.get("expires_at", 0) - time.time())
            if left > 0:
                self.state, self.left = d.get("scope", "?"), left
                self.by, self.note = d.get("granted_by", "?"), d.get("note") or ""
                return
        except Exception:
            pass
        self.state, self.left = "none", 0

    def label(self):
        return "no lease" if self.state == "none" else "%s %d:%02d" % (
            self.state.upper() if self.state == "shell" else self.state, self.left // 60, self.left % 60)

    def draw(self, cr, x, y, r):
        col = COL.get(self.state, COL["none"])
        cr.new_sub_path(); cr.arc(x, y, r, 0, 6.2832)
        if self.state == "none":
            cr.set_source_rgb(*col); cr.set_line_width(max(1.0, r * 0.35)); cr.stroke()
        else:
            cr.set_source_rgb(*col); cr.fill()

    def click(self, button, scope="t1", minutes=20):
        argv = [ACS, "end"] if button == 2 else [ACS, "grant", scope, str(minutes)]
        subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
