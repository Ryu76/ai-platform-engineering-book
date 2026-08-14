# 실행 위치: 저장소 루트의 Anaconda PowerShell Prompt
# 사전 조건: conda activate ai-platform-engineering-book
$ErrorActionPreference = "Stop"

if ($env:CONDA_DEFAULT_ENV -ne "ai-platform-engineering-book") {
    throw "먼저 'conda activate ai-platform-engineering-book'를 실행하세요."
}

ruff check .
mypy src
python scripts/validate_docs.py
python scripts/validate_links.py
python scripts/validate_code_blocks.py
python scripts/check_secrets.py
pytest -q
