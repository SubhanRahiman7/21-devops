# Final Troubleshooting Challenge

Seven faults were injected **on purpose** into the Task Tracker stack ([`broken.yaml`](broken.yaml)).
[`fixed.yaml`](fixed.yaml) is the known-good version; `diff fixed.yaml broken.yaml` shows exactly what was broken.
Each fault hides the next one (a Pending pod cannot show an image error), so they were solved one at a time,
always in the same loop: **observe → describe/events → logs/resources → root cause → fix → verify**.

```bash
kubectl apply -f broken.yaml          # namespace "challenge"
# ...diagnose and fix each fault as described below...
kubectl diff -f fixed.yaml            # should show no meaningful drift at the end
kubectl delete ns challenge           # clean up
```

| # | Symptom | Where it was visible | Root cause | Fix | Evidence |
|---|---------|----------------------|------------|-----|----------|
| 1 | Pod `Pending` | `describe pod` → `FailedScheduling: unbound PersistentVolumeClaims`; `describe pvc` → `storageclass "fast-ssd" not found` | PVC asks for a StorageClass that does not exist in the cluster | `storageClassName: standard` (field is immutable → delete and recreate the PVC) | [42](../docs/screenshots/42-fault1-pvc-pending.png) |
| 2 | `ErrImagePull` / `ImagePullBackOff` | `describe pod` events: `manifest unknown` / failed to pull `:1.0.9` | Image tag `1.0.9` was never published | `kubectl set image ... :1.0.0` | [43](../docs/screenshots/43-fault2-imagepull.png) |
| 3 | `CreateContainerConfigError` | events: `couldn't find key API_TOKEN in Secret challenge/tt-secret` | Secret was created with the key `API_TOKN` (typo) | recreate the Secret with `API_TOKEN` | [44](../docs/screenshots/44-fault3-secret-key.png) |
| 4 | `CrashLoopBackOff` | `describe pod` → `Last State: Terminated, Reason: OOMKilled, Exit Code 137` | memory limit 16Mi is far below what gunicorn + Flask needs | request/limit → 64Mi / 192Mi | [45](../docs/screenshots/45-fault4-oomkilled.png) |
| 5 | `Running` but `0/1` Ready | events: `Readiness probe failed: HTTP probe failed with statuscode: 404`; app log shows `GET /readyz 404` | probe path `/readyz` does not exist (app serves `/ready`) | patch readiness path to `/ready` | [46](../docs/screenshots/46-fault5-readiness.png) |
| 6 | Calls to the Service time out | `get endpoints tt` → `<none>`; selector `app=tt-app` vs pod label `app=tt` | Service selector does not match any pod | selector → `app: tt` | [47](../docs/screenshots/47-fault6-service-selector.png) |
| 7 | Ingress returns `503` | ingress-nginx `describe ingress` → backend `tt:8080 ()` (no endpoints); Service port is 80 | Ingress points to a port the Service does not expose | backend port → `80` | [48](../docs/screenshots/48-fault7-ingress-503.png) |

Final state, all faults fixed and requests succeeding through the Ingress: [49](../docs/screenshots/49-challenge-all-fixed.png).

## A real incident from this project (not injected)

While building the GitOps step, `helm install` for the dev environment was rejected by the nginx admission webhook:
two Ingress objects used the same host + path (`tasks.local` `/`). Root cause: the dev values re-used the
production host. Fix: `ingress.host: tasks-dev.local` in `helm/task-tracker/values-dev.yaml`.

## Debugging checklist used

1. `kubectl get pods,pvc,svc,endpoints,ingress` – what state is each object in?
2. `kubectl describe <object>` – read the **Events** at the bottom first.
3. `kubectl logs [--previous]` – application view; `--previous` for crash loops.
4. Compare what *selects* with what is *selected* (labels, ports, names, keys).
5. Fix the smallest thing, then verify from the outside (Service, then Ingress), not just `Running`.
