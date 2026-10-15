# Disk Full and Disk Space Problems

## Find which filesystem is full
`df -h` shows size, used and available space per mounted filesystem. A filesystem can also run out
of inodes while still having free bytes: check with `df -i`. Many tiny files (for example session
files or a mail queue) are the usual cause of inode exhaustion.

## Find what is using the space
`du -xh --max-depth=1 / | sort -h` summarises directory sizes on one filesystem without crossing
mount points. `ncdu` gives an interactive view if it is installed. Common culprits are `/var/log`,
`/var/lib/containers`, `/var/cache/dnf` and core dumps in `/var/lib/systemd/coredump`.

## Space not freed after deleting a file
If `df` still reports the disk as full after you deleted a large log file, a process probably still
holds the file open. The data is only released when the last file descriptor is closed. Find such
files with `lsof +L1` (open files with a link count of zero) and restart the owning process, or
truncate the file instead of deleting it: `: > /var/log/big.log`.

## Shrinking the systemd journal
Check its size with `journalctl --disk-usage`. Reduce it with `journalctl --vacuum-size=500M` or
`journalctl --vacuum-time=2weeks`. Make the limit permanent with `SystemMaxUse=` in
`/etc/systemd/journald.conf`.

## Cleaning package and container caches
`dnf clean all` removes cached package metadata and downloaded RPMs. For containers,
`podman system df` shows usage and `podman system prune` removes unused images, containers and
build cache.
