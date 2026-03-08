## 2025-03-08 - Use secure hashing for API keys
**Vulnerability:** API keys were hashed using SHA-256 and stored indexed by hash. SHA-256 is vulnerable to fast brute-force and rainbow table attacks.
**Learning:** API keys should be generated as a multi-part format (`prefix_id_secret`) allowing O(1) lookup by ID, and the secret should be securely hashed using `bcrypt`.
**Prevention:** Use `secrets.token_hex` for key parts and `bcrypt` for secure hashing, avoiding fast algorithms like SHA-256 for secrets.
