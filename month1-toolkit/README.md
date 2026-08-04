# Practice DevSecOps — Month 1: Linux Security Toolkit

A Linux security auditing and hardening toolkit: a Python script that inspects a system for common misconfigurations, and a Bash hardening script, validated against real Lynis benchmark scans.

---

## What This Project Demonstrates

- Practical Linux permission model knowledge (SUID/SGID, world-writable files, UID=0 accounts)
- Debugging a real false-positive in my own security tool (symlink permission bits)
- Safe, idempotent system hardening scripting practices
- Honest interpretation of benchmark results — including when a hardening effort *doesn't* move a score, and why

---

## Project Structure

```
month1-toolkit/
├── audit.py               # Read-only Python audit script
├── harden.sh               # Bash hardening script (SSH config, firewall)
├── audit-report.json       # Sample audit output
├── lynis-before.txt        # Lynis scan, SSH active, before hardening
├── lynis-after.txt         # Lynis scan, SSH active, after hardening
├── lynis-suggestions-full.txt
└── README.md
```

---

## Part 1: The Audit Script (`audit.py`)

Read-only — makes zero changes to the system. Checks three categories:

| Check | Why it matters |
|---|---|
| SUID/SGID binaries | Programs that run with the file owner's (often root's) privileges — a classic privilege escalation vector if a binary is vulnerable or unexpected |
| World-writable files | Any local user can modify these — risk of tampering or backdoor insertion |
| UID=0 accounts | Multiple accounts with root-equivalent privileges beyond the default `root` — a sign of hidden backdoor accounts |

Output is structured JSON, so results can be diffed over time or fed into other tooling, not just read once and discarded.

### A real bug I found and fixed: symlinks and the "1835 false positives" problem

First run of the world-writable check returned **1835 findings** — an alarming number. Investigating the actual paths showed the list was dominated by files like `/etc/localtime` and `/etc/ssl/certs/*.0` — all symlinks.

**Root cause:** on Linux, a symlink's own permission bits are always reported as `777` (rwxrwxrwx) by the OS, regardless of what the symlink points to. That's standard Unix behavior, not a security issue — the target file's real permissions are what actually matter. My script used `os.lstat()` (correctly, to avoid following broken symlinks), but didn't account for this always-777 symlink quirk, so every symlink was flagged as a false positive.

**Fix:**
```python
if stat.S_ISLNK(st.st_mode):
    continue  # symlinks always show 777, not a real finding
```
After the fix, the same scan returned **0** world-writable files — the accurate, meaningful result.

### Real audit results on my system

```
SUID/SGID binaries found: 80
World-writable files found: 0
UID=0 accounts found: 1
```

80 SUID/SGID binaries is a normal range for a full desktop Linux install (things like `passwd`, `sudo`, `su`, `mount` — all expected). 0 world-writable files and exactly 1 UID=0 account (`root` only) are both healthy results.

---

## Part 2: The Hardening Script (`harden.sh`)

Applies SSH hardening (disable root login, disable password authentication, disable empty passwords) and configures basic firewall default-deny rules via `ufw` or `firewalld`, whichever is present.

**Safety design choices:**
- `set -euo pipefail` — exits immediately on any error or undefined variable, rather than silently continuing after something breaks
- Interactive confirmation prompt before making any changes
- Backs up the original `sshd_config` with a timestamp before modifying it
- Detects available firewall tool rather than assuming one exists
- `sed` patterns handle both commented and already-set config lines, making the script safe to re-run

---

## Part 3: Lynis Validation — An Honest Result, Not a Padded One

### The real before/after numbers

| Metric | Before | After |
|---|---|---|
| Hardening index | 65 | 65 |
| Tests performed | 257 | 257 |

**The index did not change.** I want to explain why honestly rather than omit or dress this up, because the investigation itself is the actual learning outcome here.

### What actually happened, step by step

1. First hardening attempt showed no change because `sshd` was disabled on this desktop machine — Lynis doesn't meaningfully score SSH configuration for a service that isn't running.
2. I enabled `sshd`, re-ran a genuine before-scan (65/257), ran `harden.sh` (confirmed real changes: `PermitRootLogin no`, `PasswordAuthentication no`, `PermitEmptyPasswords no` written to `sshd_config`, backup created), then re-ran Lynis.
3. The score still didn't move. Checking the full 35-item suggestion list confirmed why: Lynis's `[SSH-7408] Consider hardening SSH configuration` finding was still present, and none of the 35 suggestions were resolved by my script's three directive changes — Lynis's hardening index is a weighted score across 257 individual checks, and three SSH directives represent too small a fraction of the total weighted score to move an integer percentage.

