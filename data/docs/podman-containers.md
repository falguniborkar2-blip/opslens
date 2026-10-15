# Running and Debugging Containers with Podman

## Basics
Podman is a daemonless container engine compatible with the Docker CLI. `podman ps -a` lists all
containers including stopped ones, `podman logs -f <name>` follows a container's output and
`podman inspect <name>` shows its full configuration, including the exit code under `State`.

## Rootless containers
Podman can run containers as a normal user without root. Rootless containers cannot bind to ports
below 1024 by default; publish a higher port (`-p 8080:80`) or lower
`net.ipv4.ip_unprivileged_port_start`. User namespaces map container UIDs to the user's subordinate
UIDs defined in `/etc/subuid` and `/etc/subgid`.

## Volume permission denied
On SELinux systems a bind-mounted host directory is not readable inside the container until it is
relabelled. Append `:Z` (private) or `:z` (shared) to the volume: `-v ./data:/data:Z`. For rootless
UID mismatches, `--userns=keep-id` maps your user into the container.

## Container exits immediately
Check the exit code with `podman ps -a`. Exit code 125 is a Podman error, 126 means the command
could not be invoked, 127 means command not found and 137 means the container was killed
(often out of memory). Run `podman run -it --entrypoint sh <image>` to explore the image.

## Running containers as systemd services
Quadlet lets you describe a container in a `.container` file under `~/.config/containers/systemd/`
and manage it with `systemctl --user`. This replaces the older `podman generate systemd`.

## Pods and Kubernetes YAML
`podman pod create` groups containers that share a network namespace. `podman kube play pod.yaml`
runs Kubernetes YAML locally and `podman kube generate` exports a running pod to YAML.
