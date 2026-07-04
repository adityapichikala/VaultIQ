# Incident Response Playbook

**Owner:** SRE Team  
**Version:** 4.0  
**ACL:** engineering

---

## 1. Severity Levels

| Severity | Definition | Response Time | Example |
|----------|-----------|--------------|---------|
| P0 — Critical | Complete outage, data loss, security breach | 15 minutes | Payment system down, customer data leaked |
| P1 — High | Major feature broken, >10% users affected | 30 minutes | Login failing for mobile users, search returning errors |
| P2 — Medium | Feature degraded, workaround exists | 2 hours | Slow dashboard loading, intermittent API timeouts |
| P3 — Low | Minor issue, cosmetic, <1% users | Next business day | Typo in email template, wrong icon on settings page |

## 2. Incident Commander (IC) Rotation

The IC is the person who runs the incident response. Current rotation:

| Week | Primary IC | Backup IC |
|------|-----------|-----------|
| Week 1 (Mon-Sun) | Deepak Gupta | Arjun Nair |
| Week 2 | Sanjay Rao | Amit Joshi |
| Week 3 | Rohit Saxena | Sneha Patel |
| Week 4 | Meena Krishnan | Ravi Shankar |

## 3. Incident Workflow

### Step 1: Detect & Alert
- **Automated:** PagerDuty alert from Grafana/DataDog
- **Manual:** Anyone can declare an incident by posting in #incidents with the `/incident` Slack command

### Step 2: Triage (first 5 minutes)
1. IC acknowledges the alert
2. Determine severity (P0/P1/P2/P3)
3. Create incident Slack channel: `#inc-20260629-short-name`
4. Post initial assessment: what's broken, who's affected, what we know

### Step 3: Assemble (first 15 minutes for P0/P1)
- IC pages relevant on-call engineers
- IC assigns roles:
  - **Comms Lead:** posts updates to #incidents every 15 minutes
  - **Tech Lead:** drives the investigation and fix
  - **Scribe:** records timeline in the incident doc

### Step 4: Investigate & Fix
- Check recent deployments (last 24h)
- Check infrastructure changes
- Check external dependencies (AWS status, API providers)
- **If in doubt, rollback first, investigate later**

### Step 5: Resolve & Communicate
- IC declares incident resolved
- Post summary in #incidents
- Customer-facing incidents: notify Customer Success team within 30 minutes of resolution
- Status page updated (statuspage.bigcorp.com)

### Step 6: Post-Incident Review (PIR)
- Schedule within **48 hours** of resolution
- Blameless — focus on systems, not individuals
- Template: Confluence → "PIR Template"
- Publish PIR to #engineering within 1 week

## 4. Escalation Matrix

| If... | Escalate to... |
|-------|---------------|
| P0 not acknowledged in 15 min | VP Engineering (Vikram Mehta) |
| P0 lasting > 1 hour | CTO (Sunita Reddy) |
| Data breach suspected | DPO (Ananya Iyer) + Legal |
| Customer SLA at risk | Head of Customer Success |
| PR/media risk | CMO + Corporate Communications |

## 5. Communication Templates

### Internal Update (every 15 min during P0/P1)
```
🔴 INCIDENT UPDATE — [INC-2026XXXX]
Status: Investigating / Identified / Monitoring / Resolved
Impact: [who is affected]
Current action: [what we're doing now]
Next update: [time]
IC: [name]
```

### Customer-Facing (via Status Page)
```
We are currently experiencing [brief description]. 
Our engineering team is actively investigating.
Affected services: [list]
Started: [time IST]
Last update: [time IST]
```

## 6. Post-Mortem Metrics (2026 YTD)

| Month | P0 | P1 | P2 | MTTR (P0) | MTTR (P1) |
|-------|----|----|-------|-----------|-----------|
| Jan | 0 | 2 | 5 | — | 45 min |
| Feb | 1 | 1 | 3 | 28 min | 22 min |
| Mar | 0 | 3 | 4 | — | 38 min |
| Apr | 1 | 0 | 6 | 52 min | — |
| May | 0 | 2 | 2 | — | 31 min |

**2026 Target:** MTTR < 30 min for P0, < 45 min for P1.

---

*This playbook is reviewed quarterly. Last review: April 2026. Next review: July 2026.*
