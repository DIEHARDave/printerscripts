#!/usr/bin/env python3
"""Delete thumbnails left behind by print files that no longer exist.

Moonraker extracts thumbnails into a .thumbs folder next to each print file
but never removes them when the print is deleted. On slow printers (e.g. the
AD5M) a large .thumbs folder makes directory listings block Moonraker for
long enough that Mainsail's startup scan loses its websocket, which is why
the .theme folder sometimes doesn't load.

Checks two kinds of thumbnail folders under the gcodes root:
  .thumbs  Moonraker's: "<print stem>-<W>x<H>.png", matched against the
           print files in the folder that contains it.
  thum     FlashForge stock firmware's: "<print stem>.<ext>", matched against
           print files anywhere under gcodes.

Talks to Moonraker over its HTTP API, so nothing needs installing on the
printer. Dry run by default; pass --delete to remove the files.

    python clean_orphan_thumbs.py 10.0.1.179 10.0.1.180
    python clean_orphan_thumbs.py 10.0.1.179:7125 --delete
"""
import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

THUMB_DIRS = (".thumbs", "thum")
SIZE_SUFFIX = re.compile(r"-\d+x\d+$")
TIMEOUT = 180  # listing a big folder on an AD5M can take well over 10 s


def request(base, method, path, query=None):
    url = base + path
    if query:
        url += "?" + urllib.parse.urlencode(query)
    req = urllib.request.Request(url, method=method)
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        return json.load(resp)["result"]


def list_dir(base, path):
    return request(base, "GET", "/server/files/directory", {"path": path})


def walk(base, path="gcodes"):
    """Yields (path, listing) for every folder under path, not entering thumbnail folders."""
    listing = list_dir(base, path)
    yield path, listing
    for d in listing.get("dirs", []):
        if d["dirname"] not in THUMB_DIRS:
            yield from walk(base, path + "/" + d["dirname"])


def stem(filename):
    return os.path.splitext(filename)[0]


def find_orphans(base):
    """Returns a list of (path relative to gcodes, size) for orphaned thumbnails."""
    folders = dict(walk(base))
    all_stems = {stem(f["filename"]) for listing in folders.values() for f in listing.get("files", [])}
    orphans = []
    for path, listing in folders.items():
        local_stems = {stem(f["filename"]) for f in listing.get("files", [])}
        for d in listing.get("dirs", []):
            name = d["dirname"]
            if name not in THUMB_DIRS:
                continue
            thumb_path = path + "/" + name
            for f in list_dir(base, thumb_path).get("files", []):
                owner = stem(f["filename"])
                if name == ".thumbs":
                    keep = SIZE_SUFFIX.sub("", owner) in local_stems or owner in local_stems
                else:
                    keep = owner in all_stems
                if not keep:
                    rel = (thumb_path + "/" + f["filename"])[len("gcodes/"):]
                    orphans.append((rel, f.get("size", 0)))
    return orphans


def base_url(host):
    if "://" not in host:
        host = "http://" + host
    return host.rstrip("/")


def clean(host, delete):
    base = base_url(host)
    print(f"== {host}: scanning gcodes (this can take a minute on slow printers)")
    orphans = find_orphans(base)
    total = sum(size for _, size in orphans)
    print(f"   {len(orphans)} orphaned thumbnails, {total / 1e6:.1f} MB")
    for rel, _ in orphans[:5]:
        print(f"     {rel}")
    if len(orphans) > 5:
        print(f"     ... and {len(orphans) - 5} more")
    if not orphans or not delete:
        return 0
    failed = 0
    for rel, _ in orphans:
        try:
            request(base, "DELETE", "/server/files/gcodes/" + urllib.parse.quote(rel))
        except (urllib.error.URLError, OSError) as e:
            failed += 1
            print(f"   failed: {rel}: {e}")
    print(f"   deleted {len(orphans) - failed}, failed {failed}")
    return 1 if failed else 0


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("hosts", nargs="+", help="printer address, e.g. 10.0.1.179 or 10.0.1.179:7125")
    ap.add_argument("--delete", action="store_true", help="delete the orphans (default is a dry run)")
    args = ap.parse_args()
    status = 0
    for host in args.hosts:
        try:
            status |= clean(host, args.delete)
        except (urllib.error.URLError, OSError, KeyError, ValueError) as e:
            print(f"   error talking to {host}: {e}")
            status = 1
    if not args.delete:
        print("\nDry run. Re-run with --delete to remove them.")
    return status


if __name__ == "__main__":
    sys.exit(main())
