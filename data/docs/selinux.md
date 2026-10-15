# SELinux Troubleshooting on RHEL and Fedora

## Check the current mode
`getenforce` prints Enforcing, Permissive or Disabled. `sestatus` gives more detail. In Permissive
mode denials are logged but not blocked, which is useful for diagnosis. Switch temporarily with
`setenforce 0` (permissive) and `setenforce 1` (enforcing). Do not disable SELinux permanently to
"fix" a problem.

## Find denials
SELinux denials are recorded as AVC messages in the audit log. Search recent ones with
`ausearch -m AVC -ts recent`. `sealert -a /var/log/audit/audit.log` (from setroubleshoot) explains
denials in plain language and suggests fixes.

## Wrong file context
The most common cause of denials is a file with the wrong label, for example web content copied
into `/var/www/html` from a home directory. Show labels with `ls -Z` and fix them with
`restorecon -Rv /var/www/html`. To label a custom directory permanently use
`semanage fcontext -a -t httpd_sys_content_t "/srv/web(/.*)?"` followed by `restorecon -Rv /srv/web`.

## Booleans
Booleans switch policy features on or off. List them with `getsebool -a`. For example, allowing
Apache to connect to a remote database requires `setsebool -P httpd_can_network_connect_db on`
(`-P` makes it persistent).

## Non-standard ports
If a service must listen on a custom port, add it to the right port type:
`semanage port -a -t http_port_t -p tcp 8081`.
