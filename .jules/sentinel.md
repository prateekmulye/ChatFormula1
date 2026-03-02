## 2024-05-24 - [Replace MD5 with SHA-256 for Document Hashing]
**Vulnerability:** Weak hashing algorithm (MD5) used for document deduplication in `src/ingestion/document_processor.py`.
**Learning:** MD5 is cryptographically broken and susceptible to collision attacks. Even in non-cryptographic contexts like deduplication, it triggers security linters and presents a risk if an attacker can control the input to intentionally cause collisions.
**Prevention:** Use SHA-256 (or stronger algorithms) consistently across the codebase for hashing operations, avoiding MD5 entirely.
