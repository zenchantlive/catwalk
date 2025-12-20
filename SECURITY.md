# Security Policy

## Reporting Vulnerabilities

**Please report security vulnerabilities responsibly.**

### How to Report

**DO NOT** open public GitHub issues for security vulnerabilities.

Instead, please email security concerns to: **zenchant@users.noreply.github.com**

Include:
- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if you have one)

We'll respond within 48 hours and work with you to understand and fix the issue.

## Security Best Practices

### Credential Handling

- ✅ All user credentials are encrypted with **Fernet** (symmetric encryption) before storage
- ✅ Encryption keys are stored as environment variables, never in code
- ✅ Database credentials use PostgreSQL's built-in SSL/TLS
- ✅ API keys are validated and sanitized before use

### Environment Variables

**Never commit `.env` files!**

- Use `.env.example` as a template
- Store production secrets in Fly.io secrets: `fly secrets set KEY=value`
- Rotate API keys if accidentally exposed
- Use strong encryption keys (32+ bytes, generated cryptographically)

### API Security

- All API endpoints validate inputs with Pydantic
- SQL injection protection via SQLAlchemy ORM
- CORS policies restrict allowed origins
- Rate limiting (planned for future phase)

### Infrastructure

- Fly.io provides network isolation for MCP containers
- Each deployment runs in its own isolated machine
- Health checks auto-restart unhealthy containers
- SSL/TLS enforced for all external communication

## Known Limitations

### Phase 1 (Current)

- **No rate limiting** - API endpoints are currently unprotected from abuse
- **No audit logging** - User actions are not logged for security review
- **Package validation is basic** - npm/PyPI packages are checked for existence but not for malware

These limitations will be addressed in future phases. See `context/plans/roadmap/` for details.

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 0.1.x   | ✅ Active development |

## Security Updates

Security fixes will be released as patch versions (e.g., 0.1.1) and announced via:
- GitHub Security Advisories
- Release notes
- Email to contributors

## License

This security policy is licensed under CC0 1.0 Universal (Public Domain).
