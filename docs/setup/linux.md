# Linux 환경 설정

이 교본의 공식 Python 실습 환경은 Anaconda의 Conda 환경입니다. Linux에서 학습한다면 Anaconda Distribution을 설치한 뒤 터미널을 새로 열어 `conda`가 인식되는지 확인합니다.

```bash
# 실행 위치: Linux 터미널, Anaconda 초기화 뒤
conda --version
cd ~/projects/ai-platform-engineering-book
conda env create --file environment.yml
conda activate ai-platform-engineering-book
python --version
```

`python --version`은 3.12 계열이어야 합니다. 이후 모든 예제·테스트·정적 검사는 이 활성 환경에서 `python`, `pytest`, `ruff`, `mypy`로 실행합니다. `uv`, 별도 `venv`, 시스템 Python을 섞지 않습니다.

Windows 학습자는 이 문서 대신 [Windows 준비](windows.md)와 [Anaconda 환경 설정](anaconda.md)을 사용합니다.
