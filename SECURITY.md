# Security Policy

Relay takes system security and sandbox isolation seriously.

---

## 1. Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 0.4.x   | :white_check_mark: |
| < 0.4.0 | :x:                |

---

## 2. Reporting Vulnerabilities

If you discover a security vulnerability (such as a sandbox path traversal or checkpoint deserialization flaw), please report it directly to:

**Email**: `security@relay-ai.org`

Please **do not** open public GitHub issues for undisclosed security vulnerabilities. We will acknowledge receipt within 24 hours and provide a patch within 5 business days.

---

## 3. Security Hardening Architecture

- **Checkpoint Containment**: All file operations in `CheckpointManager` validate that target paths remain strictly inside designated checkpoint storage directories.
- **Trace Sandbox Isolation**: `TraceReplayExecutor` enforces root path containment (`abs_path.startswith(sandbox_abs)`).
- **CORS Restricting**: FastAPI endpoints restrict CORS origins strictly to localhost.
