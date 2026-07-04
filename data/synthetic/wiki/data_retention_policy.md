# Data Retention & Deletion Policy

**Owner:** Legal & Compliance  
**Version:** 2.1  
**ACL:** engineering, hr, leadership

---

## 1. Purpose

BigCorp is committed to responsible data management in compliance with the Digital Personal Data Protection Act (DPDPA) 2023, IT Act 2000, and applicable sector-specific regulations. This policy defines how long we retain different categories of data and when/how data must be deleted.

## 2. Retention Schedule

| Data Category | Retention Period | After Expiry |
|--------------|-----------------|-------------|
| Customer PII (name, email, phone) | Active account + 3 years | Anonymize |
| Transaction records | 7 years (tax compliance) | Archive, then delete |
| Payment card data | Do not store (PCI-DSS) | N/A |
| Employee records | Employment + 7 years | Delete |
| Recruitment data (rejected candidates) | 1 year from rejection | Delete |
| Server logs (access logs) | 90 days | Delete |
| Application logs | 30 days (hot) + 1 year (cold) | Delete |
| Marketing consent records | Active consent + 5 years | Delete |
| CCTV footage | 90 days | Overwrite |
| Backup tapes | 1 year rolling | Overwrite |

## 3. Deletion Methods

| Data Location | Method | Verification |
|--------------|--------|-------------|
| PostgreSQL / MySQL | `DELETE` + `VACUUM` | Audit log entry |
| S3 / Object storage | Lifecycle policy + deletion marker | AWS CloudTrail |
| Elasticsearch | Index deletion | Curator logs |
| Physical media | Degaussing + certificate of destruction | Vendor certificate |
| Email archives | Auto-purge policy in Google Workspace | Admin console log |

## 4. Right to Erasure (DPDPA Compliance)

When a data principal (customer) exercises their right to erasure:

1. Request received via privacy@bigcorp.com or in-app "Delete My Data" button
2. Identity verification within 48 hours
3. Data mapping: identify all systems holding the principal's data
4. Deletion executed within **30 calendar days**
5. Confirmation sent to the data principal
6. Audit log retained for 5 years (legal requirement)

### Systems to Check for Erasure

- User database (PostgreSQL)
- Analytics warehouse (BigQuery) — anonymize, don't delete
- CRM (Salesforce)
- Email marketing (Mailchimp)
- Support tickets (Zendesk) — anonymize agent notes
- Slack messages — cannot delete individual user messages; anonymize in exports

## 5. Data Classification

| Classification | Examples | Access Level |
|---------------|----------|-------------|
| Public | Marketing content, blog posts | Anyone |
| Internal | Org charts, process docs | All employees |
| Confidential | Financial reports, salary data | Need-to-know |
| Restricted | Customer PII, payment data, health records | Specific roles only |

## 6. Breach Notification

If data is accessed or disclosed without authorization:

1. Report to security@bigcorp.com within **1 hour**
2. Data Protection Officer notified within 4 hours
3. CERT-In notification within 6 hours (if applicable under IT Act)
4. Customer notification within 72 hours (if PII is involved)

## 7. Contact

- Data Protection Officer: Ananya Iyer (dpo@bigcorp.internal)
- Legal & Compliance: legal@bigcorp.internal
- Security team: #security on Slack
