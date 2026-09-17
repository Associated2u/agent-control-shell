# Cinnamon — without the tray

Two options if you would rather have it in a panel than in the tray:

1. **The tray is the panel.** Cinnamon's system tray applet hosts `acs-tray` directly —
   run `install-acs.sh` and the dot appears in the tray area of whichever panel holds it.

2. **A text applet.** Install the *Command Runner* applet (Spices: `command-runner@ghent`),
   add it to a panel, set the command to `acs status --format i3` and the interval to
   1 s. It shows `● t2 14:32` while a lease is live and nothing when idle. Set
   "on click" to `acs end` for the free stop.

Either way the privileged parts are untouched: the panel only reads a file and calls `acs`.
