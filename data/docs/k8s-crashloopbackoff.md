# Kubernetes: Pod in CrashLoopBackOff

## What it means
`CrashLoopBackOff` means a container starts, exits, and the kubelet keeps restarting it with an
exponential back-off delay (up to five minutes). The status is a symptom; the cause is whatever makes
the process exit.

## Investigate
1. `kubectl get pods` shows the restart count.
2. `kubectl describe pod <pod>` shows the last state, exit code and events.
3. `kubectl logs <pod> --previous` prints logs from the crashed instance, which is usually where the
   real error is. Add `-c <container>` for multi-container pods.

## Common causes by exit code
* **Exit code 1** - application error: bad configuration, missing environment variable, failed
  connection to a database at startup.
* **Exit code 137 / OOMKilled** - the container exceeded its memory limit; raise
  `resources.limits.memory` or fix the leak.
* **Exit code 127** - the command in `command`/`args` does not exist in the image.
* **Liveness probe failures** - if the probe is too aggressive the kubelet kills a healthy but slow
  container. Increase `initialDelaySeconds` or use a `startupProbe`.

## Debugging a container that dies too fast
Override the command temporarily (`command: ["sleep", "3600"]`) and `kubectl exec -it <pod> -- sh`
into it, or use `kubectl debug -it <pod> --image=busybox --target=<container>` to attach an
ephemeral debug container.
