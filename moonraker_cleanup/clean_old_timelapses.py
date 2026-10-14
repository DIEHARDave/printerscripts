#!/usr/bin/env python3
"""Delete timelapse videos and files older than N days from a printer over SSH.

moonraker-timelapse saves each render into its output folder (~/timelapse by
default) as <name>.mp4, a <name>.jpg preview and, if saveframes is on, a
<name>_frames.zip. This removes any of those older than --days. The frames of
a timelapse in progress live in /tmp/timelapse and are never touched.
Works with BusyBox find/sh, so it runs on stock-ish printers too.

Uses the system ssh client (OpenSSH ships with Windows 10+), so set up a key
or expect a password prompt. Dry run by default; pass --delete to remove.

    python clean_old_timelapses.py root@10.0.1.179
    python clean_old_timelapses.py pi@10.0.1.180 --days 14 --delete
    python clean_old_timelapses.py root@10.0.1.179 --path /usr/data/timelapse
"""
import argparse
import shlex
import subprocess
import sys

PATTERNS = ("*.mp4", "*.jpg", "*_frames.zip")

REMOTE_SCRIPT = r"""
DIR={dir}
[ -d "$DIR" ] || {{ echo "no such folder: $DIR" >&2; exit 2; }}
find "$DIR" -maxdepth 1 -type f \( {names} \) -mtime +{days} -print |
{{
    n=0
    while IFS= read -r f; do
        echo "$f"
        n=$((n + 1))
        [ {delete} = 1 ] && rm -f "$f"
    done
    echo "$n file(s)" >&2
}}
"""


def remote_path(path):
    # Let the remote shell expand a leading ~ to its own $HOME
    if path == "~":
        return '"$HOME"'
    if path.startswith("~/"):
        return '"$HOME"/' + shlex.quote(path[2:])
    return shlex.quote(path)


def main():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("host", help="ssh target, e.g. root@10.0.1.179")
    p.add_argument("--days", type=int, default=30, help="delete timelapses older than this (default 30)")
    p.add_argument("--path", default="~/timelapse", help="timelapse output folder on the printer")
    p.add_argument("--port", type=int, default=22)
    p.add_argument("--delete", action="store_true", help="actually delete (default is dry run)")
    args = p.parse_args()

    names = " -o ".join(f"-name '{pat}'" for pat in PATTERNS)
    script = REMOTE_SCRIPT.format(
        dir=remote_path(args.path),
        names=names,
        days=args.days,
        delete=1 if args.delete else 0,
    )

    print(f"{'Deleting' if args.delete else 'Would delete'} timelapses older than "
          f"{args.days} days on {args.host}:{args.path}")
    # Send bytes: text mode on Windows would turn \n into \r\n and break sh
    r = subprocess.run(["ssh", "-p", str(args.port), args.host, "sh", "-s"], input=script.encode())
    if r.returncode == 0 and not args.delete:
        print("Dry run - pass --delete to remove these.")
    sys.exit(r.returncode)


if __name__ == "__main__":
    main()
