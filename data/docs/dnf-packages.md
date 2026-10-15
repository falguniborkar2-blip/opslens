# Package Management with DNF and RPM

## Everyday commands
`dnf install <pkg>`, `dnf remove <pkg>` and `dnf upgrade` cover most needs. `dnf search <term>`
searches names and summaries. `dnf provides /usr/bin/dig` finds which package ships a file
(here `bind-utils`).

## Information and history
`dnf info <pkg>` shows version and repository. `rpm -qa | grep <name>` lists installed packages and
`rpm -ql <pkg>` lists the files in one. `dnf history` shows past transactions and
`dnf history undo <id>` rolls one back.

## Repository problems
"Failed to download metadata for repo" usually points to network/DNS problems, a proxy, or a stale
cache. Try `dnf clean all && dnf makecache`. List repositories with `dnf repolist` and enable one with
`dnf config-manager --set-enabled <repo>`. On RHEL, content requires a registered system
(`subscription-manager status`).

## Locked database
"Waiting for process with pid ... to finish" means another dnf or PackageKit process holds the lock.
Wait for it to finish rather than deleting lock files.

## Verifying files
`rpm -V <pkg>` verifies installed files against the package database and reports changed sizes,
permissions or checksums, which helps spot accidental edits or tampering.
