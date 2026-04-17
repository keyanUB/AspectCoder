# OWASP Secure Coding Practices — Quick Reference (2010, still current)

Source: https://owasp.org/www-project-secure-coding-practices-quick-reference-guide/

For each practice area below, verify the code under review complies.

---

## 1. Input Validation
- Validate all input from untrusted sources (users, files, network, environment variables).
- Validate for expected type, length, format, and range before any processing.
- Reject or sanitize inputs that fail validation; do not attempt to "fix" dangerous input.
- Validate on the server side; never rely solely on client-side validation.
- Use a centralised, library-based validation approach rather than ad-hoc checks.

## 2. Output Encoding
- Encode all output to the appropriate context (HTML, URL, JS, CSS, SQL, shell).
- Apply encoding as close to output as possible, not at input time.
- Do not rely on "blacklist" encoding; use context-aware allowlist encoding.

## 3. Authentication and Password Management
- Require authentication for all pages and resources except those intended to be public.
- Use only strong, standard authentication algorithms (e.g., bcrypt, Argon2 for passwords).
- Enforce minimum password complexity and length requirements.
- Do not store passwords in plain text or with weak hashing (MD5, SHA-1).
- Implement account lockout after repeated failed attempts.
- Use HTTPS for all authentication-related traffic.
- Transmit credentials only over TLS-encrypted connections.

## 4. Session Management
- Use the framework's built-in session management; never write custom session tokens.
- Generate a new session ID upon authentication.
- Set session tokens to be random, long (≥128 bits), and unpredictable.
- Expire sessions after inactivity and on logout; invalidate server-side.
- Set cookies with Secure, HttpOnly, and SameSite attributes.

## 5. Access Control
- Enforce access control decisions on every request server-side.
- Deny access by default; grant minimum necessary permissions (principle of least privilege).
- Log all access-control failures.
- Do not use direct object references that expose internal IDs without authorisation checks.
- Separate privileged logic from unprivileged logic.

## 6. Cryptographic Practices
- Use only vetted, strong cryptographic algorithms and key lengths (AES-256, RSA-2048+, SHA-256+).
- Generate cryptographically random values with a CSPRNG; never use Math.random() for secrets.
- Do not hard-code cryptographic keys in source code.
- Manage key lifecycle: generation, distribution, storage, rotation, and destruction.
- Do not implement custom cryptographic algorithms.

## 7. Error Handling and Logging
- Do not expose stack traces, internal paths, or sensitive data in error messages to users.
- Log all security-relevant events: authentication, authorisation failures, input validation errors.
- Do not log sensitive data (passwords, session tokens, PII) in log files.
- Ensure logs are protected from unauthorised access and modification.
- Handle all exceptions; do not silently swallow errors.

## 8. Data Protection
- Protect sensitive data at rest with encryption.
- Minimise data collection; do not store sensitive data longer than necessary.
- Scrub sensitive data from memory after use (overwrite, don't just dereference).
- Do not cache sensitive data in client-side storage (localStorage, cookies) unless necessary and encrypted.

## 9. Communication Security
- Encrypt all transmissions of sensitive data using TLS (TLS 1.2+ recommended).
- Verify certificates; never disable certificate validation.
- Use HSTS, certificate pinning where appropriate.
- Never transmit sensitive data in query strings (visible in logs and browser history).

## 10. System Configuration
- Keep all software components up to date; remove unused dependencies.
- Disable debug features, verbose error messages, and directory listings in production.
- Run services with the minimum required privileges.
- Apply security headers (CSP, X-Frame-Options, X-Content-Type-Options).

## 11. Database Security
- Use parameterised queries or prepared statements for all database access.
- Minimise database account privileges (read-only where possible).
- Disable unnecessary stored procedures and built-in database functions.
- Sanitise all data returned from the database before displaying to users.

## 12. File Management
- Do not pass user-supplied filenames directly to filesystem APIs.
- Validate file types by content (magic bytes), not solely by extension or MIME type from the client.
- Store uploaded files outside the web root or in a sandboxed location.
- Ensure file permissions are set to the minimum required.

## 13. Memory Management (C/C++ and similar)
- Validate buffer sizes before copying; prefer bounded functions (strncpy, snprintf).
- Free all allocated memory and set pointers to NULL after free.
- Avoid dangerous functions: gets(), sprintf(), strcat() without length checks.
- Use ASLR, stack canaries, and other OS-level mitigations where available.
- Check return values of all memory allocation calls.

## 14. General Coding Practices
- Use tested, approved, and maintained libraries and frameworks.
- Avoid dead code, unused variables, and commented-out code blocks.
- Do not use deprecated or unsafe APIs.
- Review all third-party components for known vulnerabilities (CVE databases).
- Treat all data from outside the trust boundary as hostile.
