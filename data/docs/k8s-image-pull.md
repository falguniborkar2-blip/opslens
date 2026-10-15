# Kubernetes: ImagePullBackOff and ErrImagePull

## Symptoms
The pod stays in `ErrImagePull` and then `ImagePullBackOff`. `kubectl describe pod <pod>` shows an
event such as "Failed to pull image ... not found" or "unauthorized: authentication required".

## Causes and fixes
* **Typo in the image name or tag** - verify the exact reference; `latest` may not exist if the
  registry only has versioned tags.
* **Private registry** - create a pull secret with
  `kubectl create secret docker-registry regcred --docker-server=<registry> --docker-username=<u> --docker-password=<p>`
  and reference it in the pod spec under `imagePullSecrets`, or attach it to the service account.
* **Rate limiting** - public registries limit anonymous pulls; authenticate or use a mirror.
* **Network or DNS on the node** - the node itself must reach the registry. Test from the node with
  `podman pull` or `crictl pull`.
* **Architecture mismatch** - an amd64-only image will not run on arm64 nodes ("exec format error").

## imagePullPolicy
`Always` pulls on every start, `IfNotPresent` uses the cached image when present. Pods using the
`latest` tag default to `Always`.
