# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.5.0] - 2025-08-03

### Added
- **Modern Project Structure**: Migrated from `setup.py` to `pyproject.toml` configuration
- **setuptools_scm**: Automatic version management from git tags
- **Development Tools**: Integrated Ruff for linting and formatting
- **Type Annotations**: Complete type hints throughout the codebase for better developer experience
- **Comprehensive Testing**: Enhanced unittest coverage with comprehensive test cases for all major components

### Changed
- **Pre-commit Configuration**: Enhanced pre-commit hooks with updated tools and better code quality checks
- **CI/CD Pipeline**: Improved GitHub Actions workflow
- **Minimum Python Version**: Upgraded from Python 3.6+ to Python 3.10+
- **Package Metadata**: Enhanced PyPI package information with proper classifiers
- **Dependencies**: Updated BeautifulSoup4 to 4.12.0+, added lxml 4.9.0+ for faster parsing
- **Error Handling**: Improved with custom `EksiError` exception class and better user feedback
- **Entry Parsing**: Optimized entry display logic and text wrapping for better readability

### Fixed
- **Error Recovery**: Improved error handling for network timeouts and HTTP errors

### Removed
- **Python < 3.10**: Dropped support for Python versions below 3.10
- **setup.py**: Removed in favor of modern pyproject.toml configuration
- **Deprecated Code**: Cleaned up legacy code patterns and unused dependencies

[0.5.0]: https://github.com/furkanonder/eksigundem/releases/tag/v0.5.0
