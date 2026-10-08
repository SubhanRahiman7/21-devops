# DevOps Task Tracker - end-to-end DevOps project

[![CI/CD + DevSecOps](https://github.com/SubhanRahiman7/21-devops/actions/workflows/ci-cd.yml/badge.svg)](https://github.com/SubhanRahiman7/21-devops/actions/workflows/ci-cd.yml)

**Author:** Subhan Rahiman (24BCS10095) - Session 21, final DevOps project.

## Table of contents

1. [Project overview](#1-project-overview)
2. [Architecture diagram](#2-architecture-diagram)
3. [Technologies used](#3-technologies-used)
4. [Repository layout](#4-repository-layout)
5. [Application setup](#5-application-setup)
6. [Docker setup](#6-docker-setup)
7. [Kubernetes deployment](#7-kubernetes-deployment)
8. [Helm deployment](#8-helm-deployment)
9. [Terraform infrastructure](#9-terraform-infrastructure)
10. [CI/CD pipeline](#10-cicd-pipeline)
11. [DevSecOps implementation](#11-devsecops-implementation)
12. [Monitoring](#12-monitoring)
13. [GitOps](#13-gitops)
14. [Troubleshooting](#14-troubleshooting)
15. [Screenshots](#15-screenshots)
16. [Lessons learned](#16-lessons-learned)

---

## 1. Project overview

A small but complete service, **DevOps Task Tracker** (Flask + SQLite), taken through the whole DevOps life cycle:

```
Application -> Git -> GitHub -> CI -> Build & Test -> Security Scanning -> Docker Image -> Registry
            -> Kubernetes -> Helm -> Monitoring -> GitOps
```

| Area | What is delivered |
|------|-------------------|
| Application | REST API + web page: `/`, `/health`, `/ready`, `/api/info`, `/api/tasks` (token protected), `/metrics`; 8 tests, 96 % coverage |
| Containers | Multi-stage, non-root image with health check; Docker Compose for local use |
| Kubernetes | Deployment, Service, ConfigMap, Secret, Ingress, HPA, PDB, probes, resource limits, persistent storage |
| Helm | One chart, dev/prod values, `helm test`, upgrade and rollback |
| Terraform | VPC, ECR, S3 + KMS, IAM, EC2 - formatted, validated, planned, applied and destroyed |
| CI/CD | GitHub Actions: 13 jobs, security gate, image published to GHCR, deployed to a kind cluster and smoke tested |
| DevSecOps | SAST (Bandit, CodeQL), SCA (pip-audit), secret scanning (Gitleaks), image + IaC scanning (Trivy), security gate, Dependabot |
| Monitoring | Prometheus, Grafana, Loki + Promtail, six alert rules, outage and load demos |
| GitOps | Argo CD with auto-sync, prune and self-heal; release and rollback done only through Git |
| Troubleshooting | Final challenge: seven injected faults diagnosed and fixed |

> **Honest notes**
> * Terraform was applied against the **Moto AWS emulator** (same code, `use_local_emulator = true`), because the AWS
>   account used for the course is blocked by an organisation policy for EC2/S3. The IDs in the screenshots (for example
>   account `123456789012`) are the emulator's. The code is unchanged for real AWS (`use_local_emulator = false`).
> * Terminal screenshots are rendered from the **real output** of the commands that were run in this project.
>   Browser screenshots (Grafana, Prometheus, Argo CD, GitHub) are real captures of the running tools.

## 2. Architecture diagram

![Architecture](docs/architecture.png)

* **Pipeline (top):** every push runs build/test and all scans; only if the *security gate* passes is the image published
  and deployed to a throw-away kind cluster.
* **Runtime (middle):** Ingress -> Service -> Deployment (2-5 pods, HPA) with ConfigMap/Secret and a PVC for SQLite.
* **Operations (right):** Helm packages the release, Argo CD keeps the cluster equal to Git, Prometheus/Grafana/Loki observe it,
  Terraform describes the cloud infrastructure.

## 3. Technologies used

| Layer | Tools |
|-------|-------|
| Application | Python 3.12, Flask 3.1, gunicorn, SQLite, prometheus-client |
| Quality | ruff, pytest, pytest-cov |
| Containers | Docker (multi-stage build), Docker Compose |
| Orchestration | Kubernetes (minikube), ingress-nginx, HPA, PDB |
| Packaging | Helm 3 |
| Infrastructure as Code | Terraform >= 1.6, AWS provider 6.x, Moto emulator |
| CI/CD | GitHub Actions, GitHub Container Registry (GHCR), kind |
| Security | Bandit, CodeQL, pip-audit, Gitleaks, Trivy (image + config), Dependabot |
| Observability | Prometheus, Grafana, Loki, Promtail |
| GitOps | Argo CD 3.1 |

## 4. Repository layout

```
application/      Flask app, tests, requirements
docker/           Dockerfile, docker-compose.yml
kubernetes/       plain manifests (+ kustomization)
helm/             task-tracker chart, values-dev / values-prod
terraform/        AWS infrastructure (VPC, ECR, S3+KMS, IAM, EC2)
.github/          CI/CD workflow and Dependabot config
security/         Bandit, Gitleaks and Trivy configuration
monitoring/       Prometheus, Grafana, Loki, Promtail, alert rules, dashboard
gitops/           Argo CD Application + per-environment values
troubleshooting/  Final challenge: broken.yaml, fixed.yaml, write-up
docs/             architecture diagram and screenshots
```

## 5. Application setup

```bash
cd application
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
ruff check .                       # lint
pytest                             # 8 tests, coverage gate 85 %
API_TOKEN=dev-token gunicorn --bind 127.0.0.1:8080 wsgi:app
curl http://127.0.0.1:8080/health
curl -H "X-API-Token: dev-token" -H "Content-Type: application/json" \
     -d '{"title":"write README"}' http://127.0.0.1:8080/api/tasks
```

Configuration is read from environment variables: `APP_ENV`, `APP_VERSION`, `LOG_LEVEL`, `DATA_DIR`, `PORT`, `API_TOKEN`
(the token is compared with `hmac.compare_digest`; write requests without it get `401`).

![unit tests](docs/screenshots/01-unit-tests.png)
![app in browser](docs/screenshots/03-app-in-browser.png)

## 6. Docker setup

[`docker/Dockerfile`](docker/Dockerfile): multi-stage build (dependencies are built in one stage, only the result is copied),
runs as **uid 10001**, has a `HEALTHCHECK`, stores data in the `/data` volume and starts gunicorn on port 8080.

```bash
docker build -f docker/Dockerfile -t devops-task-tracker:1.0.0 application
docker run -d -p 8080:8080 -e API_TOKEN=local-token -v task-data:/data devops-task-tracker:1.0.0
docker compose -f docker/docker-compose.yml up --build      # same thing with Compose
```

![docker build and run](docs/screenshots/02-docker-build-run.png)

## 7. Kubernetes deployment

All objects live in namespace `task-tracker` ([`kubernetes/`](kubernetes/)).

| Requirement | Implementation |
|-------------|----------------|
| Deployment | 2 replicas, rolling update (`maxUnavailable: 0`), non-root, read-only root filesystem, dropped capabilities |
| Service | ClusterIP `task-tracker:80` -> container port 8080 |
| ConfigMap | `APP_ENV`, `LOG_LEVEL` |
| Secret | `API_TOKEN`, created out-of-band with [`create-secret.sh`](kubernetes/create-secret.sh) (random value, never stored in Git; only `secret.example.yaml` is committed) |
| Ingress | nginx, host `tasks.local` |
| HPA | 2-5 pods at 60 % CPU |
| Probes | startup + readiness (`/ready`) + liveness (`/health`) |
| Storage | 100Mi PVC mounted at `/data` (SQLite survives pod restarts) |
| Extras | PodDisruptionBudget, resource requests/limits, Prometheus scrape annotations |

```bash
kubectl apply -f kubernetes/namespace.yaml
./kubernetes/create-secret.sh task-tracker
kubectl apply -k kubernetes/
kubectl -n task-tracker get all,pvc,ingress,hpa
```

![k8s resources](docs/screenshots/04-k8s-resources.png)
![pod details](docs/screenshots/05-k8s-pod-details.png)
![ingress](docs/screenshots/06-k8s-ingress-and-lb.png)
![persistence](docs/screenshots/07-k8s-persistence.png)
![app via ingress](docs/screenshots/08-k8s-app-via-ingress.png)

**Autoscaling.** Eight busybox pods called `/api/tasks` in a loop. CPU went from 6 % to 209 %, the HPA raised the replicas
from 2 to 4 and then 5 (its maximum); the load pods were deleted afterwards and the HPA scaled back in to 2.

![HPA](docs/screenshots/30-hpa-scale-out.png)

## 8. Helm deployment

The chart in [`helm/task-tracker`](helm/task-tracker) renders the same objects from values. `values-dev.yaml` and
`values-prod.yaml` differ in replicas, resources, host and autoscaling. A chart test (`helm test`) calls the service.

```bash
helm lint helm/task-tracker
helm upgrade --install tt helm/task-tracker -n task-tracker -f helm/task-tracker/values-dev.yaml \
     --set secret.existingSecret=task-tracker-secret
helm test tt -n task-tracker
helm upgrade tt helm/task-tracker -n task-tracker -f helm/task-tracker/values-dev.yaml --set image.tag=1.1.0
helm history tt -n task-tracker && helm rollback tt 1 -n task-tracker
```

![helm install 1](docs/screenshots/09-helm-install-1.png)
![helm install 2](docs/screenshots/09-helm-install-2.png)
![helm install 3](docs/screenshots/09-helm-install-3.png)
![helm upgrade and rollback](docs/screenshots/10-helm-upgrade-rollback.png)

## 9. Terraform infrastructure

[`terraform/`](terraform/) creates: a VPC with public/private subnets and a restrictive security group, an **ECR** repository
(immutable tags, scan on push, lifecycle rule), an **S3** artifact bucket (versioning, SSE-KMS with a customer key, public
access blocked), a **KMS** key, an **IAM** role/instance profile for EC2, and an **EC2** instance (IMDSv2, encrypted root volume,
no public SSH). 19 resources in total.

```bash
cd terraform
terraform fmt -check && terraform init && terraform validate
terraform plan  -var-file=terraform.tfvars          # real AWS (copy terraform.tfvars.example first)
terraform apply -var-file=terraform.tfvars
terraform destroy -var-file=terraform.tfvars

# same code against the Moto emulator (what was run for the screenshots)
docker run -d -p 5001:5000 -e MOTO_IAM_LOAD_MANAGED_POLICIES=true motoserver/moto
terraform apply -var-file=local-emulator.tfvars
```

The IaC scan found three real issues in the first version (public IP on the subnet, S3 without a customer key, an
undocumented open egress rule); they were fixed and the scan is now clean (screenshot 16).

![init and validate](docs/screenshots/11-terraform-init-validate.png)
![plan](docs/screenshots/12-terraform-plan.png)
![apply](docs/screenshots/13-terraform-apply.png)
![verify](docs/screenshots/14-terraform-verify.png)
![destroy](docs/screenshots/15-terraform-destroy.png)
![iac scan](docs/screenshots/16-iac-scan.png)

## 10. CI/CD pipeline

[`.github/workflows/ci-cd.yml`](.github/workflows/ci-cd.yml) - 13 jobs, runs on every push and pull request:

```
test | chart-lint | terraform-validate | iac-scan | sast-bandit | sast-codeql | sca | secret-scan     (in parallel)
                                   |
                              docker-build -> image-scan -> security-gate -> publish (GHCR) -> deploy (kind + Helm + smoke test)
```

| Job | Purpose |
|-----|---------|
| Build and test | ruff + pytest with a coverage gate of 85 % |
| Validate Helm chart and manifests | `helm lint` (default, dev, prod values), `helm template`, `kubectl kustomize` |
| Validate Terraform | `fmt -check`, `init -backend=false`, `validate` |
| Docker build / Image scan | build the image, Trivy fails the pipeline on HIGH/CRITICAL |
| Security gate | reads the result of every scan job and blocks publishing if any failed |
| Push image to GHCR | pushes the scanned image as `latest` and the commit SHA (only on `main`, never on pull requests) |
| Deploy with Helm (kind) | creates a cluster, installs the chart, runs `helm test` and a smoke test |

Latest run on `main` - all 13 jobs green: [run #25](https://github.com/SubhanRahiman7/21-devops/actions/runs/37792752929)

![GitHub Actions run](docs/screenshots/50-github-actions-run.png)

## 11. DevSecOps implementation

| Control | Tool | Where | Gate |
|---------|------|-------|------|
| SAST | Bandit (`security/bandit.yaml`) | `sast-bandit` | MEDIUM and above fail |
| SAST | CodeQL | `sast-codeql` | results in the Security tab |
| SCA | pip-audit | `sca` | any known vulnerable dependency fails |
| Secret scanning | Gitleaks (`security/gitleaks.toml`) | `secret-scan` | any finding fails |
| Image scanning | Trivy | `image-scan` | HIGH/CRITICAL fail |
| IaC scanning | Trivy config | `iac-scan` | HIGH/CRITICAL fail (Terraform, Kubernetes, Helm, Dockerfile) |
| Security gates | `security-gate` job | before publish/deploy | all of the above must be green |
| Dependency updates | Dependabot | `.github/dependabot.yml` | weekly PRs for pip, Docker and GitHub Actions |

Secure-by-default choices in the code: non-root user, read-only root filesystem, dropped capabilities, seccomp
`RuntimeDefault`, token compared in constant time, Secret never committed, IAM least privilege, encrypted storage.

**Accepted exception, documented on purpose:** the third-party monitoring stack in `monitoring/` (Prometheus, Grafana,
Loki, Promtail) is excluded from the IaC scan: those images need a writable filesystem and Prometheus needs node-proxy access
to read container metrics. Everything else in the repository is scanned and clean.

## 12. Monitoring

Namespace `monitoring`: **Prometheus** (scrapes the app pods via annotations and the kubelet cAdvisor), **Grafana**
(pre-provisioned dashboard and data sources), **Loki + Promtail** (logs), and alert rules in
[`monitoring/alert-rules.yml`](monitoring/alert-rules.yml):
`TaskTrackerDown`, `TaskTrackerPodNotReady`, `HighErrorRate`, `HighLatency`, `HighCPUUsage`, `HighMemoryUsage`.

```bash
kubectl apply -k monitoring/
kubectl -n monitoring port-forward svc/grafana 13000:3000
kubectl -n monitoring port-forward svc/prometheus 19090:9090
```

![monitoring stack](docs/screenshots/17-monitoring-stack.png)
![grafana healthy](docs/screenshots/18-grafana-healthy.png)
![prometheus targets](docs/screenshots/19-prometheus-targets.png)
![alerts ok](docs/screenshots/20-prometheus-alerts-ok.png)

**Outage demo.** The Deployment was scaled to zero: `TaskTrackerDown` fired, Grafana showed the drop, and after scaling
back up the alert resolved.

![outage](docs/screenshots/21-monitoring-outage.png)
![alerts firing](docs/screenshots/22-prometheus-alerts-firing.png)
![grafana outage](docs/screenshots/23-grafana-outage.png)
![recovery](docs/screenshots/24-monitoring-recovery.png)
![grafana recovered](docs/screenshots/25-grafana-recovered.png)

**CPU alert demo.** With the HPA active the load is spread over five pods and per-pod CPU stays below the alert threshold
(correct behaviour, so the alert stayed inactive). With the HPA removed and two pods under load, `HighCPUUsage` went to
*FIRING*. The HPA was applied again afterwards.

![cpu alert](docs/screenshots/26-cpu-alert.png)
![alerts cpu](docs/screenshots/27-prometheus-alerts-cpu.png)
![grafana under load](docs/screenshots/28-grafana-under-load.png)

## 13. GitOps

[`gitops/argocd/application.yaml`](gitops/argocd/application.yaml) tells Argo CD to render the Helm chart from this repository
with [`gitops/environments/dev/values.yaml`](gitops/environments/dev/values.yaml), with **automated sync, prune and self-heal**.
From then on the cluster is changed only by committing to Git.

```bash
./gitops/argocd/install.sh                     # local demo install (auth disabled - never on a shared cluster)
kubectl apply -f gitops/argocd/application.yaml
kubectl -n argocd port-forward svc/argocd-server 8085:80
```

| Step | What was done | Evidence |
|------|---------------|----------|
| Deploy | Application created, Argo CD installs the chart (2 replicas, tag 1.0.0) | [33](docs/screenshots/33-gitops-deploy-1.png), [34](docs/screenshots/34-argocd-synced-v1.png), [35](docs/screenshots/35-app-via-gitops-v1.png) |
| Release | `values.yaml` changed to tag 1.1.0 with 3 replicas and **committed**; Argo CD synced by itself | [36](docs/screenshots/36-gitops-release.png), [37](docs/screenshots/37-argocd-synced-v2.png), [38](docs/screenshots/38-app-via-gitops-v2.png) |
| Self-heal | `kubectl scale ... --replicas=6` (manual drift) was reverted to 3 automatically | [39](docs/screenshots/39-gitops-selfheal.png) |
| Rollback | `git revert` of the release commit; the cluster went back to 1.0.0 / 2 replicas | [40](docs/screenshots/40-gitops-rollback.png), [41](docs/screenshots/41-argocd-rolled-back.png) |

![gitops deploy](docs/screenshots/33-gitops-deploy-1.png)
![argocd synced](docs/screenshots/37-argocd-synced-v2.png)
![release](docs/screenshots/36-gitops-release.png)
![self heal](docs/screenshots/39-gitops-selfheal.png)
![rollback](docs/screenshots/40-gitops-rollback.png)

## 14. Troubleshooting

### Final Troubleshooting Challenge

Seven faults were injected on purpose ([`troubleshooting/broken.yaml`](troubleshooting/broken.yaml); the known-good version is
[`fixed.yaml`](troubleshooting/fixed.yaml)). Every fault was solved with the same loop:
**observe -> describe/events -> logs/resources -> root cause -> fix -> verify**. Full write-up:
[troubleshooting/README.md](troubleshooting/README.md).

| # | Symptom | Root cause | Fix |
|---|---------|-----------|-----|
| 1 | Pod `Pending` | PVC uses StorageClass `fast-ssd`, which does not exist | `storageClassName: standard` |
| 2 | `ImagePullBackOff` | image tag `1.0.9` was never published | use `1.0.0` |
| 3 | `CreateContainerConfigError` | Secret has key `API_TOKN`, Deployment asks for `API_TOKEN` | recreate the Secret with the right key |
| 4 | `CrashLoopBackOff`, `OOMKilled` (exit 137) | memory limit 16Mi | 64Mi request / 192Mi limit |
| 5 | `Running` but `0/1` Ready | readiness probe path `/readyz` returns 404 | path `/ready` |
| 6 | Service unreachable, endpoints `<none>` | selector `app=tt-app` vs pod label `app=tt` | selector `app: tt` |
| 7 | Ingress returns 503 | backend port 8080, but the Service exposes 80 | backend port 80 |

![fault 1](docs/screenshots/42-fault1-pvc-pending.png)
![fault 2](docs/screenshots/43-fault2-imagepull.png)
![fault 3](docs/screenshots/44-fault3-secret-key.png)
![fault 4](docs/screenshots/45-fault4-oomkilled.png)
![fault 5](docs/screenshots/46-fault5-readiness.png)
![fault 6](docs/screenshots/47-fault6-service-selector.png)
![fault 7](docs/screenshots/48-fault7-ingress-503.png)
![all fixed](docs/screenshots/49-challenge-all-fixed.png)

### Other problems met while building this project

| Problem | Cause | Fix |
|---------|-------|-----|
| `helm install` rejected by the ingress admission webhook | two Ingresses used the same host and path | dev values use `tasks-dev.local` |
| Trivy IaC scan failed (AWS-0104, AWS-0164, AWS-0132) | public IP on subnet, S3 without CMK, open egress | fixed in Terraform; egress exception documented in code |
| CI `Validate Terraform` failed on GitHub only | lock file had checksums for macOS only | `terraform providers lock` for Linux and macOS |
| CI IaC scan failed on the challenge manifests and the monitoring stack | missing `readOnlyRootFilesystem`; third-party stack | hardened the manifests; documented exclusion of `monitoring/` |
| Promtail Kubernetes discovery found no targets | no pods discovered in this cluster setup | static file tailing with labels taken from the log path |
| Moto rejected the AWS managed IAM policy attachments | managed policies not loaded | run Moto with `MOTO_IAM_LOAD_MANAGED_POLICIES=true` |
| Alert never fired during the load test | the HPA spread the load over five pods | demonstrated with the HPA removed, restored afterwards |

Generic checklist: `get` (state) -> `describe` (events) -> `logs [--previous]` -> compare selectors/ports/names -> fix the
smallest thing -> verify from the outside.

## 15. Screenshots

All screenshots are in [`docs/screenshots`](docs/screenshots) and embedded in the sections above:

| Topic | Files |
|-------|-------|
| Application / Docker | 01-03 |
| Kubernetes and HPA | 04-08, 30 |
| Helm | 09, 10 |
| Terraform and IaC scan | 11-16 |
| Monitoring and alerts | 17-28 |
| GitOps (Argo CD) | 33-41 |
| Troubleshooting challenge | 42-49 |
| CI/CD and repository | 50, 51 |

![Repository](docs/screenshots/51-github-repo.png)

## 16. Lessons learned

* **Gates beat good intentions.** The IaC scan found real problems (public IPs, unencrypted bucket, missing hardening)
  that are easy to miss when reading code.
* **Reproduce CI locally before pushing.** Both CI failures (Terraform lock file, scan scope) were understood in minutes
  once the exact CI command was run locally.
* **Faults hide each other.** A Pending pod cannot show an image error; fixing in order and verifying after every step
  is faster than guessing.
* **`describe` events and `logs --previous` answer most questions**; compare what *selects* with what is *selected*.
* **Git is the control plane with GitOps.** A manual `kubectl scale` was reverted within seconds, and a rollback was a
  plain `git revert`.
* **Never put secrets in Git.** The Secret is created out-of-band; Gitleaks guards the history.
* **Autoscaling hides symptoms.** The CPU alert only fired once the HPA was out of the way - alerts and autoscalers must
  be designed together.
* **Be honest about the environment.** Where a real cloud was not available (Terraform), the emulator is named
  explicitly instead of pretending.
* **Do not trust a destructive command through a symlink.** One `rm -rf` through a symlink deleted a working copy; it was
  rebuilt from Git, which is exactly what version control is for.
