# agent-control-shell

**Give an AI agent root for twenty minutes — not forever.** A leased, policy-checked,
journalled root shell for Linux desktops, with a tray icon that shows the lease and ends it
in one click, and a status command any panel can poll.

```
  ○  no lease        ●  t1 / t2 live  (amber, countdown)        ⊖  SHELL live  (red, countdown)

  you:    tray ▸ Grant t2 ▸ 20 min   ──password──▸  /run/mrog/lease.json   (root-owned, expires by itself)
  agent:  mrog write /etc/foo.conf staged token     ──lease? scope? never-touch? allow-list? diff-token? validator?──▸ applied + journalled
  you:    middle-click the dot  ──no password──▸  lease destroyed             (or move on: it expires)
```

The idea: an agent that can run `sudo` can do anything, and "be careful" is not a control.
Here the capability is **time-boxed** (1–240 min, shell ≤ 60), **scoped** (`t1` units and
packages · `t2` + config writes · `shell` arbitrary root), **refused by default** (the
NOPASSWD binary is inert without a lease), **policy-checked per action** (allow-list,
never-touch list, diff confirmation, validators), **journalled** (every action, with caller
and session id; shell commands with their full output), and **visible** (the dot, the
countdown). Stopping is free; starting always costs the password.

Built and run on Linux Mint 22 / Cinnamon. The privileged pieces are ~700 lines of bash you
can read in one sitting. **The security review that found and fixed a real bypass is in the
sibling repo:** [mrog-lease/REVIEW.md](https://github.com/Associated2u/mrog-lease/blob/main/REVIEW.md).

## The tray — `acs/acs-tray.py`

`Gtk.StatusIcon`, ~180 lines, holds no privilege. It reads one file once a second and
draws a dot:

| glyph | state | tooltip |
|---|---|---|
| ○ hollow grey | no lease | *left-click: grant · middle-click: end* |
| ● amber | `t1` or `t2` live | `t2 lease · 14:32 left · by chris · note` |
| ⊖ red with a bar | `shell` live — arbitrary root | `SHELL lease · 08:10 left …` |
| blinking | last 60 s | |

**Left-click:** a menu — *Grant t1 ▸ 10/20/60 min*, *Grant t2 ▸ …*, *Grant SHELL ▸ 15/30*,
*End lease (no password)*, *Status*, *Journal (last 20)*, *Quit tray*. Granting raises the
polkit dialog (`auth_admin`, ceilings enforced by the root side). **Middle-click:** end the
lease — no menu, no dialog. That is the panic path, and it is one button.

Works in any XEmbed tray (Cinnamon, XFCE, MATE, LXQt, tint2, stalonetray); on a
StatusNotifier-only desktop the activate/popup fallbacks still give the menu.

## The panel — `acs status`, for whatever bar you run

```
acs status                       t2 · 14:31 left · by chris · note
acs status --format json         {"state":"t2","left":870,"expires_at":…,"by":"chris","note":"…"}
acs status --format waybar       {"text":"t2 14:30","alt":"t2","class":"t2","tooltip":"…"}
acs status --format polybar      %{F#e5a02e}● t2 14:30%{F-}
acs status --format i3           ● t2 14:30
```

`integrations/` has a drop-in for each: `waybar.jsonc`, `polybar.ini`, a Cinnamon
*Command Runner* recipe, and `gtk-pill/lease_dot.py` — the dot as a class you can draw into
your own cairo bar (this is how the [notch-pills](https://github.com/Associated2u/notch-pills)
system pill shows it). Every one of them only reads a file and calls `acs`.

## The CLI — `acs/acs`

```
acs grant <t1|t2|shell> <minutes> [note…]   password: sudo on a tty, polkit otherwise
acs end                                      no password (mrog-lease-kill); polkit fallback
acs journal [N]                              last N journalled actions
acs run <command…>                           arbitrary root under a SHELL lease, output journalled
```

## The root side — `root/`, `ui/`

This is the part with teeth; it is unchanged from the [mrog-lease](https://github.com/Associated2u/mrog-lease)
repo and installed by its own one-paste `sudo bash` installers, each of which validates its
sudoers fragment with `visudo -c` before it lands.

| | |
|---|---|
| `mrog-lease` | root-only: `grant / status / revoke`. Writes the lease (root:root 0644 in `/run/mrog`) — the user can read the countdown, never forge or extend it. |
| `mrog-apply` | **the one NOPASSWD binary.** Verbs `unit`, `pkg` (t1); `diff`, `write`, `revert` (t2); `run` (shell). Inert without a live lease of sufficient scope. |
| `mrog` | the user driver: `stage / diff / write / unit / pkg / run / journal / status / lease / unlease`. |
| `policy.conf` | allow-lists and the **never-touch** list, every glob quoted. |
| `mrog-lease-kill` | the second NOPASSWD binary: root-only, **no arguments**, deletes exactly the lease file. What makes stopping free. |
| `mrog-lease-ui` + `com.mrog.lease.policy` | the polkit front door the tray uses (`auth_admin`; `allow_any` / `allow_inactive` = no). |

**`write`, in order:** scope check → **canonical path** (`realpath -m`; `/etc//shadow` and
`/etc/../etc/shadow` used to slip past the never-touch list — found and fixed in the review)
→ never-touch → allow-list → the diff-token must match the diff *as it is now* → validator
(`systemd-analyze verify`, `sshd -t`) → snapshot to `/var/backups/` → `install` with the
original mode → `etckeeper commit` → journal.

**`shell` is honest about itself.** `mrog run` refuses a deny-list of the catastrophic
(`mkfs`, `rm -rf /`, `visudo`, key paths) and that list is a **tripwire, not a sandbox** —
the control is the 60-minute cap, your password to arm it, and the full-output journal in
`/var/log/mrog/run/`.

`hooks/guard-bash.sh` is the optional Claude Code `PreToolUse` hook: logs every Bash tool
call and refuses the obviously wrong. Keyword-level; an audit trail and a tripwire, not a
boundary.

## Install

```bash
sudo bash root/install-mrog.sh            # lease + apply + driver + policy + sudoers fragment
sudo bash root/install-mrog-lease-kill.sh # the free kill
sudo bash root/unlock-shell.sh            # only if you want the shell scope (read it first)
bash acs/install-acs.sh                   # user side: acs + tray + autostart. No root.
```

Then `acs status` → `no lease`, a hollow dot in the tray, and the installers' printed proof
steps (each gate driven to refuse before it is trusted to allow).

## Relationship to the other repos

| repo | what |
|---|---|
| **agent-control-shell** (this) | the root lease as a standalone product: tray, CLI, panel integrations |
| [mrog-lease](https://github.com/Associated2u/mrog-lease) | the whole lease layer incl. the **input** lease (agent keyboard/mouse), and the security review |
| [notch-pills](https://github.com/Associated2u/notch-pills) | the desktop panel that shows the same dot, plus everything else |

All three are public exports of one private development tree; machine and account names in
comments and docs are placeholders, the code paths and measurements are real.

MIT — [LICENSE](LICENSE).
