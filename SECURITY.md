# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 1.0.x   | :white_check_mark: |
| < 1.0   | :x:                |

## Reporting a Vulnerability

We take security seriously. If you discover a security vulnerability within Industrial Data Bridge, please follow these steps:

1. **Do NOT open a public GitHub Issue**
2. Email us at [team@industrial-data-bridge.org](mailto:team@industrial-data-bridge.org)
3. Include detailed information:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if any)

We will respond within 48 hours and work with you to address the issue promptly.

## Security Best Practices for Deployments

### 1. Change All Defaults

Before deploying to production, change all default credentials:

```bash
# In .env file - NEVER use the example values
JWT_SECRET_KEY=<generate-a-strong-random-key>
POSTGRES_PASSWORD=<unique-strong-password>
INFLUXDB_TOKEN=<unique-strong-token>
ENCRYPTION_KEY=<32-byte-random-key>
```

Generate strong secrets:
```bash
# Linux/macOS
openssl rand -hex 32

# All platforms (Python)
python -c "import secrets; print(secrets.token_hex(32))"
```

### 2. Network Security

- Use TLS/SSL for all external connections
- Configure firewall to restrict access to database ports
- Use VPN or private networks for production deployments
- Enable `ssl_mode` in database configuration

### 3. Authentication

- Enable JWT authentication
- Rotate API keys regularly
- Use strong passwords for all services
- Implement rate limiting for API endpoints

### 4. Data Protection

- Enable encryption for data at rest
- Use encrypted connections for data in transit
- Implement data retention policies
- Regularly back up configuration and data

### 5. Monitoring

- Enable audit logging
- Monitor for suspicious activities
- Set up alerts for security events
- Review logs regularly

## Dependencies

We use Dependabot to automatically update dependencies. Security patches for dependencies are applied promptly.

## Responsible Disclosure Timeline

- Day 0: Vulnerability reported
- Day 1-2: Initial assessment and acknowledgment
- Day 3-7: Investigation and fix development
- Day 7-14: Testing and validation
- Day 14-30: Coordinated disclosure and release

We appreciate responsible disclosure and will credit researchers who report valid security issues.