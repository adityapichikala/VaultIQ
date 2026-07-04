# Database Naming Conventions

**Owner:** Data Platform Team  
**ACL:** engineering

---

## 1. General Rules

All database objects at BigCorp follow these naming conventions to ensure consistency across services.

## 2. Table Naming

| Rule | Example |
|------|---------|
| Use snake_case | `user_profiles`, `order_items` |
| Use plural nouns | `users` not `user` |
| Prefix with domain for shared schemas | `payment_transactions`, `auth_sessions` |
| Junction tables: combine both table names | `user_roles`, `order_products` |

## 3. Column Naming

| Rule | Example |
|------|---------|
| snake_case always | `first_name`, `created_at` |
| Primary key: always `id` | `id BIGSERIAL PRIMARY KEY` |
| Foreign key: `{referenced_table}_id` | `user_id`, `order_id` |
| Timestamps: `{action}_at` | `created_at`, `updated_at`, `deleted_at` |
| Booleans: `is_{adjective}` or `has_{noun}` | `is_active`, `has_verified_email` |
| Money: always store in smallest unit (paise) | `amount_paise INTEGER` |
| Status fields: use ENUMs | `status payment_status NOT NULL` |

## 4. Index Naming

Format: `idx_{table}_{columns}`

Examples:
- `idx_users_email` — index on users.email
- `idx_orders_user_id_created_at` — composite index
- `uniq_users_email` — unique index

## 5. Migration Files

Format: `YYYYMMDD_HHMMSS_{description}.sql`

Example: `20260615_143022_add_payment_retry_count.sql`

Every migration must have a corresponding rollback file:
`20260615_143022_add_payment_retry_count.rollback.sql`

## 6. Common Anti-Patterns to Avoid

- ❌ `camelCase` column names (`firstName` → use `first_name`)
- ❌ Abbreviations (`usr`, `txn`, `amt` → use full words)
- ❌ Generic names (`data`, `value`, `type` without context)
- ❌ Storing money as FLOAT (use INTEGER in paise or NUMERIC)
- ❌ Using `status = 1/2/3` instead of ENUMs or status tables
