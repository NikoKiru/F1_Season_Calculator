# Contributing to F1 Season Calculator

First off, thank you for considering contributing to F1 Season Calculator! It's people like you that make this tool amazing for the F1 community.

## 📋 Table of Contents

- [Code of Conduct](#code-of-conduct)
- [How Can I Contribute?](#how-can-i-contribute)
- [Development Setup](#development-setup)
- [Coding Standards](#coding-standards)
- [Commit Guidelines](#commit-guidelines)
- [Pull Request Process](#pull-request-process)
- [Project Structure](#project-structure)
- [Testing](#-testing)
- [CI/CD Pipeline](#-cicd-pipeline)

## 📜 Code of Conduct

This project adheres to a simple code of conduct: be respectful, be collaborative, and be constructive. We're all here to learn and build something great together.

## 🤝 How Can I Contribute?

### Reporting Bugs

Before creating bug reports, please check the issue list as you might find out that you don't need to create one. When you are creating a bug report, please include as many details as possible:

* **Use a clear and descriptive title**
* **Describe the exact steps to reproduce the problem**
* **Provide specific examples to demonstrate the steps**
* **Describe the behavior you observed and what you expected**
* **Include screenshots if relevant**
* **Mention your environment** (OS, Python version, browser, etc.)

**Bug Report Template:**
```markdown
**Describe the bug**
A clear description of what the bug is.

**To Reproduce**
Steps to reproduce:
1. Go to '...'
2. Click on '....'
3. See error

**Expected behavior**
What you expected to happen.

**Screenshots**
If applicable, add screenshots.

**Environment:**
 - OS: [e.g. Windows 11]
 - Python: [e.g. 3.10]
 - Browser: [e.g. Chrome 120]

**Additional context**
Any other information about the problem.
```

### Suggesting Enhancements

Enhancement suggestions are tracked as GitHub issues. When creating an enhancement suggestion, please include:

* **Use a clear and descriptive title**
* **Provide a detailed description of the suggested enhancement**
* **Explain why this enhancement would be useful**
* **List some examples of how it would be used**

### Your First Code Contribution

Unsure where to begin? You can start by looking through these issues:

* **good-first-issue** - issues which should only require a few lines of code
* **help-wanted** - issues which might be a bit more involved
* **documentation** - improvements to documentation

## 💻 Development Setup

### Prerequisites

- Python 3.10+ (tested on 3.10, 3.11, 3.12)
- Git
- Virtual environment tool (venv)

### Setup Steps

```bash
# 1. Fork and clone the repository
git clone https://github.com/YOUR_USERNAME/F1_Season_Calculator.git
cd F1_Season_Calculator

# 2. Create a virtual environment
python -m venv .venv

# 3. Activate virtual environment
# Windows
.venv\Scripts\Activate.ps1
# Linux/Mac
source .venv/bin/activate

# 4. Install in development mode
pip install -e .

# 5. Install development dependencies
pip install pytest pytest-cov black flake8

# 6. Run setup
flask setup

# 7. Run tests to verify setup
pytest
```

### Running the Development Server

```bash
flask run
```

The application will be available at `http://127.0.0.1:5000`

## 🎨 Coding Standards

### Python Style Guide

We follow [PEP 8](https://pep8.org/) with some exceptions:

* Line length: 100 characters (vs 79)
* Use 4 spaces for indentation (never tabs)
* Use descriptive variable names
* Add docstrings to all functions and classes

### Code Formatting

We use `black` for code formatting:

```bash
# Format all Python files
black .

# Check formatting without modifying
black --check .
```

### Linting

We use `flake8` for linting:

```bash
# Run linter
flake8 .

# With specific configuration
flake8 --max-line-length=100 --ignore=E203,W503 .
```

### Naming Conventions

* **Functions/Methods:** `snake_case`
* **Classes:** `PascalCase`
* **Constants:** `UPPER_SNAKE_CASE`
* **Private methods:** `_leading_underscore`
* **Modules:** `lowercase`

### Documentation

* Add docstrings to all public functions, classes, and modules
* Use Google-style docstrings

```python
def calculate_standings(drivers, scores, race_subset):
    """Calculate championship standings for a subset of races.

    Args:
        drivers (np.ndarray): Array of driver abbreviations.
        scores (np.ndarray): 2D array of driver scores per race.
        race_subset (tuple): Tuple of race indices to include.

    Returns:
        tuple: (sorted_drivers, sorted_scores) - Arrays sorted by points.

    Example:
        >>> drivers = np.array(['VER', 'NOR', 'LEC'])
        >>> scores = np.array([[25, 18], [18, 25], [15, 15]])
        >>> calculate_standings(drivers, scores, (0,))
        (array(['VER', 'NOR', 'LEC']), array([25, 18, 15]))
    """
    # Implementation
```

## 📝 Commit Guidelines

### Commit Message Format

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types:**
* **feat:** New feature
* **fix:** Bug fix
* **docs:** Documentation changes
* **style:** Code style changes (formatting, etc.)
* **refactor:** Code refactoring
* **perf:** Performance improvements
* **test:** Adding or updating tests
* **chore:** Build process or auxiliary tool changes

**Examples:**
```
feat(api): add championship win probability endpoint

Implemented new endpoint that calculates win probability based on
number of races. Uses caching for performance.

Closes #123
```

```
fix(ui): resolve table overflow on mobile devices

Tables were extending beyond container on small screens.
Added responsive wrapper with horizontal scroll.

Fixes #456
```

```
docs(readme): update installation instructions

Added section about virtual environment setup and
clarified Python version requirements.
```

### Commit Message Guidelines

* Use the present tense ("Add feature" not "Added feature")
* Use the imperative mood ("Move cursor to..." not "Moves cursor to...")
* Limit the first line to 72 characters or less
* Reference issues and pull requests liberally after the first line
* Consider starting the commit message with an applicable emoji:
    * 🎨 `:art:` - Improve structure/format
    * ⚡ `:zap:` - Improve performance
    * 🐛 `:bug:` - Fix a bug
    * ✨ `:sparkles:` - Add new feature
    * 📝 `:memo:` - Add or update documentation
    * ♻️ `:recycle:` - Refactor code
    * ✅ `:white_check_mark:` - Add or update tests

## 🔄 Pull Request Process

### Before Submitting

1. **Update documentation** - Ensure README and docs are updated
2. **Add tests** - Write tests for new features
3. **Run tests** - Make sure all tests pass
4. **Format code** - Run `black` and `flake8`
5. **Update CHANGELOG** - Add entry for your changes

### Submitting a Pull Request

1. **Create a branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes**
   - Write code
   - Add tests
   - Update documentation

3. **Commit your changes**
   ```bash
   git commit -m "feat(scope): description"
   ```

4. **Push to your fork**
   ```bash
   git push origin feature/your-feature-name
   ```

5. **Open a Pull Request**
   - Go to the repository on GitHub
   - Click "New Pull Request"
   - Select your branch
   - Fill out the PR template

### Pull Request Template

```markdown
## Description
Brief description of changes.

## Type of change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
Describe the tests you ran.

## Checklist
- [ ] My code follows the project's style guidelines
- [ ] I have performed a self-review
- [ ] I have commented my code where necessary
- [ ] I have updated the documentation
- [ ] I have added tests
- [ ] All tests pass locally
```

### Review Process

* At least one maintainer review is required
* Address all review comments
* Keep your PR up to date with main branch
* Be patient and respectful during review

## 📁 Project Structure

Understanding the codebase structure:

```
F1_Season_Calculator/
├── championship/           # Core business logic
│   ├── api.py             # REST API endpoints
│   ├── commands.py        # CLI commands
│   ├── views.py           # Web routes
│   ├── logic.py           # Calculations
│   ├── models.py          # Data models
│   └── errors.py          # Error handlers
│
├── static/                # Frontend assets
│   ├── js/               # JavaScript files
│   └── style.css         # Stylesheets
│
├── templates/             # HTML templates
│
├── docs/                  # Documentation
│   ├── setup/            # Setup guides
│   ├── architecture/     # Architecture docs
│   ├── performance/      # Performance docs
│   └── ui/               # UI/UX docs
│
├── tests/                 # Test suite
│
├── scripts/               # Utility scripts
│
└── config/                # Configuration files
```

### Key Files

* `app.py` - Application entry point
* `db.py` - Database initialization
* `setup.py` - Package configuration
* `requirements.txt` - Dependencies

## 🧪 Testing

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=championship --cov-report=html

# Run specific test file
pytest tests/test_api.py

# Run specific test
pytest tests/test_api.py::test_highest_position
```

### Writing Tests

* Place tests in the `tests/` directory
* Name test files `test_*.py`
* Name test functions `test_*`
* Use descriptive test names
* Follow AAA pattern: Arrange, Act, Assert

```python
def test_calculate_standings_single_race():
    """Test championship standings calculation for a single race."""
    # Arrange
    drivers = np.array(['VER', 'NOR', 'LEC'])
    scores = np.array([[25], [18], [15]])
    race_subset = (0,)

    # Act
    sorted_drivers, sorted_scores = calculate_standings(
        drivers, scores, race_subset
    )

    # Assert
    assert sorted_drivers[0] == 'VER'
    assert sorted_scores[0] == 25
```

## 🚀 CI/CD Pipeline

All pull requests are automatically validated by our CI pipeline.

### What CI Checks

When you submit a PR, the following checks run automatically:

| Check | Description | Must Pass |
|-------|-------------|-----------|
| **Lint** | flake8 code quality | Yes |
| **Security** | pip-audit vulnerability scan | Yes |
| **Test (3.10)** | pytest on Python 3.10 | Yes |
| **Test (3.11)** | pytest on Python 3.11 | Yes |
| **Test (3.12)** | pytest on Python 3.12 | Yes |
| **Coverage** | Minimum 30% code coverage | Yes |
| **App Validation** | Flask app starts correctly | Yes |

### Before Submitting a PR

Run these locally to catch issues early:

```bash
# 1. Run linter
flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics

# 2. Run tests with coverage
pytest tests/ -v --cov=championship --cov-fail-under=30

# 3. Verify app starts
flask run  # Should start without errors
```

### Release Process

Releases are managed by maintainers using the Release workflow:

1. Maintainer runs **Release** workflow
2. Selects version bump (patch/minor/major)
3. Workflow creates:
   - Git tag (e.g., `v1.2.3`)
   - Auto-generated changelog
   - GitHub Release

### Deployment

- **Staging**: Auto-deploys when CI passes on `main`
- **Production**: Manual deployment with version tag + confirmation

## 📚 Additional Resources

* [Flask Documentation](https://flask.palletsprojects.com/)
* [Pandas Documentation](https://pandas.pydata.org/)
* [NumPy Documentation](https://numpy.org/)
* [PEP 8 Style Guide](https://pep8.org/)
* [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html)

## 💬 Questions?

* Check existing [GitHub Issues](https://github.com/NikoKiru/F1_Season_Calculator/issues)
* Open a [Discussion](https://github.com/NikoKiru/F1_Season_Calculator/discussions)
* Contact maintainers

## 🙏 Thank You!

Your contributions make this project better for everyone. Whether it's fixing a typo or adding a major feature, every contribution is valued and appreciated!

---

**Happy Coding! 🏎️💨**