### The real, more valuable output: 35 specific findings

Rather than one abstract number, Lynis produced a concrete, actionable backlog. A sample of what it actually flagged:

- `[SSH-7408]` Consider hardening SSH configuration further
- `[AUTH-9230]` Configure password hashing rounds in `/etc/login.defs`
- `[AUTH-9262]` Install a PAM module for password strength testing
- `[AUTH-9328]` Default umask in `/etc/login.defs` could be more strict (027)
- `[BOOT-5122]` Set a password on the GRUB boot loader
- `[ACCT-9628]` Enable `auditd` to collect audit information
- `[FINT-4350]` Install a file integrity monitoring tool
- `[HRDN-7230]` Install a malware scanner for periodic filesystem scans
- `[KRNL-6000]` Several sysctl values differ from the hardening profile

(Full list of all 35 in `lynis-suggestions-full.txt`.)

### The actual lesson

A single hardening script addressing 2-3 settings has limited measurable impact on an aggregate benchmark score. Meaningful hardening improvement requires systematically working through findings across many categories — authentication policy, kernel parameters, logging/auditing, boot security, file integrity monitoring — which is exactly what a tool like Lynis is designed to surface. The suggestion list, not the single index number, is the actually useful output of this exercise.

---

## How to Run

```bash
git clone https://github.com/KR-007J/practice-devsecops.git
cd practice-devsecops/month1-toolkit

# Read-only audit — safe to run anytime
python3 audit.py
cat audit-report.json

# Review harden.sh before running — it modifies SSH config and firewall rules
chmod +x harden.sh
./harden.sh

# Measure the result
sudo lynis audit system
```

⚠️ Review `harden.sh` fully before running on any machine you access remotely — it disables SSH password authentication, which will lock you out if you don't have a working SSH key configured first.

---

## Interview Q&A

**Q: Walk me through this project.**
A: A Python script audits a Linux system read-only, checking for SUID/SGID binaries, world-writable files, and unexpected UID=0 accounts, outputting structured JSON. A separate Bash script applies SSH and firewall hardening. I validated the actual effect using Lynis, a real benchmarking tool — and found a genuinely interesting result: the hardening index didn't move, which led me to investigate why and produced a more useful concrete finding than the number itself.

**Q: Tell me about a bug you found in your own tool.**
A: My world-writable file check initially returned 1835 results — clearly wrong. Investigating showed the list was dominated by symlinks like `/etc/localtime`, and I learned that symlinks always report `777` permissions on Linux regardless of their target's real permissions — that's standard OS behavior, not a security issue. I added an explicit symlink skip using `stat.S_ISLNK()`, and the count dropped to an accurate 0. I documented this in the script itself as a comment, not just fixed it silently.

**Q: Your hardening script didn't change the Lynis score. Doesn't that mean it failed?**
A: No — I verified the script genuinely worked (config file modified, backup created, confirmed via `grep` against the live `sshd_config`), and I investigated why the aggregate score didn't move: Lynis's hardening index averages across 257 individual weighted checks, and three SSH directive changes are a small fraction of that. The more useful output was Lynis's list of 35 specific, actionable findings across categories my script didn't touch — GRUB password, audit logging, file integrity monitoring, kernel sysctl tuning. That's a more honest and more useful result than an inflated score.

**Q: What's the difference between SUID and SGID?**
A: SUID makes a program run with the file owner's privileges rather than the executing user's — e.g., `passwd` needs SUID root to write to `/etc/shadow`. SGID does the same for group privileges, or on a directory, makes new files inherit the directory's group. Both are legitimate mechanisms for specific binaries, but unnecessary or unexpected SUID/SGID bits are a classic audit finding and a common privilege escalation vector if the binary itself has a vulnerability.

**Q: Why separate the audit script (read-only) from the hardening script (modifies the system)?**
A: Safety and repeatability. The audit script can be run anytime, even on a schedule, with zero risk since it never changes anything. The hardening script is a higher-risk, deliberate action — it backs up config before touching it and requires interactive confirmation. Keeping them separate means you can audit as often as you like without any chance of accidentally modifying a live system.

**Q: What would you add to make this production-ready?**
A: Address the actual Lynis suggestion backlog systematically — starting with `auditd` for audit logging, a file integrity monitoring tool, and GRUB boot password, since those cover categories with real security impact beyond SSH config alone. I'd also convert the audit script into a scheduled check with drift alerting, and add a `--dry-run` mode to the hardening script so changes can be previewed before being applied.

---

## Author

Krish Joshi — B.Tech CSE (Cybersecurity), building toward a DevSecOps career.
