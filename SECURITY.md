# Security Policy

## Reporting a Vulnerability

Please report security concerns privately to [jiuzhou.zhu@ucdconnect.ie](mailto:jiuzhou.zhu@ucdconnect.ie). Do not open a public issue for a suspected vulnerability or accidental credential exposure.

Include a concise description, affected component, reproduction steps, impact, and any suggested mitigation. Do not include real production data, customer data, valid API keys, access tokens, passwords, or connection strings in a report.

## Sensitive Issues

Treat the following as security-sensitive:

- API-key exposure or insufficient secret masking.
- Unsafe SQL execution, including paths that bypass the read-only SQL guardrails.
- Dependency vulnerabilities affecting backend, frontend, or development tooling.

Use synthetic or redacted examples only. A report should contain the minimum information needed to reproduce the issue safely.
