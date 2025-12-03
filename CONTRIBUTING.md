# Contributing to Docker MCP Orchestrator

Thank you for your interest in contributing! 🎉

## How to Contribute

### Reporting Bugs

1. Check if the bug already exists in [Issues](https://github.com/semenovsd/docker-mcp-orchestrator/issues)
2. If not, create a new issue with:
   - Clear title
   - Steps to reproduce
   - Expected vs actual behavior
   - Environment details (OS, Python version, Cursor version)

### Suggesting Features

1. Open an issue with `[Feature]` prefix
2. Describe the use case and proposed solution
3. Discuss with maintainers before implementation

### Pull Requests

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Make your changes
4. Run tests: `pytest`
5. Run linter: `ruff check .`
6. Commit with clear message
7. Push and create PR

### Code Style

- Follow PEP 8
- Use type hints
- Write docstrings for public functions
- Keep functions focused and small

### Adding New MCP Servers

To add support for new Docker MCP Toolkit servers:

1. Add entry to `MCP_SERVER_REGISTRY` in `src/mcp_orchestrator/server.py`
2. Include:
   - Accurate description
   - Tool summary
   - Correct category
   - Auth requirements
   - Estimated tool count

### Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src/mcp_orchestrator

# Run specific test
pytest tests/test_orchestrator.py::TestServerRegistry
```

## Development Setup

```bash
# Clone
git clone https://github.com/semenovsd/docker-mcp-orchestrator.git
cd docker-mcp-orchestrator

# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest
```

## License

By contributing, you agree that your contributions will be licensed under CC BY-NC 4.0.

## Questions?

Open an issue or contact the maintainer.
