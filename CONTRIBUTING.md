# Contributing to Relay

Thank you for your interest in contributing to Relay! We welcome contributions from developers, AI researchers, and systems engineers.

---

## 1. Development Workflow

1. Fork the repository and create your branch from `main`.
2. Install development dependencies:
   ```bash
   pip install -e .[dev]
   ```
3. Ensure all pytest unit tests pass:
   ```bash
   python3 -m pytest tests/ -v
   ```
4. Run code quality linters before submitting a pull request:
   ```bash
   black relay/ tests/
   flake8 relay/ tests/
   mypy relay/
   ```

---

## 2. Pull Request Submission Checklist

- [ ] Code follows project formatting standards (`black`).
- [ ] New features include corresponding unit tests in `tests/`.
- [ ] All 31+ unit tests pass cleanly (`pytest tests/`).
- [ ] All 3 demonstration scripts execute successfully (`scripts/demo_*.py`).
- [ ] Documentation is updated in `docs/` if modifying core abstractions.
