# Contributing Guidelines & Branching Strategy

Thank you for contributing to the **EV Charging Slot Booking System**. This document defines our Git workflow, branching policies, coding standards, and pull request procedures.

---

## 1. Branching Strategy

We follow a GitFlow-inspired branching model to ensure stability and smooth integration:

```
feature/<short-name> ──► develop ──► (release/hotfix) ──► main (production stable)
```

### 1.1 Branch Roles
- **`main`**:
  - The **production-ready stable branch**.
  - Direct commits to `main` are strictly prohibited.
  - All changes enter `main` only via reviewed and tested merges from `develop` or hotfix branches.
  - Every commit on `main` is considered deployable and should be tagged with a semantic version (e.g. `v1.0.0`).
- **`develop`**:
  - The **primary integration branch**.
  - All ongoing development features and bug fixes merge into `develop`.
  - Continuous Integration (CI) test suites run against this branch.
- **`feature/<short-description>`**:
  - Short-lived feature branches created off `develop`.
  - Example: `feature/seed-stations-data`, `feature/user-profile-endpoint`.
  - Merged into `develop` via Pull Request after code review and automated test passing.
- **`bugfix/<short-description>`** or **`hotfix/<short-description>`**:
  - Branches created to address defects. Bug fixes branch from `develop`; urgent hotfixes branch from `main`.

---

## 2. Development Workflow

### Step 1: Branch Creation
Always ensure your local `develop` branch is up to date before branching:
```bash
git checkout develop
git pull origin develop
git checkout -b feature/your-feature-name
```

### Step 2: Implementation & Quality Standards
- Preserve architectural conventions (Django REST Framework serializers, viewsets/APIViews).
- Always wrap database writes affecting multiple entities or bookings inside `transaction.atomic()`.
- Respect database locks: acquire `Charger` locks before `Booking` locks to eliminate deadlock potential.
- Never hardcode credentials, secrets, or host-specific ports.

### Step 3: Local Verification
Before committing or creating a pull request:
1. Run Django checks:
   ```bash
   docker compose exec web python manage.py check
   ```
2. Verify migrations:
   ```bash
   docker compose exec web python manage.py makemigrations --check --dry-run
   ```
3. Run the automated test suite:
   ```bash
   docker compose exec web python manage.py test
   ```

### Step 4: Committing Changes
Use meaningful, Conventional Commit messages:
- `feat: add station seeding management command`
- `fix: handle edge case in slot boundary validation`
- `docs: update API documentation for vehicle retrieval`
- `chore: update dependencies in requirements.txt`

### Step 5: Pull Request & Code Review
1. Push your feature branch:
   ```bash
   git push origin feature/your-feature-name
   ```
2. Open a Pull Request targeting the **`develop`** branch.
3. Complete the pull request template checklist.
4. Ensure all CI checks and tests pass.
5. Address review feedback before merging.

---

## 3. Security & Git Hygiene

- **`.env` files**: Never commit `.env` or files containing passwords, secret keys, or tokens.
- **`powershell.cmd` / Local Scripts**: Keep local helper scripts untracked and excluded from commits.
- **Clean Diffs**: Avoid committing unnecessary whitespace, IDE files (`.vscode/`, `.idea/`), or bytecode.
