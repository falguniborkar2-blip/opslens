# SSH Login Problems

## Permission denied (publickey)
The server rejected every key the client offered. Check that your public key is in
`~/.ssh/authorized_keys` on the server and that permissions are strict: `~/.ssh` must be `700` and
`authorized_keys` `600`, owned by the user. sshd ignores keys in group- or world-writable
directories. On SELinux systems run `restorecon -Rv ~/.ssh` if files were copied in.

## Debugging from the client
`ssh -vvv user@host` prints which keys are offered and where authentication fails.

## Debugging on the server
Read sshd logs with `journalctl -u sshd`. Validate configuration changes with `sshd -t` before
restarting; a syntax error can lock you out of a remote machine.

## Connection refused or timed out
"Connection refused" means nothing listens on port 22 (sshd stopped, or it uses another port).
"Connection timed out" usually means a firewall drops packets. Check `systemctl status sshd` and
`firewall-cmd --list-services`.

## Hardening
Prefer key authentication, set `PasswordAuthentication no` and `PermitRootLogin no` in
`/etc/ssh/sshd_config`, and consider fail2ban to block brute-force attempts.
