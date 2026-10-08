#!/usr/bin/env bash
# Installs Argo CD (v3.1.0) into the current cluster for a local demo.
# The UI login is disabled (server.disable.auth) so the demo is easy to screenshot – NEVER do this on a shared cluster.
set -euo pipefail
kubectl create namespace argocd --dry-run=client -o yaml | kubectl apply -f -
kubectl apply -n argocd --server-side --force-conflicts \
  -f https://raw.githubusercontent.com/argoproj/argo-cd/v3.1.0/manifests/install.yaml
kubectl -n argocd patch configmap argocd-cmd-params-cm --type merge \
  -p '{"data":{"server.insecure":"true","server.disable.auth":"true"}}'
kubectl -n argocd rollout restart deploy/argocd-server
kubectl -n argocd rollout status deploy/argocd-server --timeout=180s
echo "Argo CD is ready. UI:  kubectl -n argocd port-forward svc/argocd-server 8085:80   ->  http://localhost:8085"
