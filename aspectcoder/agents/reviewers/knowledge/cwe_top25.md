# CWE Top 25 Most Dangerous Software Weaknesses (2024)

Source: https://cwe.mitre.org/top25/archive/2024/2024_cwe_top25.html

For each item below, check whether the code under review is vulnerable to this weakness.

---

## 1. CWE-79 — Improper Neutralization of Input During Web Page Generation (XSS)
User-controlled data is reflected into HTML/JS output without encoding.
**Check:** Any output of user input to HTML, JS, or CSS context without escaping (e.g. innerHTML, document.write, template literals with raw user data).

## 2. CWE-787 — Out-of-bounds Write
Writing to a memory location before the start or past the end of a buffer.
**Check:** Array indexing without bounds validation; memcpy/strcpy with unchecked sizes; pointer arithmetic.

## 3. CWE-89 — SQL Injection
SQL queries constructed by concatenating unsanitized user input.
**Check:** String concatenation or f-string formatting to build SQL; absence of parameterized queries / prepared statements.

## 4. CWE-416 — Use After Free
Memory accessed after it has been freed.
**Check:** Pointers used after free(); dangling pointer patterns in C/C++; double-free.

## 5. CWE-78 — OS Command Injection
Shell commands constructed from unsanitized user input.
**Check:** subprocess/os.system calls using string concatenation; shell=True with user data; exec/eval with external input.

## 6. CWE-20 — Improper Input Validation
Inputs not validated for type, length, format, or range before use.
**Check:** Missing null checks, length guards, integer range checks, format validation at function/API entry points.

## 7. CWE-125 — Out-of-bounds Read
Reading from a memory location before the start or past the end of a buffer.
**Check:** Array access without upper-bound check; strlen-based loops on untrusted strings; read past allocated size.

## 8. CWE-22 — Path Traversal (Improper Limitation of a Pathname)
File paths constructed from user input allow access outside intended directory.
**Check:** open()/fopen() calls using concatenated user input; missing canonicalization or prefix-check of resolved path.

## 9. CWE-352 — Cross-Site Request Forgery (CSRF)
Forged cross-site requests execute privileged actions on behalf of authenticated users.
**Check:** State-changing endpoints lack CSRF token validation; no SameSite cookie policy enforced.

## 10. CWE-434 — Unrestricted Upload of Dangerous File Type
Server accepts uploaded files without restricting executable or dangerous types.
**Check:** File upload handlers that do not validate extension, MIME type, or content; uploaded files stored in web-accessible directories.

## 11. CWE-862 — Missing Authorization
Actions performed without verifying the caller has permission.
**Check:** Operations that modify data or access sensitive resources without checking identity or role.

## 12. CWE-476 — NULL Pointer Dereference
Dereferencing a pointer that is NULL.
**Check:** Return values of malloc/calloc/realloc not checked; function return values not null-checked before use.

## 13. CWE-287 — Improper Authentication
Authentication mechanism can be bypassed or is insufficient.
**Check:** Authentication logic with hardcoded bypass conditions; weak credential comparisons; missing MFA enforcement on critical actions.

## 14. CWE-190 — Integer Overflow or Wraparound
Arithmetic operations produce values that exceed the integer type's range.
**Check:** Size computations used in memory allocation; loop counters; calculations involving user-supplied integers without overflow guard.

## 15. CWE-502 — Deserialization of Untrusted Data
Deserializing data from untrusted sources without integrity checks.
**Check:** pickle.loads / yaml.load / eval / JSON.parse of raw user input; object deserialization from network/file without schema validation.

## 16. CWE-77 — Command Injection (Improper Neutralization of Special Elements in a Command)
Special characters in user input alter the intended command structure.
**Check:** Any command-line construction using user data; missing shell metacharacter escaping.

## 17. CWE-119 — Improper Restriction of Operations within Bounds of Memory Buffer
Buffer operations not restricted to the buffer's bounds.
**Check:** gets(), sprintf(), strcat() without length checks; fixed-size buffers receiving variable-length input.

## 18. CWE-798 — Use of Hard-coded Credentials
Credentials embedded directly in source code.
**Check:** Hardcoded passwords, API keys, tokens, or secrets in code; default credentials never changed.

## 19. CWE-918 — Server-Side Request Forgery (SSRF)
Server makes HTTP requests to attacker-controlled URLs.
**Check:** URLs constructed from user input passed to HTTP clients; missing allowlist of target hosts/protocols.

## 20. CWE-306 — Missing Authentication for Critical Function
Critical functionality accessible without any authentication.
**Check:** Administrative or destructive endpoints reachable without identity verification.

## 21. CWE-362 — Race Condition (Concurrent Execution Using Shared Resource)
Multiple threads/processes access a shared resource without adequate synchronization.
**Check:** Shared mutable state accessed without locks; TOCTOU patterns (check-then-use of files, flags, counters).

## 22. CWE-269 — Improper Privilege Management
Processes or operations run with more privileges than necessary.
**Check:** setuid/setgid misuse; operations that do not drop privileges after they are no longer needed.

## 23. CWE-94 — Code Injection (Improper Control of Generation of Code)
Attacker-controlled data is interpreted as code.
**Check:** eval(), exec(), compile() on user input; dynamic code generation from external data.

## 24. CWE-863 — Incorrect Authorization
Access control decisions made incorrectly.
**Check:** Authorization logic based on untrusted client-provided values; missing server-side enforcement.

## 25. CWE-276 — Incorrect Default Permissions
Resources created with overly permissive access settings.
**Check:** Files/directories created with world-writable permissions; umask not set appropriately; sensitive resources accessible to all users.
