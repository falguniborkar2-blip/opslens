# Kubernetes: Pods Stuck in Pending

## What Pending means
A Pending pod has been accepted by the API server but has not been scheduled to a node, or its
volumes are not ready. The scheduler explains why in the pod's events: run
`kubectl describe pod <pod>` and read the `FailedScheduling` message.

## Insufficient resources
"0/3 nodes are available: 3 Insufficient cpu" means no node has enough unreserved CPU or memory for
the pod's **requests** (not its actual usage). Lower the requests, add nodes, or check node capacity
with `kubectl describe node` and `kubectl top nodes`.

## Taints, tolerations and selectors
"node(s) had untolerated taint" means nodes are tainted (for example control-plane nodes) and the pod
has no matching toleration. A `nodeSelector` or node affinity that matches no node also keeps the pod
Pending. Check labels with `kubectl get nodes --show-labels`.

## Unbound PersistentVolumeClaims
"pod has unbound immediate PersistentVolumeClaims" means the PVC is not bound. `kubectl get pvc`
shows the claim status; make sure a StorageClass exists (`kubectl get storageclass`) and can
provision volumes, or that a matching PersistentVolume is available.

## Quotas
A ResourceQuota in the namespace can reject pods; `kubectl describe quota -n <ns>` shows usage.
