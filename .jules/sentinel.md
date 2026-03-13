## 2026-03-13 - Replace MD5 with SHA-256 for Non-Security Contexts
**Vulnerability:** Use of MD5 hashing algorithm for document deduplication (`hashlib.md5`).
**Learning:** Even when hashing is used for non-security contexts (like caching or document deduplication), using cryptographically broken algorithms like MD5 or SHA-1 triggers static analysis security alarms (e.g., Bandit S324).
**Prevention:** Use SHA-256 or stronger algorithms for all hashing needs throughout the codebase, regardless of whether the context is security-sensitive or not, to maintain a clean security posture and avoid false positives in automated scans.
