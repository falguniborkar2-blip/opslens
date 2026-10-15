# Linux Network Troubleshooting

## Interfaces and routes
`ip -br addr` shows interfaces and their addresses in brief form. `ip route` shows the routing table;
the `default via` line is the gateway. NetworkManager users can inspect connections with
`nmcli connection show`.

## Is the service listening?
`ss -tulpn` lists listening TCP/UDP sockets with the owning process. If the service listens only on
`127.0.0.1` it is unreachable from other machines; change its bind address to `0.0.0.0` or the
interface address.

## Connectivity tests
`ping` checks ICMP reachability (often blocked). `curl -v http://host:port/` tests an HTTP service.
`nc -zv host port` checks whether a TCP port is open. `tracepath` or `mtr` show where packets are lost.

## DNS problems
If an IP address works but the hostname does not, the problem is name resolution. Query a name with
`dig example.com` or `getent hosts example.com` (which uses the same resolver path as applications).
On systemd-resolved systems, `resolvectl status` shows the DNS servers in use.

## Firewall
On RHEL and Fedora, firewalld manages the firewall. `firewall-cmd --list-all` shows the active zone's
rules. Open a port with `firewall-cmd --add-port=8080/tcp --permanent` and then
`firewall-cmd --reload`, or allow a known service with `--add-service=http`.
