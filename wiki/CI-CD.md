# CI/CD Pipeline

Continuous Integration and Deployment documentation.

## Overview

F1 Season Calculator uses GitHub Actions for automated testing, building, and deployment.

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   Commit    │───▶│     CI      │───▶│   Staging   │───▶│ Production  │
│             │    │   Pipeline  │    │   Deploy    │    │   Deploy    │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
      │                  │                  │                  │
      │            Automatic           Automatic            Manual
      │            on push/PR          on main             with approval
```

## Workflows

| Workflow | File | Trigger | Purpose |
|----------|------|---------|---------|
| CI | `ci.yml` | Push/PR | Test and build |
| CD - Staging | `cd-staging.yml` | Push to main | Auto-deploy staging |
| CD - Production | `cd-production.yml` | Manual | Production deploy |
| Release | `release.yml` | Manual | Create releases |

## CI Pipeline

Runs on every push and pull request.

### Jobs

```yaml
┌─────────┐  ┌──────────┐  ┌─────────────────────┐
│  Lint   │  │ Security │  │        Test         │
│         │  │   Scan   │  │ (3.10, 3.11, 3.12)  │
└────┬────┘  └────┬─────┘  └──────────┬──────────┘
     │            │                   │
     └────────────┴───────────────────┘
                  │
                  ▼
         ┌───────────────┐
         │ App Validation│
         └───────┬───────┘
                 │
                 ▼
         ┌───────────────┐
         │     Build     │
         └───────────────┘
```

### Lint Job

Checks code quality with flake8.

```yaml
- name: Run flake8
  run: |
    flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
    flake8 . --count --exit-zero --max-complexity=10 --max-line-length=127 --statistics
```

**What it catches**:
- Syntax errors
- Undefined names
- Unused imports
- Code complexity issues

### Security Job

Scans dependencies for vulnerabilities.

```yaml
- name: Run pip-audit
  run: pip-audit --strict
```

**What it checks**:
- Known CVEs in dependencies
- Outdated packages with security issues

### Test Job

Matrix testing across Python versions.

```yaml
strategy:
  matrix:
    python-version: ['3.10', '3.11', '3.12']
```

**Requirements**:
- Minimum 30% code coverage
- All tests must pass
- Coverage report uploaded as artifact

### App Validation Job

Verifies application starts correctly.

```yaml
- name: Validate Flask app starts
  run: |
    flask run &
    sleep 3
    curl -f http://127.0.0.1:5000/ || exit 1
    curl -f http://127.0.0.1:5000/apidocs/ || exit 1
```

### Build Job

Creates deployment artifact.

```yaml
- name: Create deployment package
  run: |
    tar -czvf dist/app-${{ github.sha }}.tar.gz \
      --exclude='.git' \
      --exclude='__pycache__' \
      .
```

**Output**: `app-package` artifact with 30-day retention

## CD - Staging

Automatically deploys to staging after CI passes on main.

### Flow

1. Push to main branch
2. Wait for CI workflow to complete
3. Deploy to staging environment
4. Run smoke tests
5. Notify on success/failure

### Configuration

The staging workflow includes placeholder deployment steps. Configure one of:

| Platform | Configuration |
|----------|--------------|
| Railway | `RAILWAY_TOKEN` secret |
| Heroku | `HEROKU_API_KEY`, `HEROKU_EMAIL` secrets |
| Render | `RENDER_DEPLOY_HOOK_STAGING` secret |
| Cloud Run | `GCP_PROJECT` secret |
| SSH | `STAGING_HOST`, `STAGING_USER`, `STAGING_SSH_KEY` secrets |

### Skip CI Option

For emergencies, deployment can skip CI:

```yaml
workflow_dispatch:
  inputs:
    skip_tests:
      description: 'Skip CI checks (use with caution)'
      default: 'false'
```

## CD - Production

Manual deployment with approval gates.

### Deployment Steps

1. Go to **Actions** > **CD - Production**
2. Click **Run workflow**
3. Enter version tag (e.g., `v1.2.3`)
4. Type `deploy` to confirm
5. Wait for environment approval
6. Deployment proceeds

### Safety Features

- Version tag must exist
- Confirmation text required
- Environment approval required
- Smoke tests after deploy
- Automatic rollback on failure

### Environment Configuration

Set up in GitHub repository settings:

1. Go to **Settings** > **Environments**
2. Create `production` environment
3. Add protection rules:
   - Required reviewers
   - Wait timer (optional)
4. Add secrets (deployment credentials)

## Release Workflow

Creates semantic version releases.

### Running a Release

1. Go to **Actions** > **Release**
2. Click **Run workflow**
3. Select version bump:
   - `patch` (1.0.0 → 1.0.1)
   - `minor` (1.0.0 → 1.1.0)
   - `major` (1.0.0 → 2.0.0)
4. Workflow creates:
   - Git tag
   - GitHub Release
   - Auto-generated changelog

### Version Calculation

```bash
# Get latest tag
LATEST=$(git describe --tags --abbrev=0 2>/dev/null || echo "v0.0.0")

# Calculate new version based on bump type
# patch: 1.0.0 → 1.0.1
# minor: 1.0.0 → 1.1.0
# major: 1.0.0 → 2.0.0
```

## Dependabot

Automated dependency updates.

### Configuration

```yaml
# .github/dependabot.yml
updates:
  - package-ecosystem: "pip"
    schedule:
      interval: "weekly"
      day: "monday"
    groups:
      python-minor-patch:
        update-types: ["minor", "patch"]

  - package-ecosystem: "github-actions"
    schedule:
      interval: "weekly"
```

### What It Does

- Weekly dependency checks
- Groups minor/patch updates
- Creates PRs automatically
- Labels PRs appropriately

## Local CI Simulation

Run CI checks locally before pushing:

```bash
# 1. Lint
flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics

# 2. Security
pip install pip-audit
pip-audit --strict

# 3. Tests with coverage
pytest tests/ -v --cov=championship --cov-fail-under=30

# 4. App validation
flask run &
sleep 3
curl -f http://127.0.0.1:5000/
```

## Secrets Required

| Secret | Used By | Description |
|--------|---------|-------------|
| `GITHUB_TOKEN` | All workflows | Auto-provided by GitHub |
| Deployment secrets | CD workflows | Platform-specific credentials |

## Troubleshooting

### CI Failing

1. Check which job failed
2. Read error logs
3. Run locally to reproduce
4. Fix and push

### Deployment Stuck

1. Check CD workflow logs
2. Verify secrets are configured
3. Check environment protection rules
4. Verify deployment platform status

### Coverage Too Low

1. Add tests for uncovered code
2. Focus on critical paths
3. Check coverage report artifact
