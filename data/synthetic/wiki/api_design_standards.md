# API Design Standards — BigCorp Engineering

**Owner:** Architecture Review Board  
**Version:** 3.2  
**ACL:** engineering

---

## 1. General Principles

All public and internal APIs at BigCorp must follow RESTful design principles. GraphQL is permitted for BFF (Backend-for-Frontend) layers only, with Architecture Board approval.

## 2. URL Structure

```
https://api.bigcorp.com/v{major}/{resource}/{id}/{sub-resource}
```

### Rules:
- Use **plural nouns** for resources: `/users`, `/orders`, `/invoices`
- Use **kebab-case** for multi-word resources: `/payment-methods`
- Never put verbs in URLs. Use HTTP methods instead
- Maximum URL depth: 3 levels (e.g., `/users/123/orders`)
- Version in the URL path, not headers: `/v1/`, `/v2/`

## 3. HTTP Methods

| Method | Use Case | Idempotent | Safe |
|--------|----------|-----------|------|
| GET | Retrieve resource(s) | Yes | Yes |
| POST | Create a new resource | No | No |
| PUT | Full update of a resource | Yes | No |
| PATCH | Partial update | No | No |
| DELETE | Remove a resource | Yes | No |

## 4. Response Codes

| Code | When to Use |
|------|-------------|
| 200 | Successful GET, PUT, PATCH |
| 201 | Successful POST (resource created) |
| 204 | Successful DELETE (no body) |
| 400 | Bad request (validation error) |
| 401 | Unauthorized (no/bad token) |
| 403 | Forbidden (valid token, no permission) |
| 404 | Resource not found |
| 409 | Conflict (duplicate, version mismatch) |
| 422 | Unprocessable entity (semantic validation) |
| 429 | Rate limited |
| 500 | Internal server error |
| 503 | Service unavailable (maintenance, overload) |

## 5. Pagination

All list endpoints **must** support pagination. Use cursor-based pagination for large datasets:

```json
{
  "data": [...],
  "pagination": {
    "next_cursor": "eyJpZCI6MTAwfQ==",
    "has_more": true,
    "total_count": 1523
  }
}
```

Query parameters: `?limit=20&cursor=eyJpZCI6MTAwfQ==`

Default limit: 20. Maximum limit: 100.

## 6. Error Response Format

All errors must follow this schema:

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Human-readable description",
    "details": [
      {
        "field": "email",
        "issue": "must be a valid email address"
      }
    ],
    "request_id": "req_abc123xyz"
  }
}
```

## 7. Authentication

- All APIs use **OAuth 2.0 Bearer tokens** via the Authorization header
- Internal service-to-service: mTLS + service accounts
- API keys are deprecated and must not be used for new services
- Token lifetime: 1 hour (access), 30 days (refresh)

## 8. Rate Limiting

| Tier | Requests/min | Who |
|------|-------------|-----|
| Free | 60 | External free-tier users |
| Standard | 600 | Paying customers |
| Premium | 6,000 | Enterprise customers |
| Internal | 30,000 | Internal services |

Rate limit headers must be included in every response:
```
X-RateLimit-Limit: 600
X-RateLimit-Remaining: 542
X-RateLimit-Reset: 1719648000
```

## 9. Versioning Strategy

- **Major version** in URL: `/v1/`, `/v2/`
- Breaking changes require a new major version
- Old versions supported for **12 months** after new version GA
- Non-breaking changes (new optional fields, new endpoints) do not require version bump

## 10. Documentation

Every API must have:
- OpenAPI 3.1 spec in the repo (`/docs/openapi.yaml`)
- Auto-generated docs served at `/{service}/docs`
- At least 3 example requests per endpoint
- Changelog maintained in `CHANGELOG.md`

---

*Questions? Ask in #api-guild on Slack or file an Architecture Review request in Jira.*
