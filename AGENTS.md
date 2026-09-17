# Working on agent-control-shell (for AI coding agents and contributors)

You are working on the layer that decides what an agent like you may do as root. Read
README.md, then the sibling review: mrog-lease/REVIEW.md.

- **This repo is a scrubbed export of the maintainer's working tree.** Send fixes as PRs; they
  are ported back and return in the next export. After any change to `root/`, `cmp` the
  installed copy against the source -- a difference is a finding.
- **The tray and `acs` hold no privilege, and must stay that way.** Grant goes through polkit
  or a tty password prompt; end goes through the delete-only kill helper. Do not add a code
  path that reaches root any other way.
- **Nothing on the tray's tick may block.** One file read per second. Every action is a
  child process.
- **Never install the root side yourself.** Each installer is a `sudo bash` paste by the
  human, on purpose. Do not propose NOPASSWD rules or widen a fragment.
- **Policy decisions happen on canonical paths** (`canon()` in `mrog-apply`); every glob in
  `policy.conf` stays quoted.
- **Prove by effect.** `acs status` on none / a fake live lease (`ACS_LEASE=…`) / an expired
  one; the tray under `timeout` with a fake lease; `--glyphs DIR` to eyeball the four states.

Quick check:
`bash -n acs/acs acs/install-acs.sh root/* ui/mrog-lease-ui hooks/*.sh && python3 -c "import ast;[ast.parse(open(f).read()) for f in ('acs/acs-tray.py','integrations/gtk-pill/lease_dot.py')]"`
