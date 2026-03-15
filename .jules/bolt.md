## 2024-03-24 - Pre-compiling Regex Patterns
**Learning:** Compiling regular expression patterns dynamically inside loops or frequently called functions (like `re.sub` in `_sanitize` and `validate`) incurs unnecessary CPU overhead on every API request.
**Action:** Always pre-compile regular expression patterns using `re.compile()` at the class or module level, especially when used inside loops or high-frequency read paths, to avoid the overhead of repeated compilation.
