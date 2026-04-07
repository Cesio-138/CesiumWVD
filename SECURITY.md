# Security Policy

## Reporting a Vulnerability

If you discover a security vulnerability in CesiumWVD, please report it responsibly.

**Do not open a public issue.** Instead:

1. **GitHub Security Advisory** (preferred): Go to the repository's **Security** tab → **Report a vulnerability** → fill in the details.
2. **Email**: Contact the maintainer directly via the email address listed on their GitHub profile.

## What to Include

- Description of the vulnerability
- Steps to reproduce
- Affected versions
- Potential impact

## Scope

This project runs locally on the user's machine and interacts with:
- ADB (local USB/TCP connections to Android devices)
- GitHub (downloading frida-server releases)
- Google CDN (downloading Android system images)

Security concerns might include:
- Command injection via user-controlled inputs passed to subprocess calls
- Insecure temporary file handling
- Credential/key material leakage

## Response

We aim to acknowledge reports within **48 hours** and provide a fix or mitigation plan within **7 days** for confirmed vulnerabilities.
