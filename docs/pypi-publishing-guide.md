# PyPI Publishing Guide for VAPI Manager

## Prerequisites

1. **Create PyPI Account**
   - Production: https://pypi.org/account/register/
   - Test: https://test.pypi.org/account/register/

2. **Generate API Tokens**
   - PyPI: https://pypi.org/manage/account/token/
   - TestPyPI: https://test.pypi.org/manage/account/token/

3. **Install Publishing Tools**
   ```bash
   pip install twine
   ```

## Configuration

### 1. Configure Poetry with API Tokens

```bash
# For TestPyPI
poetry config repositories.testpypi https://test.pypi.org/legacy/
poetry config pypi-token.testpypi pypi-YOUR_TEST_TOKEN_HERE

# For PyPI
poetry config pypi-token.pypi pypi-YOUR_PRODUCTION_TOKEN_HERE
```

### 2. Alternative: Use .pypirc File

Create `~/.pypirc`:
```ini
[distutils]
index-servers =
    pypi
    testpypi

[pypi]
repository = https://upload.pypi.org/legacy/
username = __token__
password = pypi-YOUR_API_TOKEN_HERE

[testpypi]
repository = https://test.pypi.org/legacy/
username = __token__
password = pypi-YOUR_TEST_API_TOKEN_HERE
```

## Publishing Process

### Step 1: Update Version

Edit `vapi_manager/__version__.py`:
```python
__version__ = "1.0.0"  # Update this
```

Edit `pyproject.toml`:
```toml
version = "1.0.0"  # Update this
```

### Step 2: Update CHANGELOG

Add release notes to `CHANGELOG.md`:
```markdown
## [1.0.0] - 2024-01-25
### Added
- New features...
### Fixed
- Bug fixes...
```

### Step 3: Build Package

```bash
# Clean previous builds
rm -rf dist/ build/ *.egg-info

# Build new package
poetry build
```

### Step 4: Check Package

```bash
# Check with twine
twine check dist/*

# Check package contents
tar -tzf dist/vapi-manager-*.tar.gz | head -20
```

### Step 5: Test on TestPyPI

```bash
# Publish to TestPyPI
poetry publish -r testpypi

# Or use the publish script
python publish.py --test
```

### Step 6: Test Installation from TestPyPI

```bash
# Create test environment
python -m venv test-env
source test-env/bin/activate  # On Windows: test-env\Scripts\activate

# Install from TestPyPI
pip install -i https://test.pypi.org/simple/ vapi-manager

# Test the package
vapi-manager --version
vapi-manager --help
```

### Step 7: Publish to PyPI

```bash
# Publish to production PyPI
poetry publish

# Or use the publish script
python publish.py
```

### Step 8: Verify Installation

```bash
# Install from PyPI
pip install vapi-manager

# Verify
vapi-manager --version
```

## Automated Publishing with GitHub Actions

Create `.github/workflows/publish.yml`:

```yaml
name: Publish to PyPI

on:
  release:
    types: [published]

jobs:
  publish:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3

    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'

    - name: Install Poetry
      run: |
        curl -sSL https://install.python-poetry.org | python3 -
        echo "$HOME/.local/bin" >> $GITHUB_PATH

    - name: Build package
      run: poetry build

    - name: Publish to PyPI
      env:
        POETRY_PYPI_TOKEN_PYPI: ${{ secrets.PYPI_API_TOKEN }}
      run: poetry publish
```

## Version Management

### Semantic Versioning

Follow [Semantic Versioning](https://semver.org/):
- **MAJOR**: Breaking changes
- **MINOR**: New features (backward compatible)
- **PATCH**: Bug fixes (backward compatible)

### Version Bump Script

```bash
# Patch version (1.0.0 -> 1.0.1)
poetry version patch

# Minor version (1.0.0 -> 1.1.0)
poetry version minor

# Major version (1.0.0 -> 2.0.0)
poetry version major
```

## Testing Checklist

Before publishing, ensure:

- [ ] All tests pass: `pytest`
- [ ] Code is formatted: `black vapi_manager`
- [ ] Linting passes: `ruff check vapi_manager`
- [ ] Documentation is updated
- [ ] CHANGELOG is updated
- [ ] Version number is updated
- [ ] Package builds successfully
- [ ] TestPyPI installation works
- [ ] All CLI commands work

## Common Issues and Solutions

### 1. Authentication Error

**Problem**: "Invalid or non-existent authentication"

**Solution**:
```bash
poetry config pypi-token.pypi pypi-YOUR_TOKEN_HERE
```

### 2. Version Already Exists

**Problem**: "File already exists"

**Solution**: Increment version number in `__version__.py` and `pyproject.toml`

### 3. Missing Files in Package

**Problem**: Templates or data files missing

**Solution**: Update `MANIFEST.in` to include required files

### 4. Import Errors After Installation

**Problem**: Module import errors

**Solution**: Ensure all dependencies are in `pyproject.toml`

## Post-Publishing Tasks

1. **Create GitHub Release**
   ```bash
   git tag v1.0.0
   git push origin v1.0.0
   ```

2. **Update Documentation**
   - Update installation instructions
   - Update README badges
   - Update docs site

3. **Announce Release**
   - GitHub Discussions
   - Discord/Slack
   - Social media

4. **Monitor Issues**
   - Watch for installation issues
   - Monitor PyPI download stats
   - Respond to user feedback

## Useful Commands

```bash
# View package info
pip show vapi-manager

# Check available versions
pip index versions vapi-manager

# Download stats
# Visit: https://pepy.tech/project/vapi-manager

# Package page
# Visit: https://pypi.org/project/vapi-manager/
```

## Security Considerations

1. **Never commit tokens** to version control
2. **Use API tokens** instead of passwords
3. **Scope tokens** appropriately
4. **Rotate tokens** regularly
5. **Use 2FA** on PyPI account

## Support

For publishing issues:
- PyPI Support: https://pypi.org/help/
- Poetry Docs: https://python-poetry.org/docs/
- GitHub Issues: https://github.com/vapi-ai/vapi-manager/issues