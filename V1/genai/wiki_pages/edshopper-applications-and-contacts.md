# EdShopper applications, owners and on-call contacts
- Space: Applications
- Labels: edshopper, applications, inventory, services, owners, dependencies, contacts, on-call, paging, database, urls
- Owner: platform-team
- Last updated: 2026-11-10

## Summary of the five API services
| Application | Tier | Owner team | Database | Primary contact | On-call rota |
|---|---|---|---|---|---|
| checkout-api | 1 | shop-team | orders-db | Maria Lopez | shop-oncall |
| orders-api | 2 | shop-team | orders-db | Maria Lopez | shop-oncall |
| payments-api | 1 | payments-team | payments-db | Daniel Okafor | payments-oncall |
| inventory-api | 2 | shop-team | orders-db | Maria Lopez | shop-oncall |
| notifications-api | 3 | platform-team | no database (uses the message queue notifications-queue) | Aisha Khan | platform-oncall |
The Argo CD application of each service is named after the service and the environment, for example orders-api-stage. The current person on call is in the paging tool (see "Who is on call right now?").

## Service tiers
- Tier 1: checkout-api and payments-api. An outage is a SEV1. 4 and 3 replicas in prod.
- Tier 2: orders-api and inventory-api. An outage is a SEV2. 4 and 3 replicas in prod.
- Tier 3: notifications-api. An outage is a SEV3 unless it lasts for hours. 3 replicas in prod.

## checkout-api
The API behind the basket and checkout pages of www.edshopper.com: delivery address and placing the order. Tier 1.
- Owner team: shop-team (Slack #shop-team)
- Primary contact: Maria Lopez, maria.lopez@edshopper.com
- On-call contact: rota shop-oncall in the paging tool
- Database: orders-db (read and write)
- Depends on: orders-api, payments-api and orders-db
- URLs: prod https://api.edshopper.com/checkout, stage https://api.stage.edshopper.com/checkout, dev https://api.dev.edshopper.com/checkout
- Argo CD applications: checkout-api-prod, checkout-api-stage, checkout-api-dev
- Namespace: checkout. Deployment: checkout-api. Repository: https://github.com/edshopper/checkout-api

## orders-api
The API that creates and reads orders. Tier 2.
- Owner team: shop-team (Slack #shop-team)
- Primary contact: Maria Lopez, maria.lopez@edshopper.com
- On-call contact: rota shop-oncall in the paging tool
- Database: orders-db (read and write)
- Depends on: orders-db and inventory-api
- URLs: prod https://api.edshopper.com/orders, stage https://api.stage.edshopper.com/orders, dev https://api.dev.edshopper.com/orders
- Argo CD applications: orders-api-prod, orders-api-stage, orders-api-dev
- Namespace: orders. Deployment: orders-api. Repository: https://github.com/edshopper/orders-api

## payments-api
Takes the payment from the customer through the external payment provider (Stripe). Tier 1.
- Owner team: payments-team (Slack #payments-team)
- Primary contact: Daniel Okafor, daniel.okafor@edshopper.com
- On-call contact: rota payments-oncall in the paging tool
- Database: payments-db (read and write)
- Depends on: payments-db and the external payment provider (Stripe)
- URLs: internal only, called by checkout-api. prod https://payments-api.prod.edshopper.internal, stage https://payments-api.stage.edshopper.internal, dev https://payments-api.dev.edshopper.internal
- Argo CD applications: payments-api-prod, payments-api-stage, payments-api-dev
- Namespace: payments. Deployment: payments-api. Repository: https://github.com/edshopper/payments-api

## inventory-api
Keeps the stock levels of the products. Tier 2.
- Owner team: shop-team (Slack #shop-team)
- Primary contact: Maria Lopez, maria.lopez@edshopper.com
- On-call contact: rota shop-oncall in the paging tool
- Database: orders-db (read only for stock queries, write for stock updates)
- Depends on: orders-db
- URLs: prod https://api.edshopper.com/inventory, stage https://api.stage.edshopper.com/inventory, dev https://api.dev.edshopper.com/inventory
- Argo CD applications: inventory-api-prod, inventory-api-stage, inventory-api-dev
- Namespace: inventory. Deployment: inventory-api. Repository: https://github.com/edshopper/inventory-api

## notifications-api
Sends order emails and alerts to customers. Tier 3.
- Owner team: platform-team (Slack #platform-help)
- Primary contact: Aisha Khan, aisha.khan@edshopper.com
- On-call contact: rota platform-oncall in the paging tool
- Database: none. It reads jobs from the message queue notifications-queue and sends the emails through the email provider (Amazon SES).
- Depends on: the message queue notifications-queue and the email provider
- URLs: internal only, no public address. Health check: https://notifications-api.prod.edshopper.internal/health
- Argo CD applications: notifications-api-prod, notifications-api-stage, notifications-api-dev
- Namespace: notifications. Deployment: notifications-api. Repository: https://github.com/edshopper/notifications-api

## Teams, contacts and on-call rotas
| Team | Owns | Team lead (primary contact) | On-call rota | Slack |
|---|---|---|---|---|
| shop-team | checkout-api, orders-api, inventory-api | Maria Lopez | shop-oncall | #shop-team |
| payments-team | payments-api | Daniel Okafor | payments-oncall | #payments-team |
| platform-team | clusters, network, notifications-api | Aisha Khan | platform-oncall | #platform-help |
| dba-team | databases orders-db and payments-db | Tomasz Nowak | dba-oncall | #dba-team |
| sre-team | the on-call process and incident commanders | Chen Wei | sre-oncall, incident-commander | #sre-team |
Email addresses follow the pattern firstname.lastname@edshopper.com, for example tomasz.nowak@edshopper.com.

## Who is on call right now?
The wiki shows the rota, not the person on duty today, because that changes every week. Open the paging tool (PagerDuty) at https://edshopper.pagerduty.com, choose the rota (for example shop-oncall) and read the name under "On call now". To reach them, use "Page" on the same screen.

## Who do I page for what?
- An application problem: the on-call rota of the owner team of that application (see the summary table above).
- A database problem: dba-oncall.
- A cluster, network, DNS or certificate problem: platform-oncall.
- A SEV1: page the owner rota and also the rota incident-commander.
After 15 minutes without progress, page the team lead of the owner team.
