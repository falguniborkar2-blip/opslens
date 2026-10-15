# Troubleshooting systemd Services

## Checking the state of a service
Use `systemctl status <unit>` to see whether a unit is active, inactive or failed, its main PID,
memory use and the last few log lines. `systemctl is-active <unit>` and `systemctl is-enabled <unit>`
return a single word and are handy in scripts. To list every unit that has failed since boot run
`systemctl --failed`.

## A service fails to start
1. Read the logs for the unit: `journalctl -u <unit> -b --no-pager` shows messages from the current boot.
2. Look for the exit code in `systemctl status`. `status=203/EXEC` means the binary in `ExecStart`
   could not be executed (wrong path or missing execute permission). `status=217/USER` means the
   `User=` in the unit does not exist.
3. Validate the unit file with `systemd-analyze verify /etc/systemd/system/<unit>.service`.
4. After editing a unit file always run `systemctl daemon-reload` before restarting, otherwise
   systemd keeps using the old definition.

## Service keeps restarting
If `Restart=on-failure` is set, a crashing service is restarted until it hits the start limit
(`StartLimitBurst` within `StartLimitIntervalSec`), after which systemd reports
"start request repeated too quickly". Fix the underlying error, then clear the counter with
`systemctl reset-failed <unit>`.

## Overriding a vendor unit safely
Never edit files in `/usr/lib/systemd/system`; package updates overwrite them. Run
`systemctl edit <unit>` to create a drop-in in `/etc/systemd/system/<unit>.d/override.conf`.
`systemctl cat <unit>` shows the merged result.

## Enabling at boot
`systemctl enable --now <unit>` enables the unit at boot and starts it immediately.
`systemctl disable` removes the boot symlinks but does not stop a running service.
