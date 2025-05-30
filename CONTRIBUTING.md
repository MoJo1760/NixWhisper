# Contributing to NixWhisper

Thank you for your interest in contributing to NixWhisper! We welcome contributions from the community to help improve this project.

## Getting Started

1. Fork the repository on GitHub
2. Clone your fork locally
3. Create a new branch for your changes
4. Make your changes and commit them with clear, descriptive messages
5. Push your changes to your fork
6. Open a pull request against the main branch

## Development Setup

1. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. Install development dependencies:
   ```bash
   pip install -e ".[dev]"
   ```

3. Install pre-commit hooks:
   ```bash
   pre-commit install
   ```

## Code Style

- Follow [PEP 8](https://www.python.org/dev/peps/pep-0008/) for Python code
- Use type hints for all function signatures
- Keep lines under 88 characters (Black's default)
- Document all public functions and classes with docstrings
- Write unit tests for new functionality

## Testing

Run the test suite with:

```bash
pytest
```

## Pull Request Guidelines

- Keep pull requests focused on a single feature or bug fix
- Update documentation as needed
- Ensure all tests pass
- Add new tests for new features
- Update the CHANGELOG.md with your changes

## Reporting Issues

When reporting issues, please include:

- A clear description of the issue
- Steps to reproduce the issue
- Expected behavior
- Actual behavior
- System information (OS, Python version, etc.)
- Any relevant error messages or logs

## Code of Conduct

Please note that this project is released with a Contributor Code of Conduct. By participating in this project you agree to abide by its terms.

## License

By contributing to NixWhisper, you agree that your contributions will be licensed under its MIT License.
