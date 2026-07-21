# Contributing to GeniusQ DaaS

Thanks for helping improve this team/course demonstration. Keep changes focused, preserve existing attribution, and do not present a contribution as sole authorship of the project.

## Development Setup

Prerequisites:

- Python 3.9 or later
- Node.js 18 or later

Install the backend test dependencies and frontend packages from the repository root:

```powershell
python -m pip install -e "backend[test]"
npm.cmd --prefix frontend install
```

For a local demo, use the offline mode in `.env.example`. It works without an API key. DeepSeek mode requires your own API key and must remain local.

## Validation

Run the relevant checks before opening a pull request:

```powershell
python -m pytest backend/tests -q
npm.cmd --prefix frontend run test:run
npm.cmd --prefix frontend run build
```

For non-PowerShell shells where `npm` resolves directly, use the equivalent commands:

```powershell
npm --prefix frontend run test:run
npm --prefix frontend run build
```

In Windows PowerShell, prefer `npm.cmd`; some execution policies block `npm.ps1`.

The frontend suite currently has two known failures in `src/test/sidebar-layout.test.ts`; do not mask, delete, or alter those tests as part of an unrelated change. Report the observed result clearly in your pull request until the underlying issue is resolved.

## Pull Requests

- Keep each pull request small and focused on one clear change.
- Explain the user-facing impact and link related issues when available.
- Add or update tests when behavior changes.
- Include screenshots for visible UI changes.
- Never commit API keys, `.env` files, runtime databases, generated output, or production data.
- Use the pull request template and complete its secret-scan confirmation.

## Reporting Problems

Use the issue templates for reproducible bugs and well-scoped feature requests. For vulnerabilities or accidental credential exposure, follow [SECURITY.md](SECURITY.md) instead of opening a public issue.
