# Repository Guidelines

## Project Structure & Module Organization
The working code lives in `ACE-Step-1.5/`; the repository root is mostly a wrapper. Do day-to-day development from `ACE-Step-1.5`.

- `ACE-Step-1.5/acestep/`: core package (API, inference, UI, training)
- `ACE-Step-1.5/tests/`: top-level unit tests
- `ACE-Step-1.5/docs/`: multilingual documentation
- `ACE-Step-1.5/scripts/` and `start_*.sh|.bat`: utility and launch scripts
- `ACE-Step-1.5/examples/`: JSON examples for generation modes

## Build, Test, and Development Commands
Use `uv` for environment and runtime management.

- `cd ACE-Step-1.5 && uv sync`: install/sync dependencies
- `cd ACE-Step-1.5 && uv run acestep`: start Gradio UI (`127.0.0.1:7860`)
- `cd ACE-Step-1.5 && uv run acestep-api`: start API server
- `cd ACE-Step-1.5 && python -m unittest discover -s tests -p "test_*.py"`: run root tests
- `cd ACE-Step-1.5 && python -m unittest discover -s acestep -p "*_test.py"`: run colocated module tests
- `cd ACE-Step-1.5 && ./quick_test.sh`: quick environment check (Linux/macOS)

## Coding Style & Naming Conventions
Follow `.editorconfig`: UTF-8, LF, final newline, trimmed trailing whitespace (Windows script files use CRLF). Python uses 4-space indentation and clear, small functions. Use `snake_case` for variables/functions/files and `PascalCase` for classes. Test files should be named `test_*.py` or `*_test.py`.

## Testing Guidelines
The project primarily uses `unittest`. For each behavior change, include at least one success-path test and one regression/edge-case test. Isolate GPU, filesystem, and external service dependencies with `unittest.mock` to keep tests deterministic and fast. Before opening a PR, run focused tests for changed modules.

## Commit & Pull Request Guidelines
Recent history favors Conventional Commit prefixes (`fix:`, `feat:`) and topic branches like `fix/...` or `feat/...`. Keep each PR scoped to one issue and avoid unrelated refactors. In the PR description, include:

- summary of the change
- explicit out-of-scope items
- non-target platform impact (CPU/CUDA/MPS/XPU)
- validation commands and results

## Security & Configuration Tips
Never commit secrets or local credentials. When adding configuration, update template files such as `.env.example` and `proxy_config.txt.example`, and inject real values through local environment variables.
