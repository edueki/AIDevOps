# EdShopper runbooks: troubleshooting steps
- Space: Runbooks
- Labels: runbook, troubleshooting, kubernetes, crashloopbackoff, oomkilled, imagepullbackoff, rollback, 5xx, database, backup, tls, dns, terraform
- Owner: sre-team
- Last updated: 2026-11-10

## How to read these runbooks
The commands use the service checkout-api in the namespace checkout as the example. For another service, use its namespace and deployment name from the page "EdShopper applications, owners and on-call contacts". Check that kubectl points to the right cluster first: `kubectl config current-context` (edshopper-prod, edshopper-stage or edshopper-dev). Alerts arrive in #alerts-prod, #alerts-stage and #alerts-dev.

## Pod in CrashLoopBackOff: symptoms and causes
A pod shows the status CrashLoopBackOff and its restart count keeps growing. The alert KubePodCrashLooping appears in #alerts-prod. Users may see errors because fewer pods are serving traffic.
Likely causes:
- The application exits at startup because an environment variable, ConfigMap or Secret is missing or wrong.
- The liveness probe fails, so Kubernetes keeps killing a healthy but slow container.
- The container is killed for using too much memory (exit code 137). See "Container OOMKilled".
- A dependency such as the database is not reachable when the application starts.
- A bad release: the new version crashes while the old one worked.

## Pod in CrashLoopBackOff: diagnosis and fix
1. List the pods and their restarts: `kubectl get pods -n checkout`
2. Look at the reason and the exit code: `kubectl describe pod checkout-api-6d8f7c9b5-x2k4p -n checkout` and read "Last State".
3. Read the log of the container that crashed: `kubectl logs checkout-api-6d8f7c9b5-x2k4p -n checkout --previous`
4. Exit code 137 means OOMKilled. Exit code 1 means the application raised an error: read the last lines of the log.
Fix:
- Missing or wrong configuration: correct the ConfigMap or Secret in platform-manifests, let Argo CD sync it, then `kubectl rollout restart deployment/checkout-api -n checkout`.
- Failing liveness probe: increase initialDelaySeconds in the manifest.
- Bad release: roll back (see "Deployment rollback").
Escalation: if checkout-api or payments-api is affected for more than 10 minutes, page the service owner and declare SEV2.

## Container OOMKilled: symptoms and causes
The pod restarts and `kubectl describe pod` shows Reason: OOMKilled and Exit Code: 137. Memory usage in Grafana touches the container limit just before each restart.
Likely causes:
- The memory limit is lower than what the application needs, often after a new release.
- A memory leak: usage grows slowly until the limit is reached.
- A traffic spike or a very large request.
- A Java application whose heap (-Xmx) is as large as the container limit, so there is no room for anything else.

