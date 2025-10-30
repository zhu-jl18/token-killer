# Contributing Guidelines

## Philosophy

We follow Linus Torvalds' philosophy: **show me the code, not your ego**.

Good contributions are:
- ✅ Well-tested
- ✅ Clearly documented
- ✅ Focused on real problems
- ✅ Following existing patterns

Bad contributions are:
- ❌ "Fixed stuff" commits
- ❌ Untested code
- ❌ Breaking changes without discussion
- ❌ Overengineered solutions

## Before You Start

1. **Check existing issues** - Don't duplicate work
2. **Open an issue first** - Discuss big changes
3. **Read the code** - Understand the architecture
4. **Run tests** - Make sure everything works

## Development Setup

```bash
# Clone
git clone https://github.com/zhu-jl18/token-killer.git
cd token-killer

# Virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1  # Windows
source venv/bin/activate     # Linux/Mac

# Install dev dependencies
pip install -r requirements.txt
pip install pytest black ruff

# Verify setup
python validate.py
```

## Making Changes

### 1. Code Style

**Use Black for formatting**:
```bash
black app/ tests/
```

**Use Ruff for linting**:
```bash
ruff check app/ tests/
```

**Key rules**:
- Max line length: 100 characters
- Type hints required for public APIs
- Docstrings for modules and complex functions
- No commented-out code

### 2. Commit Messages

**Good**:
```
Add retry logic to HTTP client

- Implement exponential backoff with tenacity
- Add max 3 retry attempts
- Log retry attempts for debugging
```

**Bad**:
```
fixed stuff
```

**Format**:
```
<type>: <subject>

<body>

<footer>
```

**Types**: feat, fix, docs, style, refactor, test, chore

### 3. Branch Naming

```
feat/add-caching
fix/validation-timeout
docs/update-readme
```

### 4. Testing

**Write tests for**:
- New features
- Bug fixes
- Edge cases

**Run tests**:
```bash
pytest tests/
```

**Test structure**:
```python
def test_feature_name():
    """Test that feature does X when Y."""
    # Arrange
    input_data = ...
    
    # Act
    result = function_under_test(input_data)
    
    # Assert
    assert result == expected
```

## Pull Request Process

### 1. Before Submitting

- [ ] Code formatted with Black
- [ ] No linting errors (Ruff)
- [ ] Tests pass
- [ ] Documentation updated
- [ ] Commit messages clear

### 2. PR Description

**Template**:
```markdown
## What

Brief description of changes

## Why

Problem being solved or feature being added

## How

Technical approach

## Testing

How you tested the changes

## Checklist

- [ ] Tests pass
- [ ] Docs updated
- [ ] Breaking changes documented
```

### 3. Review Process

- Expect honest feedback
- No personal attacks, but code will be criticized
- "This is garbage" with reasoning is valid feedback
- Fix issues, don't argue about style

### 4. Merging

- Squash commits if messy
- Clean commit history
- Update CHANGELOG.md

## Areas for Contribution

### High Priority

- [ ] Comprehensive test coverage
- [ ] Performance benchmarks
- [ ] Cost tracking/analytics
- [ ] Request queuing
- [ ] Better error messages

### Medium Priority

- [ ] Caching layer
- [ ] Multi-language support
- [ ] Prompt versioning
- [ ] A/B testing framework

### Low Priority

- [ ] Web UI
- [ ] CLI tool
- [ ] Docker support
- [ ] Kubernetes manifests

## Bug Reports

**Good bug report**:
```markdown
## Description
Streaming response cuts off after 1000 characters

## Steps to Reproduce
1. Send request with stream=true
2. Question: "Write a long essay"
3. Observe truncation

## Expected
Full response streamed

## Actual
Cuts off at ~1000 chars

## Environment
- OS: Windows 11
- Python: 3.11
- Version: v1.0.0

## Logs
```
[paste relevant logs]
```
```

**Bad bug report**:
```
Doesn't work
```

## Feature Requests

**Template**:
```markdown
## Problem
[What problem does this solve?]

## Proposed Solution
[How would you solve it?]

## Alternatives Considered
[What other options did you think about?]

## Impact
[Who benefits? How much work is it?]
```

## Code of Conduct

**Do**:
- Be respectful
- Focus on the code, not the person
- Accept criticism gracefully
- Help newcomers

**Don't**:
- Make personal attacks
- Discriminate
- Harass
- Spam

**Enforcement**:
- First offense: Warning
- Second offense: Temp ban
- Third offense: Permanent ban

## Questions?

- Open an issue with "question" label
- Check existing issues first
- Be specific

---

**Remember**: Good code speaks for itself. Make your code so clean, so obvious, so well-tested that it needs no defense.
