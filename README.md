# printerscripts

A collection of handy little scripts for 3D printers, mostly Klipper/Moonraker ones.
Each script is standalone Python 3 (standard library only) and dry-runs by default where it can delete things.

## moonraker_cleanup

| Script | What it does |
| --- | --- |
| [`clean_old_prints.py`](moonraker_cleanup/clean_old_prints.py) | SSHes to a printer and deletes print files (`.gcode`, `.bgcode`, ...) older than N days, plus their `.thumbs` thumbnails. |
| [`clean_old_timelapses.py`](moonraker_cleanup/clean_old_timelapses.py) | SSHes to a printer and deletes timelapse videos, previews and frame zips (`~/timelapse`) older than N days. |
| [`clean_orphan_thumbs.py`](moonraker_cleanup/clean_orphan_thumbs.py) | Uses the Moonraker HTTP API to delete thumbnails left behind by print files that no longer exist. |

```sh
# List prints older than 30 days, then delete them
python moonraker_cleanup/clean_old_prints.py root@10.0.1.179
python moonraker_cleanup/clean_old_prints.py root@10.0.1.179 --days 30 --delete

# Delete timelapses older than 14 days
python moonraker_cleanup/clean_old_timelapses.py root@10.0.1.179 --days 14 --delete

# Find and delete orphaned thumbnails on one or more printers
python moonraker_cleanup/clean_orphan_thumbs.py 10.0.1.179 10.0.1.180 --delete
```

Run any script with `--help` for all options.
