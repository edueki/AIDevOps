# EdShopper on-call handbook and past incidents
- Space: OnCall
- Labels: oncall, severity, escalation, process, postmortem, incidents
- Owner: sre-team
- Last updated: 2026-11-10

## Severity levels
- SEV1: customers cannot use edshopper.com (checkout-api or payments-api down), or data is lost. Respond within 5 minutes.
- SEV2: a major feature is degraded or a large group of users is affected. Respond within 15 minutes.
- SEV3: a minor problem with a workaround. Handle it during working hours.

## First 10 minutes of an incident
1. Acknowledge the page in the paging tool (https://edshopper.pagerduty.com).
2. Open an incident channel named #inc-YYYYMMDD-short-name for SEV1 and SEV2, for example #inc-20261105-checkout-5xx.
3. Check the Grafana dashboard "Service overview" (https://grafana.prod.edshopper.internal) and the recent deployments in Argo CD (https://argocd.prod.edshopper.internal).
4. Declare the severity and say what you know and do not know.

## Roles and escalation path
The incident commander (rota incident-commander, led by Chen Wei) coordinates and decides. The responder fixes. The scribe writes the timeline. One person can hold two roles in a SEV2, but never the commander and the main responder in a SEV1.
Escalation path: on-call engineer, then the team lead after 15 minutes without progress, then the incident commander. Page dba-oncall for database problems and platform-oncall for cluster or network problems.

## Communication and approvals
In a SEV1 post an update in the incident channel every 30 minutes, and in a SEV2 every hour, even if the update is "no change".
Rollbacks, restarts of production databases, failovers and deleting data need approval from the on-call lead. Write the approval in the incident channel.

## After the incident
Write a postmortem within 5 working days. It must contain the Issue, the Root cause, the Resolution and the follow-up actions. The postmortems are listed below.

## Postmortem PM-2026-03: Checkout pods restarting after the v2.4 release
Issue: after the v2.4.0 release of checkout-api the pods in the namespace checkout restarted every few minutes. Customers saw 502 errors for 40 minutes and about 12 percent of orders failed.
Root cause: the new version needs more memory than the container limit of 256Mi, so Kubernetes killed it with OOMKilled. The limit was not changed in the release, and the load test did not run with production data.
Resolution: the on-call engineer raised the memory limit to 512Mi in platform-manifests and Argo CD deployed it. The restarts stopped within 5 minutes.
Follow-up: alert when memory is above 80 percent of the limit; run the load test with production-size data before each release; review the memory limits of all services.

## Postmortem PM-2026-05: Expired certificate on the customer portal
Issue: users of the customer portal (account.edshopper.com) saw the browser warning "Your connection is not private" for 90 minutes on a Saturday morning.
Root cause: the TLS certificate of account.edshopper.com expired. It had been ordered by hand two years earlier and was not managed by cert-manager, so it was never renewed automatically and nobody received an alert.
Resolution: the platform on-call ordered a new certificate, updated the secret and restarted the ingress. The portal was healthy again after 15 minutes of work.
Follow-up: move all certificates to cert-manager; add the alert CertExpiringSoon for 14 days before expiry; list every certificate in one inventory page.

## Postmortem PM-2026-07: Nightly backup stopped for three days
Issue: the nightly database backup did not run for three days. Nobody noticed until a DBA checked the bucket during a restore test.
Root cause: the backup volume was 100 percent full because old backups were never deleted. The backup job failed, but its failure did not trigger an alert.
Resolution: the DBA deleted backups older than 30 days and ran the backup job again by hand. A new backup was in the bucket edshopper-prod-db-backups within 20 minutes.
Follow-up: add a retention rule that deletes backups older than 30 days; add the alert BackupJobFailed and an alert for disk usage above 85 percent; test a restore every month.
