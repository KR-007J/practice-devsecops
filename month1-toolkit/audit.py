#!/usr/bin/env python3
"""
Linux Security Audit Script
Checks for: SUID/SGID binaries, world-writable files, UID=0 accounts.
Read-only — makes no changes to the system.
Outputs structured JSON for further processing or diffing over time.
"""

import os
import json
import stat
import pwd
from datetime import datetime, timezone


def find_suid_sgid(scan_paths=None):
    """Find all SUID and SGID binaries under given paths."""
    if scan_paths is None:
        scan_paths = ["/usr/bin", "/usr/sbin", "/bin", "/sbin"]
    findings = []
    for base in scan_paths:
        if not os.path.isdir(base):
            continue
        for root, dirs, files in os.walk(base):
            for name in files:
                path = os.path.join(root, name)
                try:
                    st = os.lstat(path)
                except (OSError, PermissionError):
                    continue
                if stat.S_ISLNK(st.st_mode):
                    continue  # skip symlinks, only interested in real binaries
                mode = st.st_mode
                is_suid = bool(mode & stat.S_ISUID)
                is_sgid = bool(mode & stat.S_ISGID)
                if is_suid or is_sgid:
                    findings.append({
                        "path": path,
                        "suid": is_suid,
                        "sgid": is_sgid,
                        "permissions": oct(stat.S_IMODE(mode)),
                        "owner_uid": st.st_uid,
                    })
    return findings


def find_world_writable(scan_paths=None):
    """Find world-writable files (any user can modify these).

    Note: symlinks are always reported as mode 777 by the OS regardless of
    their target's real permissions - that's standard Unix behavior, not a
    security issue. We skip them here to avoid false positives; the target
    file's own permissions are what actually matter and would be reported
    separately if scanned directly.
    """
    if scan_paths is None:
        scan_paths = ["/etc", "/usr/bin", "/usr/sbin", "/opt"]
    findings = []
    for base in scan_paths:
        if not os.path.isdir(base):
            continue
        for root, dirs, files in os.walk(base):
            for name in files:
                path = os.path.join(root, name)
                try:
                    st = os.lstat(path)
                except (OSError, PermissionError):
                    continue
                if stat.S_ISLNK(st.st_mode):
                    continue  # symlinks always show 777, not a real finding
                mode = st.st_mode
                if mode & stat.S_IWOTH:
                    findings.append({
                        "path": path,
                        "permissions": oct(stat.S_IMODE(mode)),
                    })
    return findings


def find_uid_zero_accounts():
    """Find all accounts with UID=0 (root-equivalent) — should normally be only 'root'."""
    findings = []
    for entry in pwd.getpwall():
        if entry.pw_uid == 0:
            findings.append({
                "username": entry.pw_name,
                "uid": entry.pw_uid,
                "shell": entry.pw_shell,
            })
    return findings


def main():
    report = {
        "scan_time_utc": datetime.now(timezone.utc).isoformat(),
        "hostname": os.uname().nodename,
        "suid_sgid_binaries": find_suid_sgid(),
        "world_writable_files": find_world_writable(),
        "uid_zero_accounts": find_uid_zero_accounts(),
    }
    report["summary"] = {
        "suid_sgid_count": len(report["suid_sgid_binaries"]),
        "world_writable_count": len(report["world_writable_files"]),
        "uid_zero_count": len(report["uid_zero_accounts"]),
    }

    output_file = "audit-report.json"
    with open(output_file, "w") as f:
        json.dump(report, f, indent=2)

    print(f"Audit complete. Report saved to {output_file}")
    print(f"  SUID/SGID binaries found: {report['summary']['suid_sgid_count']}")
    print(f"  World-writable files found: {report['summary']['world_writable_count']}")
    print(f"  UID=0 accounts found: {report['summary']['uid_zero_count']}")

    if report["summary"]["uid_zero_count"] > 1:
        print("  WARNING: More than one UID=0 account exists — investigate immediately.")


if __name__ == "__main__":
    main()
