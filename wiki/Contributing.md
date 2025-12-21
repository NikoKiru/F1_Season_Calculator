# Contributing

Guide for contributing to F1 Season Calculator.

## Ways to Contribute

| Type | Description |
|------|-------------|
| Bug Reports | Found a bug? Let us know! |
| Feature Requests | Have an idea? Share it! |
| Code | Fix bugs or add features |
| Documentation | Improve docs and wiki |
| Testing | Add test coverage |

## Getting Started

### 1. Fork the Repository

Click the "Fork" button on GitHub to create your own copy.

### 2. Clone Your Fork

```bash
git clone https://github.com/YOUR_USERNAME/F1_Season_Calculator.git
cd F1_Season_Calculator
```

### 3. Set Up Development Environment

```bash
# Create virtual environment
python -m venv .venv

# Activate (Windows)
.venv\Scripts\activate

# Activate (Linux/Mac)
source .venv/bin/activate

# Install in development mode
pip install -e .

# Install dev dependencies
pip install pytest pytest-cov black flake8

# Initialize application
flask setup

# Verify setup
pytest
```

### 4. Create a Branch

```bash
git checkout -b feature/your-feature-name
# or
git checkout -b fix/bug-description
```

## Development Workflow

### Code Style

We follow PEP 8 with these specifications:
- Line length: 100 characters
- 4 spaces for indentation
- Google-style docstrings

**Formatting**:
```bash
# Format code
black .

# Check formatting
black --check .
```

**Linting**:
```bash
# Run linter
flake8 . --max-line-length=100
```

### Testing

All changes must include tests.

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=championship --cov-report=html

# Run specific test
pytest tests/test_api.py::test_function_name
```

**Test Requirements**:
- Minimum 30% coverage (enforced by CI)
- Target 80%+ coverage
- Follow AAA pattern (Arrange, Act, Assert)

### Commit Messages

Format:
```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types**:
| Type | Description |
|------|-------------|
| `feat` | New feature |
| `fix` | Bug fix |
| `docs` | Documentation |
| `style` | Formatting |
| `refactor` | Code restructuring |
| `perf` | Performance improvement |
| `test` | Tests |
| `chore` | Build/tooling |

**Examples**:
```
feat(api): add championship win probability endpoint

Implemented new endpoint that calculates win probability
based on remaining races.

Closes #123
```

```
fix(ui): resolve table overflow on mobile

Tables were extending beyond viewport on small screens.
Added responsive wrapper with horizontal scroll.

Fixes #456
```

## Pull Request Process

### Before Submitting

- [ ] Code follows style guidelines
- [ ] Tests pass locally (`pytest`)
- [ ] Linting passes (`flake8`)
- [ ] Documentation updated if needed
- [ ] Commit messages follow conventions

### Submitting

1. Push your branch:
   ```bash
   git push origin feature/your-feature-name
   ```

2. Open a Pull Request on GitHub

3. Fill out the PR template:
   ```markdown
   ## Description
   Brief description of changes.

   ## Type of Change
   - [ ] Bug fix
   - [ ] New feature
   - [ ] Breaking change
   - [ ] Documentation

   ## Testing
   Describe tests performed.

   ## Checklist
   - [ ] Code follows style guidelines
   - [ ] Self-reviewed
   - [ ] Tests added
   - [ ] Documentation updated
   ```

### Review Process

1. Automated CI checks run
2. Maintainer reviews code
3. Address feedback
4. Approval and merge

## CI/CD Pipeline

All PRs trigger automated checks:

| Check | Description |
|-------|-------------|
| Lint | flake8 code quality |
| Security | pip-audit vulnerability scan |
| Test | pytest on Python 3.10, 3.11, 3.12 |
| Coverage | Minimum 30% required |
| App Validation | Flask app starts correctly |

See [[CI-CD]] for pipeline details.

## Project Structure

```
championship/
├── api.py        # REST endpoints
├── views.py      # Web routes
├── commands.py   # CLI commands
├── logic.py      # Calculations
├── models.py     # Data models
└── errors.py     # Error handlers
```

See [[Architecture]] for detailed documentation.

## Reporting Bugs

Use the GitHub issue template:

```markdown
**Describe the bug**
Clear description of the issue.

**To Reproduce**
1. Go to '...'
2. Click on '...'
3. See error

**Expected behavior**
What should happen.

**Screenshots**
If applicable.

**Environment**
- OS: [e.g., Windows 11]
- Python: [e.g., 3.11]
- Browser: [e.g., Chrome 120]
```

## Requesting Features

Include:
- Clear description
- Use cases
- Examples
- Why it would be useful

## Code of Conduct

- Be respectful
- Be collaborative
- Be constructive
- Welcome newcomers

## Questions?

- Check existing [Issues](https://github.com/NikoKiru/F1_Season_Calculator/issues)
- Open a [Discussion](https://github.com/NikoKiru/F1_Season_Calculator/discussions)
- Contact maintainers

## Thank You!

Every contribution matters. Whether fixing a typo or adding a major feature, your work is appreciated!
