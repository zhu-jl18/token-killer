# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2025-10-30

### Added
- Initial release of Token Killer
- FastAPI-based server with OpenAI-compatible API
- Triple-thread parallel thinking architecture
- Adversarial validation with counterexample generation
- Intelligent thread fusion with KAT-Coder-72B
- Smart context management with dynamic summarization
- Streaming response support (SSE)
- Comprehensive configuration system (YAML + environment variables)
- Externalized prompt templates
- Structured logging with structlog
- HTTP retry logic with exponential backoff
- Health check endpoint
- Automatic API documentation (Swagger UI)
- Complete test suite

### Models Supported
- Main Thinker: 万清模型2
- Fusion: KAT-Coder-Exp-72B-1010
- Summarizer: Qwen/Qwen2-7B-Instruct
- Counterexample: Qwen/Qwen2.5-7B-Instruct
- Validator: THUDM/GLM-4-9B-0414

### Documentation
- Comprehensive README with Linus-style honesty
- Architecture documentation
- Contributing guidelines
- Example scripts and tests

### Credits
- Original concept: 群友 "综"
- Refactoring from Flask to FastAPI

## [Unreleased]

### Planned
- Request caching
- Cost tracking dashboard
- Multi-language prompt support
- A/B testing framework
- Performance benchmarks

---

## Version History

### Version Numbering

- **Major**: Breaking changes, complete rewrites
- **Minor**: New features, backward compatible
- **Patch**: Bug fixes, documentation updates

### Support

- Latest version: Full support
- Previous major: Security fixes only
- Older versions: No support

---

*"Release early, release often."* — Linus Torvalds
