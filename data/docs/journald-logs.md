# Reading Logs with journalctl

## Filtering
`journalctl -u <unit>` filters by systemd unit, `-b` limits to the current boot (`-b -1` the previous
boot), `-p err` shows only priority error and above, and `--since "1 hour ago"` limits by time.
`-f` follows new messages like `tail -f`. Combine them, for example
`journalctl -u nginx -p warning --since today`.

## Kernel messages
`journalctl -k` shows kernel messages, equivalent to `dmesg`. It is where hardware errors, OOM kills
and filesystem errors appear.

## Persistent logs
On some systems the journal is kept only in memory under `/run/log/journal` and is lost at reboot.
Create `/var/log/journal` (or set `Storage=persistent` in `/etc/systemd/journald.conf`) and restart
`systemd-journald` to keep logs across reboots, which is needed to debug crashes with `-b -1`.

## Output formats
`-o json-pretty` prints structured fields, useful for scripts and log shippers. `-o short-iso` gives
ISO timestamps.
