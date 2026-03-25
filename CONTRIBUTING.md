# Contributing

Thank you for your interest in contributing!

## Development Setup

```bash
git clone https://github.com/QuartzUnit/browsegrab.git
cd browsegrab
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

## Running Tests

```bash
pytest tests/ -v
```

## How to Contribute

1. **Bug reports** — Open an issue with reproduction steps
2. **Feature requests** — Open an issue describing the use case
3. **Pull requests** — Fork, create a branch, make changes, run tests, submit PR

## Pull Request Guidelines

- Include tests for new functionality
- Run `ruff check` before submitting
- Keep commits focused and atomic
- Update CHANGELOG.md under `## [Unreleased]`

## Code Style

- Python 3.11+
- Type hints required
- Line length: 120
- Linter: ruff

## License

By contributing, you agree that your contributions will be licensed under the same license as the project.
