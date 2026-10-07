#!/usr/bin/env bash
# Creates the Secret with a random token so that no credential is ever stored in Git.
set -euo pipefail
NS="${1:-task-tracker}"
TOKEN="${API_TOKEN:-$(openssl rand -hex 16)}"
kubectl -n "$NS" create secret generic task-tracker-secret \
  --from-literal=API_TOKEN="$TOKEN" --dry-run=client -o yaml | kubectl apply -f -
echo "Secret task-tracker-secret created/updated in namespace $NS"
