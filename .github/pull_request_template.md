## Description
Provide a concise explanation of the changes introduced in this pull request and the problem they solve.

## Type of Change
- [ ] Bug fix (non-breaking change fixing an issue)
- [ ] New feature (non-breaking change adding functionality)
- [ ] Refactoring / Performance optimization (code improvement without behavior change)
- [ ] Documentation update
- [ ] CI/CD / DevOps / Infrastructure change

## Related Issues
Closes #[issue number]

## Verification & Testing
Describe the verification steps performed:
- [ ] Django system checks passed (`python manage.py check`)
- [ ] Database migrations dry-run verified (`python manage.py makemigrations --check --dry-run`)
- [ ] Automated test suite executed and passed (`python manage.py test`)
- [ ] Concurrency/overlap tests passed (if touching booking models/endpoints)
- [ ] Verified via live Docker Compose deployment (`/health/` and relevant endpoints)

## Pre-Merge Checklist
- [ ] Code follows project conventions and DRF patterns.
- [ ] No secrets, `.env` files, or API credentials are included or committed.
- [ ] Target branch is set to `develop` (not `main` directly for feature branches).
- [ ] Documentation updated to reflect changes (if applicable).
