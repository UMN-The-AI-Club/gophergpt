# Database Schema

## Tables

### Profile

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| user_id | TEXT | PRIMARY KEY | |
| major | TEXT | nullable | |
| level | TEXT | nullable | e.g. undergraduate, graduate |
| year | TEXT | nullable | e.g. freshman, sophomore |
| personalization_notes | TEXT | nullable | |

---

### Conversation

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| id | TEXT | PRIMARY KEY | timestamp-based unique ID |
| title | TEXT | nullable | short summary of the conversation |
| profile_id | TEXT | nullable, FK → Profile.user_id | null if no profile exists |

---

### Message

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| id | TEXT | PRIMARY KEY | |
| role | TEXT | NOT NULL | "user" or "agent" |
| text | TEXT | NOT NULL | |
| content | JSON | nullable | structured frontend data (e.g. schedule cards) |
| created_at | DATETIME | NOT NULL | used to order messages within a conversation |
| conversation_id | TEXT | NOT NULL, FK → Conversation.id | |

---

## Relationships

- **Profile → Conversation**: one-to-many. A profile can have many conversations. A conversation optionally belongs to a profile (nullable).
- **Conversation → Message**: one-to-many. A conversation has many messages. A message always belongs to a conversation.