## Container OOMKilled: diagnosis and fix
1. Confirm the reason: `kubectl describe pod checkout-api-6d8f7c9b5-x2k4p -n checkout` and look for OOMKilled.
2. Compare usage and limit: `kubectl top pod -n checkout` and the Grafana dashboard "Container memory vs limit" (https://grafana.prod.edshopper.internal).
3. Check whether usage grows over time (leak) or jumps at a certain moment (release or traffic).
Fix:
- Short term: raise the memory limit in platform-manifests (for example from 256Mi to 512Mi) and let Argo CD deploy it. Do not edit the live deployment, except in a SEV1 with approval from the on-call lead.
- Java: set -Xmx to about 75 percent of the container limit.
- Long term: find the leak with a profiler. Set the request to the normal usage and the limit to 1.5 to 2 times that. Add an alert when memory is above 80 percent of the limit.
If memory keeps growing after the limit was raised, ask the service owner to investigate a leak.

## ImagePullBackOff: symptoms and causes
New pods stay in ImagePullBackOff or ErrImagePull and never start. A deployment is stuck and the old pods keep running, or no pods run at all on a new service.
Likely causes:
- The image tag in the manifest does not exist in the registry (typo, or the build did not finish).
- The pull secret is missing or expired. Credentials for the container registry (ECR, 482915307764.dkr.ecr.us-east-1.amazonaws.com) expire after 12 hours.
- The registry is unreachable from the node.

## ImagePullBackOff: diagnosis and fix
1. `kubectl describe pod checkout-api-6d8f7c9b5-x2k4p -n checkout` and read the Events at the bottom.
2. "manifest unknown" means the tag does not exist. "unauthorized" means a credential problem.
3. Check that the tag exists: `aws ecr describe-images --repository-name edshopper/checkout-api --image-ids imageTag=v2.4.1 --region us-east-1`
Fix:
- Wrong tag: correct the tag in platform-manifests, run the pipeline again and let Argo CD deploy.
- Expired credentials: recreate the imagePullSecret and restart the deployment.
- Add a pipeline step that checks that the tag exists before it deploys.
If the registry itself is down, tell the platform team in #platform-help.

## Deployment rollback
Roll back first, investigate second, when the error rate or latency got worse within 30 minutes after a deployment and the cause is not obvious. Rolling back production in a SEV1 or SEV2 needs approval from the on-call lead: announce it in the incident channel before you start.
1. Find the last good version in Argo CD: open the application (for example checkout-api-prod) in https://argocd.prod.edshopper.internal, then "History and rollback".
2. Roll back in Argo CD: `argocd app rollback checkout-api-prod 42` (42 is the history ID of the last good version, shown by `argocd app history checkout-api-prod`).
3. Without Argo CD, use Kubernetes: `kubectl rollout undo deployment/checkout-api -n checkout`
4. Watch the result: `kubectl rollout status deployment/checkout-api -n checkout`
5. Check the dashboard "Service overview": the error rate should fall within 5 minutes.

## Deployment rollback: make it permanent
Argo CD syncs the cluster with Git, so a manual rollback is undone at the next sync. Revert the bad commit in Git so Git and the cluster agree. After the rollback, post an update in the incident channel and open a ticket to find the cause of the bad release.

## High 5xx error rate
The alert HighErrorRate fires when more than 5 percent of requests return a 5xx status for 5 minutes. Users report errors on the website or the mobile app.
First checks (about 5 minutes):
1. Was there a deployment in the last 30 minutes? Check the history in Argo CD. If yes, roll back first (see "Deployment rollback").
2. Are all pods ready? `kubectl get pods -n checkout`
3. Does the log show a dependency error? `kubectl logs deploy/checkout-api -n checkout --tail=100`
4. Are the database connections exhausted? See "Database connection pool exhausted".
5. Does the load balancer report unhealthy targets? Check the target group health of the load balancer edshopper-prod-alb in the AWS console.

## High 5xx error rate: decide and escalate
- Deployment in the last 30 minutes: roll back.
- Database errors in the log: follow the database runbooks and page dba-oncall.
- Only one pod fails: delete that pod so it is recreated, and investigate its node.
- Traffic spike: scale the deployment with `kubectl scale deployment/checkout-api --replicas=6 -n checkout`.
Escalation: declare SEV1 when checkout-api or payments-api is down, or SEV2 when it is degraded for more than 10 minutes.

## Database connection pool exhausted: symptoms and causes
Applications return 500 errors. The log of checkout-api, orders-api or inventory-api shows "too many connections" or "remaining connection slots are reserved". New connections to PostgreSQL (orders-db) are refused.
Likely causes:
- Every request opens its own connection and never closes it.
- Too many application pods, each with a large pool: pool size times pods is higher than max_connections (200 on orders-db).
- A burst of idle connections that were never released.

## Database connection pool exhausted: diagnosis and fix
Connect from the bastion host first: `psql -h orders-db-primary.edshopper.internal -p 5432 -U dba_readonly -d orders`
1. Check the limit: `SHOW max_connections;`
2. Count connections by state: `SELECT state, count(*) FROM pg_stat_activity GROUP BY state;`
3. Find the biggest users: `SELECT usename, application_name, count(*) FROM pg_stat_activity GROUP BY 1, 2 ORDER BY 3 DESC;`
Fix:
- Short term (needs DBA approval in production): end connections idle for more than 10 minutes with `SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE state = 'idle' AND state_change < now() - interval '10 minutes';`
- Long term: use PgBouncer (port 6432) or the application pool. Keep the pool at 20 connections per pod at most, so pool size times pods stays below max_connections.
Escalation: page dba-oncall if the connections are still at the limit after 10 minutes.

## Database replication lag
The alert ReplicaLagHigh fires when a replica is more than 30 seconds behind the primary. Reports and dashboards that read from the replica show old data.
Likely causes: the primary is overloaded with writes; a long query on the replica blocks replay; network problems; the replica has too little CPU or a slow disk.
1. On the primary (orders-db-primary.edshopper.internal): `SELECT client_addr, state, replay_lag FROM pg_stat_replication;`
2. On the replica (orders-db-replica-1.edshopper.internal): `SELECT now() - pg_last_xact_replay_timestamp();`
3. List long queries on the replica: `SELECT pid, now() - query_start AS runtime, query FROM pg_stat_activity WHERE state = 'active' ORDER BY runtime DESC;`

## Database replication lag: fix
- End the long-running queries on the replica (ask dba-oncall first in production).
- Move the heavy reports to run at night.
- Temporarily send reads to the primary if stale data is a risk.
- Scale up the replica if CPU or disk is the limit.
Never start a failover on your own. A failover needs approval from the DBA lead (Tomasz Nowak).

## Nightly backup failure and restore
The CronJob db-backup (namespace db) runs every night at 01:00 UTC and writes a dump to the backup volume. A second job copies it to the S3 bucket edshopper-prod-db-backups. We keep 30 days. The targets are RPO 24 hours and RTO 4 hours.
Symptoms: the alert BackupJobFailed fires, or the bucket has no new file this morning. Likely causes: the backup volume is full; the credentials for the bucket expired; the database was not reachable or the job ran out of time.
1. Read the job log: `kubectl logs job/db-backup-29412060 -n db` (find the job name with `kubectl get jobs -n db`).
2. Check the disk space: `df -h /backup`
3. Check the newest file in the bucket: `aws s3 ls s3://edshopper-prod-db-backups/orders-db/ | tail -3`

## Nightly backup failure and restore: fix and restore
Fix:
1. Free space by deleting backups older than 30 days.
2. Run the backup again: `kubectl create job --from=cronjob/db-backup db-backup-manual -n db`
3. Check that the new file appears in the bucket and has a normal size.
Restore:
1. Pick the backup file you need.
2. Restore it into a NEW database instance, never over production.
3. Check the row counts of the main tables.
4. Switching the application to the restored database needs approval from the DBA lead. Test a restore every month.

## TLS certificate expiring or expired
Browsers show "Your connection is not private". The alert CertExpiringSoon fires 14 days before a certificate expires. API clients fail with certificate errors. The public certificates are edshopper-com-tls (www.edshopper.com and api.edshopper.com) and account-edshopper-com-tls (account.edshopper.com), in the namespace ingress-nginx.
1. Check the real expiry date: `echo | openssl s_client -connect www.edshopper.com:443 -servername www.edshopper.com 2>/dev/null | openssl x509 -noout -dates`
2. List the certificates in the cluster: `kubectl get certificate -A`
3. Look at the status and events: `kubectl describe certificate edshopper-com-tls -n ingress-nginx`
4. If it is not Ready, check `kubectl get certificaterequest -n ingress-nginx` for the error.

## TLS certificate expiring or expired: fix
- Certificates managed by cert-manager renew themselves 30 days before expiry. If renewal failed, fix the reason (usually the DNS or HTTP validation) and force a renewal with `cmctl renew edshopper-com-tls -n ingress-nginx`.
- Certificates NOT managed by cert-manager must be renewed by hand: order a new certificate, update the secret, and restart the pods or the ingress.
- Prevention: move every certificate to cert-manager and keep the alert for 14 days before expiry.
- Escalation: if a production certificate has already expired, declare SEV2 and page platform-oncall.

## DNS failures inside the cluster (CoreDNS)
Services cannot reach each other by name. Logs show "no such host" or "Temporary failure in name resolution". Calls by IP address still work. Likely causes: the CoreDNS pods are down, restarting or out of memory; too few CoreDNS replicas; the upstream DNS server is not reachable.
1. Check CoreDNS: `kubectl get pods -n kube-system -l k8s-app=kube-dns`
2. Read the log: `kubectl logs -n kube-system -l k8s-app=kube-dns --tail=50`
3. Test from inside the cluster: `kubectl run dns-test --rm -it --image=busybox:1.36 --restart=Never -- nslookup orders-api.orders.svc.cluster.local`

## DNS failures inside the cluster: fix
- Restart CoreDNS: `kubectl rollout restart deployment/coredns -n kube-system`
- If pods are killed for memory, raise the memory limit.
- Scale to three replicas: `kubectl scale deployment/coredns --replicas=3 -n kube-system`
- Watch the DNS error rate in Grafana for 15 minutes.
If name resolution to outside hosts fails, the upstream resolver is the problem: contact the network team.

## Terraform drift
The Terraform code is in https://github.com/edshopper/infra-terraform. The state is in the S3 bucket edshopper-terraform-state and the lock in the DynamoDB table edshopper-terraform-locks. Drift means the real cloud setup no longer matches the code, usually because someone changed a resource by hand in the AWS console.
1. Run `terraform plan` and read which resources it wants to change.
2. Find who changed them in the AWS CloudTrail audit log.
3. Decide: if the manual change is right, copy it into the code. If it is wrong, let Terraform undo it.
4. Never run apply blindly: a plan that wants to destroy a resource needs a review.
5. Prevent it: restrict console changes in production.

## Terraform state lock
The error "Error acquiring the state lock" means Terraform locks the state while a plan or apply runs, so two runs cannot collide.
1. Read the Lock Info in the error: who holds it and since when.
2. Check in the GitHub Actions pipeline whether that run is still going. If it is, wait.
3. If the run crashed and the lock is stale, remove it with `terraform force-unlock 8f3a2c1e-5b7d-4e19-a6c4-90d1b2e7f3a8` (the ID is in the Lock Info). Do this only after you have confirmed that no apply is running, and ask the platform lead (Aisha Khan) for approval in production.
