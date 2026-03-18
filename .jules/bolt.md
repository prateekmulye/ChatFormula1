
## 2024-05-24 - Pre-compile Regex Patterns
**Learning:** `re.sub` and `re.search` are called continuously in hot loops or frequently accessed validation methods (like `InputValidator.validate`, `InputValidator._sanitize`, `InputSanitizer.sanitize`, and `DocumentProcessor._clean_text`). Each call to `re.sub(pattern, ...)` compiles the regular expression on the fly, which introduces CPU overhead. Python's re module caches some compiled patterns, but explicit compilation with `re.compile()` avoids the cache lookup overhead and provides a measurable speedup when used frequently.
**Action:** Pre-compile regular expressions at the class or module level, especially when used inside loops or high-frequency functions, to avoid the overhead of repeated compilation.
