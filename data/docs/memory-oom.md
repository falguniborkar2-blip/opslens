# Memory Pressure and the OOM Killer

## Reading memory usage
`free -h` shows total, used, free and available memory. The **available** column is what matters:
Linux uses spare RAM for the page cache, so low "free" memory is normal. `vmstat 1` shows paging
activity; sustained non-zero `si`/`so` columns mean the system is swapping heavily.

## Which process uses the most memory
`ps -eo pid,comm,%mem,rss --sort=-rss | head` lists processes by resident memory. `top` or `htop`
can sort interactively (press `M` in top).

## Detecting OOM kills
When the kernel runs out of memory it invokes the Out-Of-Memory killer, which terminates the process
with the highest `oom_score`. Confirm it with `journalctl -k | grep -i "out of memory"` or
`dmesg -T | grep -i oom`. A process killed this way exits with signal 9 (SIGKILL), shown as exit code
137 in containers.

## Protecting or limiting a service
In a systemd unit, `MemoryMax=2G` caps a service's memory with cgroups, and `OOMScoreAdjust=-500`
makes the kernel less likely to kill it. For containers in Kubernetes, set
`resources.limits.memory`; a container exceeding it is killed with reason `OOMKilled`.

## Adding swap
Swap gives breathing room but is not a fix for a memory leak. Create a swap file with
`fallocate -l 2G /swapfile && chmod 600 /swapfile && mkswap /swapfile && swapon /swapfile`
and add it to `/etc/fstab` to persist.
