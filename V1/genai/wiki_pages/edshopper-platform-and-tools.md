# EdShopper platform: environments, tools, network and databases
- Space: Platform
- Labels: edshopper, architecture, environments, clusters, urls, argocd, grafana, network, certificates, database, configuration, kubectl
- Owner: platform-team
- Last updated: 2026-11-10

## Overview of the EdShopper platform
EdShopper (https://www.edshopper.com) is an online shopping portal. Customers use the website www.edshopper.com, the customer portal account.edshopper.com and the mobile app. They all call five API services: checkout-api, orders-api, payments-api, inventory-api and notifications-api. Each service is a Kubernetes deployment with at least 3 replicas in production.

## How a code change gets to production
A developer merges a pull request in the repository of the service. GitHub Actions builds the image and pushes it to the container registry (ECR). The new image tag is written into the repository platform-manifests, and Argo CD syncs the cluster with Git (GitOps), first dev, then stage, then prod. Nobody deploys by hand. After the deployment, check the dashboard "Service overview" in Grafana.

Observability: Prometheus collects metrics, Grafana shows dashboards and logs (Loki), and Alertmanager sends alerts to Slack.

## Environments and clusters
| Environment | Kubernetes cluster | Website | Public API | Alerts channel |
|---|---|---|---|---|
| dev | edshopper-dev | https://dev.edshopper.com | https://api.dev.edshopper.com | #alerts-dev |
| stage | edshopper-stage | https://stage.edshopper.com | https://api.stage.edshopper.com | #alerts-stage |
| prod | edshopper-prod | https://www.edshopper.com | https://api.edshopper.com | #alerts-prod |
All clusters are Amazon EKS 1.32 in the AWS region us-east-1. Each environment has its own cluster, its own databases and its own copy of the tools below. Prod is the one customers use: check the environment in the address before you click anything.

## Argo CD (deployments, GitOps)
- prod: https://argocd.prod.edshopper.internal
- stage: https://argocd.stage.edshopper.internal
- dev: https://argocd.dev.edshopper.internal
Use it to see if an application is Synced and Healthy, to read the sync history, and to sync or roll back. Each application is named after the service and the environment, for example checkout-api-prod or orders-api-stage.

## Grafana (dashboards and logs)
- prod: https://grafana.prod.edshopper.internal
- stage: https://grafana.stage.edshopper.internal
- dev: https://grafana.dev.edshopper.internal
Start with the dashboard "Service overview". Other dashboards: "Container memory vs limit" and "Database overview". Logs (Loki) are on the Explore page: search by namespace and pod name.

## Prometheus and Alertmanager
- Prometheus (metrics), prod: https://prometheus.prod.edshopper.internal, stage: https://prometheus.stage.edshopper.internal, dev: https://prometheus.dev.edshopper.internal
- Alertmanager (active alerts and silences), prod: https://alertmanager.prod.edshopper.internal, stage: https://alertmanager.stage.edshopper.internal, dev: https://alertmanager.dev.edshopper.internal
A silence in prod needs the approval of the on-call lead.

## Shared tools (the same for all environments)
- Wiki: https://wiki.edshopper.internal
- Source code (GitHub): https://github.com/edshopper
- Manifests repository (watched by Argo CD): https://github.com/edshopper/platform-manifests
- Pipelines (GitHub Actions): the Actions tab of each repository
- Container registry (ECR): 482915307764.dkr.ecr.us-east-1.amazonaws.com, one repository per service, for example edshopper/checkout-api
- Paging tool (PagerDuty, on-call schedules): https://edshopper.pagerduty.com
- IT portal (access requests): https://itportal.edshopper.internal
All internal tools need the VPN and your company login (SSO).

## Access and kubectl (FAQ)
- Access to the clusters: raise a request in the IT portal with the title "Cluster access" and pick read-only or read-write. The team lead approves it. Production write access is only given to people on the on-call rota.
- You need the VPN for Grafana, Argo CD and the wiki.
- Connect kubectl to production: `aws eks update-kubeconfig --name edshopper-prod --region us-east-1 --alias edshopper-prod`. The other clusters are edshopper-stage and edshopper-dev.
- List your contexts with `kubectl config get-contexts` and switch with `kubectl config use-context edshopper-stage`. Always check the context with `kubectl config current-context` before you run a command: it is easy to be in production by mistake.
- Normal changes go through a pull request and Argo CD. The on-call lead approves risky production actions during an incident.

## Public addresses and certificates
| Hostname | Goes to | Certificate |
|---|---|---|
| www.edshopper.com | the online shop (ingress of edshopper-prod) | edshopper-com-tls, managed by cert-manager |
| account.edshopper.com | customer portal | account-edshopper-com-tls, managed by cert-manager |
| api.edshopper.com | public API: /checkout goes to checkout-api, /orders to orders-api, /inventory to inventory-api | edshopper-com-tls, managed by cert-manager |
Stage uses stage.edshopper.com and api.stage.edshopper.com. Dev uses dev.edshopper.com and api.dev.edshopper.com. The certificates are in the namespace ingress-nginx.

## Internal names, ports and firewall
Services call each other with the name pattern service, then namespace, then svc.cluster.local. For example checkout-api calls orders-api.orders.svc.cluster.local and payments-api.payments.svc.cluster.local.
| Port | Used by |
|---|---|
| 443 | HTTPS at the load balancer edshopper-prod-alb |
| 8080 | application containers |
| 5432 | PostgreSQL |
| 6432 | PgBouncer |
| 9090 | Prometheus |
Firewall: only the load balancer may reach the ingress. Only the application namespaces and the bastion host may reach the databases. Changes go through a pull request in https://github.com/edshopper/network-config.

## Kubernetes nodes and servers
Node groups in edshopper-prod:
| Node group | Instance type | Min nodes | Max nodes | Used for |
|---|---|---|---|---|
| ng-general | m5.xlarge (4 vCPU, 16 GB) | 3 | 9 | application pods |
| ng-system | t3.large (2 vCPU, 8 GB) | 2 | 3 | CoreDNS, ingress, monitoring |
The Cluster Autoscaler adds a node when pods stay Pending because no node has enough CPU or memory. It removes nodes that stay empty for 10 minutes.
Servers outside Kubernetes: bastion-prod-01 (bastion-prod-01.edshopper.internal) is the jump host for SSH, `ssh $USER@bastion-prod-01.edshopper.internal`, with the VPN and an approved access request. ci-runners are four self-hosted GitHub Actions runners (runner-01 to runner-04). backup-server holds the backup volume mounted at /backup (500 GB). Do not log in to a Kubernetes node to fix a pod problem: use kubectl.

## Service configuration
The manifests are in https://github.com/edshopper/platform-manifests, one folder per service (checkout-api, orders-api, payments-api, inventory-api, notifications-api). Settings that are not secret live in ConfigMaps. Passwords and keys live in AWS Secrets Manager and are synced into the cluster by External Secrets. Never put a password in Git.
| Variable | Meaning | Default |
|---|---|---|
| DATABASE_URL | address of the database | from the secret |
| LOG_LEVEL | amount of logging | info |
| REQUEST_TIMEOUT_SECONDS | time limit for outgoing requests | 10 |
| FEATURE_FLAGS_URL | feature flag service | https://flags.prod.edshopper.internal in prod |

## Default resources, probes and autoscaling
| Tier | CPU request | CPU limit | Memory request | Memory limit |
|---|---|---|---|---|
| Tier 1 (checkout-api, payments-api) | 250m | 500m | 256Mi | 512Mi |
| Tier 2 (orders-api, inventory-api, notifications-api) | 100m | 250m | 128Mi | 256Mi |
- Liveness probe: path /healthz, initialDelaySeconds 30, periodSeconds 10. Readiness probe: path /ready, initialDelaySeconds 10.
- Horizontal Pod Autoscaler: minimum 3 and maximum 10 replicas, target CPU 70 percent.
To change a setting, open a pull request in platform-manifests. After the merge, Argo CD syncs the change. An emergency change on the live cluster needs approval from the on-call lead and a pull request afterwards.

## Databases: endpoints per environment
Each environment has its own databases (PostgreSQL 15). Dev and stage run one instance without replicas. Applications connect through PgBouncer on port 6432, never directly to port 5432.
| Database | Environment | Primary | Replicas |
|---|---|---|---|
| orders-db | prod | orders-db-primary.edshopper.internal | orders-db-replica-1.edshopper.internal, orders-db-replica-2.edshopper.internal |
| orders-db | stage | orders-db-stage.edshopper.internal | none |
| orders-db | dev | orders-db-dev.edshopper.internal | none |
| payments-db | prod | payments-db-primary.edshopper.internal | payments-db-replica-1.edshopper.internal |
| payments-db | stage | payments-db-stage.edshopper.internal | none |
| payments-db | dev | payments-db-dev.edshopper.internal | none |
Credentials are in the secrets orders-db-credentials and payments-db-credentials of each cluster.

## Database settings and access
- orders-db: database name orders. Used by checkout-api, orders-api and inventory-api (users checkout_app, orders_app, inventory_app). max_connections is 200 and the applications use at most 20 connections per pod. Storage 500 GB, the alert fires at 85 percent.
- payments-db: database name payments. Used by payments-api only.
- Backup: every night at 01:00 UTC to the S3 bucket edshopper-prod-db-backups, 30 days kept. RPO 24 hours, RTO 4 hours. Maintenance window: Sunday 02:00 to 04:00 UTC.
- Access: engineers get read-only access (user dba_readonly) through the bastion host. Write access to production needs approval from the DBA lead.
