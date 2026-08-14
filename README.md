# AI Platform Engineering Bootcamp

> Hermes · Codex · RAG · Multi-Agent · Router · LangGraph · Kubernetes 기반 AI 플랫폼 개발 실무

## 프로젝트 소개
LLM 입문자가 하나의 AI 업무 처리 플랫폼을 단계적으로 확장하며 학습하는 한국어 실무 교재입니다.

## 대상 독자
Python, Git, Docker의 기초를 가진 백엔드·인프라 개발자입니다. Python 실습의 공식 환경은 **Windows Anaconda Distribution + Conda**이며, Docker·Kubernetes 명령에만 WSL을 사용합니다.

## 학습 목표
LLM API 호출에서 시작해 Prompt, Tool Calling, MCP, Embedding, RAG, Reranker, Multi-Agent, Router, LangGraph, Evaluation, Docker, Kubernetes를 연결합니다.

## 전체 커리큘럼
1. [LLM 기초](docs/volume01-llm-fundamentals/README.md)
2. [Prompt Engineering](docs/volume02-prompt-engineering/README.md)
3. [Tool Calling & MCP](docs/volume03-tool-calling-mcp/README.md)
4. [Embedding & Vector Database](docs/volume04-embedding-vector-db/README.md)
5. [RAG](docs/volume05-rag/README.md)
6. [Reranker](docs/volume06-reranker/README.md)
7. [Multi-Agent](docs/volume07-multi-agent/README.md)
8. [Router](docs/volume08-router/README.md)
9. [LangGraph](docs/volume09-langgraph/README.md)
10. [Evaluation](docs/volume10-evaluation/README.md)
11. [Kubernetes 기반 AI 운영](docs/volume11-kubernetes-ai-platform/README.md)

## 빠른 시작
```powershell
# 실행 위치: 저장소 루트의 Anaconda PowerShell Prompt
conda env create --file environment.yml
conda activate ai-platform-engineering-book
pytest -q
ruff check .
mypy src
```

처음 시작할 때는 [Anaconda 환경 설정](docs/setup/anaconda.md)을 완료한 뒤 [Volume 01 학습 경로](docs/volume01-llm-fundamentals/01-learning-objectives.md)부터 진행합니다.

## 보안
실제 API 키, 회사 문서, 개인정보는 저장소에 넣지 않습니다. 위험한 Tool 실행·삭제·배포는 항상 사용자 승인을 받아야 합니다.
