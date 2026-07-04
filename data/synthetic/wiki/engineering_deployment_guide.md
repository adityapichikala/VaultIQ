# Production Deployment Guide

**Owner:** Platform Engineering  
**Last Updated:** May 20, 2026  
**ACL:** engineering

---

## 1. Overview

All production deployments at BigCorp follow the **blue-green deployment** model using ArgoCD on our Kubernetes clusters. This guide covers the standard deployment process for backend services.

## 2. Pre-Deployment Checklist

Before initiating any production deployment, ensure:

- [ ] All CI checks pass on the `main` branch
- [ ] Code review approved by at least 2 senior engineers
- [ ] Integration tests pass in the staging environment
- [ ] Database migration tested on staging (if applicable)
- [ ] Rollback plan documented in the deployment ticket
- [ ] On-call engineer notified via #deployments Slack channel
- [ ] Change request approved in ServiceNow (CR ticket number required)

## 3. Deployment Windows

| Environment | Window | Approval Needed |
|-------------|--------|----------------|
| Development | Anytime | None |
| Staging | Mon-Fri, 9 AM – 6 PM IST | Team lead |
| Production | Tue-Thu, 10 AM – 2 PM IST | Engineering Manager + SRE |
| Production (hotfix) | Anytime | VP Engineering + SRE on-call |

**No production deployments on Fridays** unless it's a critical hotfix (P0/P1).

## 4. Deployment Process

### Step 1: Tag the Release

```bash
git tag -a v2.14.3 -m "Release 2.14.3: Add payment retry logic"
git push origin v2.14.3
```

### Step 2: Trigger the Pipeline

ArgoCD will automatically detect the new tag and create a sync plan. Monitor at: `https://argocd.internal.bigcorp.com`

### Step 3: Canary Phase

The deployment starts with **5% traffic** to the new version. Monitor for 15 minutes:

- Error rate < 0.1%
- P99 latency < 500ms
- No new error types in Sentry

### Step 4: Progressive Rollout

If canary metrics are healthy:
- 5% → 25% (wait 10 min)
- 25% → 50% (wait 10 min)
- 50% → 100%

### Step 5: Post-Deployment Verification

- Run smoke tests: `make smoke-test ENV=production`
- Check Grafana dashboard: "Service Health — Production"
- Verify key business metrics in DataDog
- Update deployment log in Confluence

## 5. Rollback Procedure

If any metric crosses thresholds during canary:

```bash
# Immediate rollback via ArgoCD CLI
argocd app rollback <app-name> --to-revision <previous-revision>
```

**Rollback SLA:** Must complete within 5 minutes of detection.

## 6. Database Migrations

- All migrations must be **backward-compatible** (no column drops, no renames without aliases)
- Use the `migrate-safe` tool: `python manage.py migrate_safe --check-backward-compat`
- Migrations run **before** the code deployment
- Rollback migrations must be tested in staging

## 7. Incident Response

If a deployment causes a production incident:

1. Rollback immediately (don't debug in production)
2. Page the on-call SRE via PagerDuty
3. Open an incident channel: #inc-YYYYMMDD-short-description
4. Post-incident review within 48 hours (template in Confluence: "PIR Template")

## 8. Contact

- **Platform Engineering:** #platform-eng on Slack
- **SRE On-Call:** page via PagerDuty or call +91-XXXX-XXXXXX
- **ArgoCD Issues:** file a ticket under "Platform > ArgoCD" in Jira
