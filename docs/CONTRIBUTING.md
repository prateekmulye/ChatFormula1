# 🤝 Contributing Guide

Thank you for considering contributing to ChatFormula1 Agent! This guide will help you get started.

---

## Code of Conduct

- Be respectful and inclusive
- Provide constructive feedback
- Focus on what is best for the community
- Show empathy towards other contributors

---

## How to Contribute

### Reporting Bugs

1. **Check existing issues** to avoid duplicates
2. **Use the bug report template**
3. **Include**:
   - Clear description of the bug
   - Steps to reproduce
   - Expected vs actual behavior
   - Environment details (OS, Python version, etc.)
   - Relevant logs or screenshots

### Suggesting Features

1. **Check existing feature requests**
2. **Use the feature request template**
3. **Include**:
   - Clear description of the feature
   - Use case and benefits
   - Possible implementation approach
   - Any relevant examples

### Submitting Pull Requests

1. **Fork the repository**
2. **Create a feature branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```
3. **Make your changes**
4. **Write tests** for new functionality
5. **Ensure all tests pass**
   ```bash
   make test
   ```
6. **Format and lint your code**
   ```bash
   cd agent
   poetry run black src ingestion tests
   poetry run ruff check src ingestion tests
   ```
7. **Commit with clear messages**
   ```bash
   git commit -m "Add: Brief description of changes"
   ```
8. **Push to your fork**
   ```bash
   git push origin feature/your-feature-name
   ```
9. **Open a Pull Request**

---

## Development Setup

### 1. Fork and Clone

```bash
# Fork on GitHub, then:
git clone https://github.com/YOUR_USERNAME/chatformula1.git
cd chatformula1

# Add upstream remote
git remote add upstream https://github.com/ORIGINAL_OWNER/chatformula1.git
```

### 2. Install Dependencies

```bash
# Install all apps (only agent/ is implemented in Phase 1)
make setup

# Or directly:
cd agent && poetry install

# Install pre-commit hooks (from the repo root)
pre-commit install
```

### 3. Create Branch

```bash
# Update main
git checkout main
git pull upstream main

# Create feature branch
git checkout -b feature/your-feature-name
```

---

## Coding Standards

### Python Style Guide

- Follow **PEP 8** style guide
- Use **type hints** for all functions
- Write **docstrings** for modules, classes, and functions
- Keep functions **small and focused**
- Use **meaningful variable names**

### Code Formatting

```bash
cd agent

# Format with Black (line length: 88)
poetry run black src ingestion tests

# Lint with Ruff
poetry run ruff check src ingestion tests

# Type check with mypy
poetry run mypy src ingestion
```

### Example Code Style

```python
from typing import List, Optional

def process_race_data(
    race_id: str,
    drivers: List[str],
    include_weather: bool = False
) -> Optional[dict]:
    """
    Process race data and return structured results.
    
    Args:
        race_id: Unique identifier for the race
        drivers: List of driver codes (e.g., ['VER', 'HAM'])
        include_weather: Whether to include weather data
        
    Returns:
        Dictionary with processed race data, or None if processing fails
        
    Raises:
        ValueError: If race_id is invalid
    """
    if not race_id:
        raise ValueError("race_id cannot be empty")
    
    # Implementation here
    return result
```

---

## Testing

### Writing Tests

- Write tests for **all new features**
- Maintain **80%+ code coverage**
- Use **pytest** for testing
- Follow **AAA pattern** (Arrange, Act, Assert)

### Test Structure

```python
import pytest

from chatf1_agent.guards import scan_for_prompt_injection


@pytest.mark.unit
def test_clean_query_passes_guard():
    """A normal F1 question is not flagged."""
    # Arrange
    query = "Who won the 2023 championship?"

    # Act
    verdict = scan_for_prompt_injection(query)

    # Assert
    assert verdict.flagged is False
    assert verdict.matched_pattern is None
```

### Running Tests

Tests run with dummy credentials — no API keys required.

```bash
cd agent

# Run all tests
poetry run pytest

# Run with coverage
poetry run pytest --cov

# Run specific test file
poetry run pytest tests/test_streaming_contract.py

# Run by marker
poetry run pytest -m unit
poetry run pytest -m integration   # needs real keys; skips otherwise
```

---

## Commit Messages

### Format

```
Type: Brief description (50 chars or less)

More detailed explanation if needed (wrap at 72 chars).
Include motivation for the change and contrast with previous behavior.

- Bullet points are okay
- Use present tense: "Add feature" not "Added feature"
- Reference issues: "Fixes #123" or "Relates to #456"
```

### Types

- **Add**: New feature or functionality
- **Fix**: Bug fix
- **Update**: Update existing functionality
- **Remove**: Remove code or files
- **Refactor**: Code refactoring
- **Docs**: Documentation changes
- **Test**: Add or update tests
- **Style**: Code style changes (formatting, etc.)
- **Chore**: Maintenance tasks

### Examples

```bash
# Good
git commit -m "Add: Vector search caching for improved performance"
git commit -m "Fix: Rate limiter not resetting daily counters"
git commit -m "Update: Improve error messages for API failures"

# Bad
git commit -m "fixed stuff"
git commit -m "WIP"
git commit -m "asdfasdf"
```

---

## Pull Request Process

### Before Submitting

- [ ] All tests pass
- [ ] Code is formatted and linted
- [ ] Documentation is updated
- [ ] CHANGELOG is updated (if applicable)
- [ ] Commit messages are clear
- [ ] Branch is up to date with main

### PR Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
- [ ] Unit tests added/updated
- [ ] Integration tests added/updated
- [ ] Manual testing completed

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Comments added for complex code
- [ ] Documentation updated
- [ ] No new warnings generated
- [ ] Tests pass locally
```

### Review Process

1. **Automated checks** run (tests, linting)
2. **Maintainer review** (usually within 48 hours)
3. **Address feedback** if requested
4. **Approval and merge** by maintainer

---

## Project Structure

```
chatformula1/
├── agent/                    # Python LangGraph inference service
│   ├── src/chatf1_agent/    # Pipeline, retrieval, guards, NDJSON server
│   ├── ingestion/           # Offline ingestion CLI
│   └── tests/               # Test suite (incl. streaming contract tests)
├── gateway/                  # Phoenix GraphQL gateway (Phase 2)
├── web/                      # React frontend (Phase 4)
├── data/                     # F1 datasets (seeds + ingestion input)
└── docs/                     # Architecture, roadmap, streaming protocol
```

---

## Areas for Contribution

### High Priority

- [ ] Add more F1 data sources
- [ ] Improve response accuracy
- [ ] Add more test coverage
- [ ] Performance optimizations
- [ ] Better error handling

### Medium Priority

- [ ] Add voice interface
- [ ] Multi-language support
- [ ] Advanced analytics
- [ ] Mobile app
- [ ] Real-time race updates

### Documentation

- [ ] API documentation
- [ ] Architecture diagrams
- [ ] Tutorial videos
- [ ] Example use cases
- [ ] FAQ section

---

## Getting Help

- **Questions**: Open a GitHub Discussion
- **Bugs**: Open a GitHub Issue
- **Chat**: Join our Discord (if available)
- **Email**: Contact maintainers

---

## Recognition

Contributors will be:
- Listed in CONTRIBUTORS.md
- Mentioned in release notes
- Credited in documentation

---

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

---

**Thank you for contributing! 🏎️**
