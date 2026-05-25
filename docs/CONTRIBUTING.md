# Contributing to Industrial Data Bridge

We love your input! We want to make contributing to Industrial Data Bridge as easy and transparent as possible.

## Development Process

We use GitHub to host code, track issues and feature requests, and accept pull requests.

### 1. Fork the Repository

```bash
# Fork via GitHub UI, then:
git clone https://github.com/YOUR_USERNAME/industrial-data-bridge.git
cd industrial-data-bridge
git remote add upstream https://github.com/industrial-data-bridge/industrial-data-bridge.git
```

### 2. Set Up Development Environment

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install development dependencies
pip install -e ".[dev,ai,edge]"

# Install pre-commit hooks
pre-commit install
```

### 3. Create a Branch

```bash
git checkout -b feature/your-feature-name
# or
git checkout -b fix/issue-number-brief-description
```

Branch naming conventions:
- `feature/*` - New features
- `fix/*` - Bug fixes
- `docs/*` - Documentation changes
- `refactor/*` - Code refactoring
- `test/*` - Adding tests
- `chore/*` - Build/CI changes

### 4. Make Changes

Follow coding standards:
- Python: Follow [PEP 8](https://pep8.org/) with max line length 88 (Black default)
- Type hints: All public functions must have type annotations
- Docstrings: Google style docstrings for all public APIs
- Comments: Explain "why", not "what"

### 5. Write Tests

```bash
# Run tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test file
pytest tests/test_protocols.py -v
```

Test requirements:
- All new features must include tests
- Bug fixes should include regression tests
- Maintain test coverage above 80%
- Integration tests for protocol adapters (with mocks)

### 6. Code Quality Checks

```bash
# Format code
black src tests

# Sort imports
isort src tests

# Lint code
flake8 src tests

# Type checking
mypy src

# Run all checks
pre-commit run --all-files
```

### 7. Commit Changes

```bash
git add .
git commit -m "feat: add Modbus RTU support for Siemens S7-1200"
```

Commit message format (Conventional Commits):
```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

Types: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`, `perf`

### 8. Keep Branch Updated

```bash
git fetch upstream
git rebase upstream/main
```

### 9. Push and Create Pull Request

```bash
git push origin feature/your-feature-name
```

Then create a Pull Request on GitHub.

## Pull Request Guidelines

### PR Description Template

```markdown
## Description
Brief description of the changes.

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## How Has This Been Tested?
Describe tests you ran.

## Checklist
- [ ] My code follows the style guidelines
- [ ] I have performed a self-review
- [ ] I have added tests that prove my fix/feature works
- [ ] New and existing tests pass locally
- [ ] I have updated the documentation accordingly
```

## Architecture Guidelines

### Adding a New Protocol Adapter

1. Create `src/protocols/your_protocol_adapter.py`
2. Extend `ProtocolAdapter` base class
3. Implement required methods: `connect`, `disconnect`, `read_point`, `write_point`
4. Optional: Override `read_all_points` for batch optimization
5. Register in `BridgeEngine.PROTOCOL_MAP`
6. Add tests in `tests/test_your_protocol.py`
7. Update documentation in `docs/PROTOCOLS.md`

Example template:
```python
from .base import ProtocolAdapter

class YourProtocolAdapter(ProtocolAdapter):
    async def connect(self) -> None:
        # Implement connection logic
        pass

    async def disconnect(self) -> None:
        # Implement cleanup
        pass

    async def read_point(self, point: Dict[str, Any]) -> Any:
        # Implement point reading
        pass

    async def write_point(self, point: Dict[str, Any], value: Any) -> bool:
        # Implement point writing
        return True

    @staticmethod
    def supported_protocols() -> List[str]:
        return ["your-protocol"]
```

### Adding AI Models

1. Add model class in `src/ai/`
2. Follow interface: `train()`, `predict()`, `load_model()`, `save_model()`
3. Use `pickle` or `joblib` for sklearn models
4. Use `h5` format for TensorFlow models
5. Support both training and inference modes

## Documentation

### API Documentation
- OpenAPI/Swagger auto-generated from FastAPI routes
- Keep docstrings updated
- Add examples for complex endpoints

### Code Documentation
- Google-style docstrings
- Module-level docstrings explaining purpose
- Inline comments for complex logic

## Community

### Communication Channels
- GitHub Issues: Bug reports and feature requests
- GitHub Discussions: Questions and community support
- Email: team@industrial-data-bridge.org

### Code of Conduct

We follow the [Contributor Covenant](https://www.contributor-covenant.org/).

- Be respectful and inclusive
- Provide constructive feedback
- Focus on what is best for the community
- Show empathy towards other community members

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

## Recognition

All contributors will be recognized in:
- [CONTRIBUTORS.md](CONTRIBUTORS.md)
- Release notes for significant contributions
- Project README for core contributors