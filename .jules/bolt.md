## 2024-03-16 - Pre-compiling regexes for performance

**Learning:** Recompiling regex patterns on every request causes unnecessary overhead, especially for complex patterns like input validation and sanitization. In `src/security/input_validation.py`, patterns were being repeatedly compiled on class initialization, negatively impacting request processing times.

**Action:** Always pre-compile regular expression patterns using `re.compile()` at the class or module level, particularly when they are used inside loops or frequently instantiated classes, to avoid the overhead of repeated compilation.
