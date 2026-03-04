## 2025-02-17 - Secure API Key Storage using bcrypt

**Vulnerability:** API keys were previously stored using a simple `SHA-256` hash and verified via direct dictionary lookup, making them vulnerable to timing attacks and potential reverse-engineering if the database was compromised.

**Learning:** When using `bcrypt` for secure secret hashing, you cannot use the hash as an O(1) dictionary lookup key because `bcrypt` includes a random salt, meaning the hash for the same secret is different every time. A dual-indexing strategy and multi-part API key structure (`prefix_{key_id}_{secret}`) are required. The `key_id` serves as a stable identifier for O(1) retrieval, and the `secret` is then verified against the stored `bcrypt` hash.

**Prevention:** Always use `bcrypt` for storing passwords and sensitive API keys. Implement a multi-part token structure that separates the public identifier (`key_id`) from the secret to allow efficient database lookups without compromising the secure, salted hashing of the sensitive component.
