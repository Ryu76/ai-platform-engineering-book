# AI Platform Engineering 실무 교재 제작 프로젝트 PRD

> 문서 버전: v1.0  
> 문서 유형: Codex 실행용 프로젝트 요구사항 정의서  
> 기본 언어: 한국어  
> 대상 실행 도구: OpenAI Codex CLI  
> 프로젝트 형태: 장기 문서 제작 + 실습 코드 구축 + 검증 자동화  
> 최종 목표: LLM 입문자가 AI Platform Engineer 수준까지 성장할 수 있는 실무형 교재 제작

---

# 1. 프로젝트 개요

## 1.1 프로젝트명

**AI Platform Engineering Bootcamp**

부제:

**Hermes · Codex · RAG · Multi-Agent · Router · LangGraph · Kubernetes 기반 AI 플랫폼 개발 실무**

## 1.2 프로젝트 배경

학습자는 현재 다음 경험을 보유하고 있다.

- Windows 환경 사용
- Linux 및 WSL 기본 사용
- Python 개발 경험
- Git 사용 경험
- Docker 사용 경험
- Hermes 설치 및 실행 경험
- Codex CLI 연동 경험
- Hermes와 Codex를 이용한 Harness Engineering 경험
- LLM 이론, RAG, Router, LangGraph 등은 처음 학습하는 단계

기존 LLM 관련 자료는 다음 문제가 있다.

- 개념 설명만 있고 실습이 부족하다.
- 설치 및 환경 구성 과정이 생략되어 있다.
- 서로 독립된 예제가 많아 전체 구조를 이해하기 어렵다.
- RAG, Multi-Agent, Router, LangGraph, Kubernetes가 각각 분리되어 설명된다.
- 실제 운영 환경에서 필요한 오류 처리, 로깅, 평가, 보안, 배포 내용이 부족하다.
- Hermes 및 Codex를 이미 사용하는 개발자 관점의 연결 설명이 부족하다.

본 프로젝트는 위 문제를 해결하기 위해, 하나의 AI 플랫폼 프로젝트를 단계적으로 확장하면서 학습하는 실무형 교재를 제작한다.

---

# 2. 프로젝트 목표

## 2.1 최종 목표

LLM을 처음 배우는 개발자가 다음 기술을 이해하고 직접 구현할 수 있도록 한다.

- LLM 기본 원리
- Token과 Context Window
- Prompt Engineering
- Function Calling
- Tool Calling
- MCP
- Embedding
- Vector Database
- RAG
- Chunking
- Retrieval
- Reranker
- Multi-Agent
- Agent Router
- LangGraph
- Evaluation
- Observability
- Docker
- Kubernetes
- AI Platform Architecture

## 2.2 학습 완료 후 기대 수준

학습자는 교재를 모두 완료한 뒤 다음 작업을 독립적으로 수행할 수 있어야 한다.

1. LLM API를 안전하게 호출한다.
2. 목적에 맞는 Prompt를 설계한다.
3. LLM이 외부 도구를 호출하도록 구현한다.
4. MCP Server와 MCP Client의 역할을 설명하고 구현한다.
5. 문서를 Embedding하고 Vector DB에 저장한다.
6. 사내 문서를 검색하는 RAG 시스템을 구축한다.
7. Reranker를 적용해 검색 품질을 개선한다.
8. 역할별 Multi-Agent 시스템을 설계한다.
9. 요청에 맞는 Agent를 선택하는 Router를 구현한다.
10. LangGraph 기반 상태형 Workflow를 구축한다.
11. 응답 품질, 검색 품질, 라우팅 품질을 평가한다.
12. Docker로 서비스를 컨테이너화한다.
13. Kubernetes에 AI 서비스를 배포한다.
14. 전체 AI Platform을 설계, 구현, 테스트, 배포한다.

---

# 3. 프로젝트 범위

## 3.1 포함 범위

- 전체 교재 목차 설계
- 권별 학습 목표 정의
- 장별 이론 설명 작성
- 환경 구축 문서 작성
- 실습 코드 작성
- 예제 데이터 작성
- 테스트 코드 작성
- 오류 해결 문서 작성
- 과제 및 미니 프로젝트 작성
- 최종 통합 프로젝트 구축
- Docker 구성
- Kubernetes Manifest 작성
- 학습 진도 체크리스트 작성
- 자동 검증 스크립트 작성
- 문서 링크 및 목차 구성

## 3.2 제외 범위

- 특정 유료 LLM API의 결제를 강제하지 않는다.
- 실제 회사의 비공개 데이터를 사용하지 않는다.
- 운영 서버에 자동 배포하지 않는다.
- 사용자 승인 없이 외부 서비스에 데이터를 전송하지 않는다.
- 실습 목적을 벗어난 인프라 비용을 발생시키지 않는다.
- 특정 클라우드 사업자에 종속된 구조만 제공하지 않는다.

---

# 4. 대상 독자

## 4.1 기본 대상

- LLM을 처음 배우는 개발자
- Python 개발자
- 백엔드 개발자
- 시스템 엔지니어
- DevOps 엔지니어
- 인프라 엔지니어
- AI Agent 개발에 관심 있는 개발자

## 4.2 선수 지식

필수:

- 변수, 조건문, 반복문, 함수 등 Python 기본 문법
- 터미널 명령어 기본 사용
- Git 기본 사용
- Docker 기본 개념

권장:

- REST API 기본 이해
- JSON 형식 이해
- Linux 파일 및 프로세스 기본 이해
- 비동기 처리 기본 개념

필수가 아닌 항목:

- 머신러닝 수학
- 딥러닝 학습 경험
- Transformer 구현 경험
- GPU 운영 경험
- Kubernetes 운영 경험

---

# 5. 핵심 학습 철학

## 5.1 쉬운 설명

모든 개념은 다음 순서로 설명한다.

1. 왜 필요한가
2. 기존 방식의 문제는 무엇인가
3. 새로운 기술이 무엇을 해결하는가
4. 내부적으로 어떻게 동작하는가
5. 실제로 어떻게 구현하는가
6. 실무에서 무엇을 주의해야 하는가

## 5.2 실습 중심

각 개념은 반드시 실행 가능한 실습으로 연결한다.

잘못된 예:

```text
Embedding은 문장을 벡터로 바꾸는 기술이다.
```

올바른 예:

```text
1. Embedding 개념 설명
2. Python 환경 구성
3. 문장을 Embedding으로 변환
4. 벡터 길이 확인
5. 유사도 계산
6. 서로 다른 문장의 유사도 비교
7. 결과 해석
8. Vector DB에 저장
```

## 5.3 프로젝트 연속성

모든 권은 독립 예제를 반복하지 않고 하나의 프로젝트를 계속 확장한다.

```text
단순 LLM 호출
    ↓
Prompt 개선
    ↓
Tool Calling
    ↓
MCP 연결
    ↓
Embedding
    ↓
Vector DB
    ↓
RAG
    ↓
Reranker
    ↓
Multi-Agent
    ↓
Router
    ↓
LangGraph
    ↓
Evaluation
    ↓
Docker
    ↓
Kubernetes
    ↓
운영 가능한 AI Platform
```

## 5.4 초보자 기준

다음 내용을 생략하지 않는다.

- 명령어를 어디에서 실행하는지
- 파일을 어느 경로에 생성하는지
- 환경 변수를 어디에 작성하는지
- 패키지를 왜 설치하는지
- 코드 실행 방법
- 정상 실행 결과
- 실패했을 때 확인할 위치
- Windows와 WSL 경로 차이
- Docker Desktop과 WSL 연동 방법
- API Key 보관 방법

---

# 6. 전체 커리큘럼

| 순서 | 권 | 주제 | 예상 기간 | 우선순위 |
|---:|---|---|---:|:---:|
| 1 | Volume 01 | LLM 기초 | 1주 | ★★★★★ |
| 2 | Volume 02 | Prompt Engineering | 1주 | ★★★★☆ |
| 3 | Volume 03 | Tool Calling & MCP | 1주 | ★★★★★ |
| 4 | Volume 04 | Embedding & Vector Database | 1주 | ★★★★☆ |
| 5 | Volume 05 | RAG | 2주 | ★★★★★ |
| 6 | Volume 06 | Reranker | 1주 | ★★★★☆ |
| 7 | Volume 07 | Multi-Agent 설계 | 2주 | ★★★★★ |
| 8 | Volume 08 | Router 설계 | 3주 | ★★★★★ |
| 9 | Volume 09 | LangGraph | 2주 | ★★★★★ |
| 10 | Volume 10 | Evaluation | 1주 | ★★★☆☆ |
| 11 | Volume 11 | Kubernetes 기반 AI 운영 | 2~3주 | ★★★★☆ |

총 예상 학습 기간:

**17~18주**

---

# 7. 권별 상세 요구사항

# Volume 01. LLM 기초

## 목표

LLM의 기본 동작 원리를 이해하고 Python에서 API를 호출한다.

## 필수 내용

- AI, 머신러닝, 딥러닝, 생성형 AI의 차이
- LLM의 정의
- Transformer 개요
- Token
- Tokenizer
- Context Window
- Input Token과 Output Token
- System, User, Assistant Message
- Temperature
- Top-p
- Max Output Token
- Stop Sequence
- Hallucination
- 모델의 지식과 실시간 정보의 차이
- API 호출 구조
- Streaming
- 오류 처리
- 비용과 Token 사용량

## 필수 실습

1. Python 가상환경 생성
2. 환경 변수 설정
3. `.env` 파일 작성
4. LLM API 최초 호출
5. System Prompt 적용
6. Temperature 변경 결과 비교
7. Streaming 출력
8. Token 사용량 확인
9. API 오류 처리
10. 간단한 CLI 챗봇 구현

## 결과물

- `llm_client.py`
- `chat_cli.py`
- `.env.example`
- `tests/test_llm_client.py`

---

# Volume 02. Prompt Engineering

## 목표

목적과 출력 형식에 맞는 Prompt를 설계한다.

## 필수 내용

- Prompt의 구성 요소
- Instruction
- Context
- Input Data
- Output Format
- Constraint
- Zero-shot
- One-shot
- Few-shot
- Role Prompt
- Structured Output
- JSON Output
- ReAct 개념
- Chain of Thought를 직접 노출시키지 않고 구조적 추론을 유도하는 방법
- Prompt Injection
- Prompt Versioning
- Prompt Template
- Prompt 테스트

## 필수 실습

1. 불명확한 Prompt 개선
2. JSON 출력 강제
3. Few-shot 예제 적용
4. Prompt Template 작성
5. 입력 검증
6. Prompt Injection 방어
7. Prompt 버전별 결과 비교
8. Prompt 테스트 데이터 작성

## 결과물

- `prompts/`
- `prompt_templates.py`
- `prompt_runner.py`
- `tests/test_prompts.py`

---

# Volume 03. Tool Calling & MCP

## 목표

LLM이 외부 함수와 시스템을 안전하게 호출하도록 구현한다.

## 필수 내용

- Tool Calling 개념
- Function Calling 구조
- JSON Schema
- Tool 선택
- Tool Argument 검증
- Tool 실행 결과 반환
- Tool Loop
- Timeout
- Retry
- 권한 통제
- MCP 개념
- MCP Server
- MCP Client
- Resource
- Tool
- Prompt
- STDIO Transport
- HTTP Transport 개요
- Hermes와 MCP의 관계
- Codex와 MCP의 관계

## 필수 실습

1. 계산기 Tool
2. 파일 조회 Tool
3. 시스템 상태 조회 Tool
4. Tool Argument 검증
5. 여러 Tool 중 하나 선택
6. MCP Server 구현
7. MCP Client 연결
8. Hermes 또는 Codex에서 MCP 호출
9. Tool 실행 로그 저장
10. 위험 명령 승인 구조 구현

## 결과물

- `tools/`
- `mcp_server/`
- `mcp_client/`
- `tool_registry.py`
- `tests/test_tools.py`

---

# Volume 04. Embedding & Vector Database

## 목표

텍스트를 벡터로 변환하고 유사도 검색을 구현한다.

## 필수 내용

- 벡터의 의미
- Embedding 개념
- 차원
- Dense Vector
- Sparse Vector
- Cosine Similarity
- Dot Product
- Euclidean Distance
- Embedding Model
- Document Embedding
- Query Embedding
- Vector Database
- Collection
- Payload
- Metadata
- Index
- Qdrant
- pgvector 개요
- Chroma 개요

## 필수 실습

1. 문장 Embedding 생성
2. 유사도 직접 계산
3. 여러 문장 비교
4. Qdrant Docker 실행
5. Collection 생성
6. Vector 저장
7. Metadata 저장
8. Query 검색
9. 검색 결과 해석
10. 데이터 삭제 및 재색인

## 결과물

- `embedding_service.py`
- `vector_store.py`
- `docker-compose.yml`
- `scripts/index_documents.py`
- `tests/test_vector_store.py`

---

# Volume 05. RAG

## 목표

외부 문서를 검색하여 근거 기반 답변을 생성한다.

## 필수 내용

- RAG의 필요성
- Indexing Pipeline
- Retrieval Pipeline
- Generation Pipeline
- Document Loader
- Parsing
- Cleaning
- Chunking
- Chunk Size
- Chunk Overlap
- Metadata
- Dense Retrieval
- Sparse Retrieval
- Hybrid Search
- Query Transformation
- Context Injection
- Citation
- No-answer 처리
- RAG 보안
- RAG 비용
- RAG 성능 문제

## 필수 실습

1. Markdown 문서 로딩
2. PDF 문서 로딩
3. 문서 정제
4. Chunk 분할
5. Embedding 생성
6. Qdrant 저장
7. 질문 검색
8. 검색 문서 Prompt 삽입
9. 출처 표시
10. 답을 찾을 수 없는 질문 처리
11. Hybrid Search 구현
12. FastAPI 기반 RAG API 구현

## 결과물

- `rag/loader.py`
- `rag/chunker.py`
- `rag/indexer.py`
- `rag/retriever.py`
- `rag/generator.py`
- `api/main.py`
- `tests/test_rag.py`

---

# Volume 06. Reranker

## 목표

Retrieval 결과를 재정렬하여 RAG 품질을 개선한다.

## 필수 내용

- Recall과 Precision
- Retriever와 Reranker 차이
- Bi-Encoder
- Cross-Encoder
- Top-k
- Candidate 수
- Reranking Score
- Threshold
- Latency와 품질의 관계
- 비용 최적화
- 다단계 검색 구조

## 필수 실습

1. 기존 Retrieval 결과 확인
2. Reranker 적용
3. 전후 순위 비교
4. 검색 품질 측정
5. Threshold 적용
6. 응답 지연 시간 측정
7. 후보 개수별 품질 비교

## 결과물

- `rag/reranker.py`
- `evaluation/retrieval_metrics.py`
- `tests/test_reranker.py`

---

# Volume 07. Multi-Agent 설계

## 목표

역할이 분리된 Agent들이 협업하는 구조를 구현한다.

## 필수 내용

- Agent 정의
- Agent와 단순 LLM 호출의 차이
- Agent Role
- Goal
- Memory
- Tool
- State
- Message Passing
- Task Delegation
- Planner
- Researcher
- Developer
- Reviewer
- QA
- DevOps
- Agent 간 충돌
- 무한 반복 방지
- 종료 조건
- Human-in-the-loop
- Hermes Agent 구조 분석

## 필수 실습

1. Planner Agent 구현
2. Developer Agent 구현
3. Reviewer Agent 구현
4. QA Agent 구현
5. Agent 간 메시지 전달
6. 작업 결과 공유
7. 최대 반복 횟수 설정
8. 실패 시 재시도
9. 승인 필요 작업 구분
10. Hermes 구성과 직접 구현 비교

## 결과물

- `agents/base.py`
- `agents/planner.py`
- `agents/developer.py`
- `agents/reviewer.py`
- `agents/qa.py`
- `orchestrator.py`
- `tests/test_agents.py`

---

# Volume 08. Router 설계

## 목표

사용자 요청과 현재 상태에 따라 최적의 Agent, Tool, Model을 선택한다.

## 필수 내용

- Router의 필요성
- Intent Classification
- Rule-based Router
- Keyword Router
- Semantic Router
- LLM Router
- Confidence Score
- Threshold
- Fallback
- Retry
- Escalation
- Cost-based Routing
- Latency-based Routing
- Capability-based Routing
- Model Routing
- Tool Routing
- Agent Routing
- Multi-stage Routing
- Router 실패 사례
- Router 평가 지표
- Router 로그
- Router 정책 관리

## 필수 실습

1. Rule-based Router
2. Keyword Router
3. Embedding 기반 Semantic Router
4. LLM 기반 Router
5. Confidence Threshold
6. Fallback Agent
7. 비용 기반 Model 선택
8. 장애 발생 시 다른 Agent로 전환
9. Router Decision Log
10. Router 평가 데이터셋
11. Routing Accuracy 측정
12. Router API 구현

## 결과물

- `router/base.py`
- `router/rule_router.py`
- `router/semantic_router.py`
- `router/llm_router.py`
- `router/policy.py`
- `router/fallback.py`
- `evaluation/router_metrics.py`
- `tests/test_router.py`

---

# Volume 09. LangGraph

## 목표

상태 기반 Agent Workflow를 LangGraph로 구현한다.

## 필수 내용

- Graph 기반 Workflow
- State
- Node
- Edge
- Conditional Edge
- START
- END
- Reducer
- Checkpoint
- Persistence
- Memory
- Subgraph
- Interrupt
- Human-in-the-loop
- Retry
- Error Node
- Streaming
- LangGraph와 직접 구현 비교

## 필수 실습

1. 단일 Node Graph
2. 여러 Node 연결
3. Conditional Edge
4. Router 연동
5. Planner-Developer-Reviewer Workflow
6. 실패 시 재시도
7. Human Approval
8. Checkpoint 저장
9. 작업 재개
10. Streaming 상태 출력
11. Subgraph 구성
12. FastAPI 연동

## 결과물

- `graph/state.py`
- `graph/nodes.py`
- `graph/workflow.py`
- `graph/checkpointer.py`
- `tests/test_graph.py`

---

# Volume 10. Evaluation

## 목표

LLM, RAG, Router, Agent의 품질을 수치로 측정한다.

## 필수 내용

- Evaluation의 필요성
- Offline Evaluation
- Online Evaluation
- Golden Dataset
- Test Case
- Deterministic Test
- LLM-as-a-Judge
- Human Evaluation
- Retrieval Recall
- Precision
- Hit Rate
- MRR
- NDCG
- Routing Accuracy
- Task Success Rate
- Hallucination Rate
- Citation Accuracy
- Latency
- Token Usage
- Cost
- Regression Test
- Prompt 변경 검증

## 필수 실습

1. 평가 데이터셋 작성
2. RAG 검색 평가
3. 답변 정확도 평가
4. Router 정확도 평가
5. Agent Task Success 측정
6. Latency 측정
7. Token 사용량 측정
8. 비용 계산
9. Prompt 변경 전후 비교
10. 평가 리포트 생성

## 결과물

- `evaluation/datasets/`
- `evaluation/runner.py`
- `evaluation/report.py`
- `reports/`
- `tests/test_evaluation.py`

---

# Volume 11. Kubernetes 기반 AI 운영

## 목표

완성된 AI Platform을 컨테이너화하고 Kubernetes에서 운영한다.

## 필수 내용

- 운영 환경과 개발 환경 차이
- Dockerfile
- Multi-stage Build
- Docker Compose
- Environment Variable
- Secret
- ConfigMap
- Health Check
- Logging
- Metrics
- Tracing
- Kubernetes Pod
- Deployment
- Service
- Ingress
- Job
- CronJob
- HPA
- PVC
- Secret
- ConfigMap
- Rolling Update
- Rollback
- Resource Limit
- Readiness Probe
- Liveness Probe
- Observability
- 장애 대응
- 비용 관리

## 필수 실습

1. API Docker 이미지 생성
2. Qdrant, Redis, PostgreSQL 구성
3. Docker Compose 통합 실행
4. Health Check 구현
5. Kubernetes 로컬 환경 구성
6. Deployment 작성
7. Service 작성
8. ConfigMap 및 Secret 작성
9. Ingress 구성
10. HPA 구성
11. Rolling Update
12. Rollback
13. 로그 확인
14. 장애 상황 재현
15. 최종 AI Platform 배포

## 결과물

- `Dockerfile`
- `docker-compose.yml`
- `k8s/namespace.yaml`
- `k8s/deployment.yaml`
- `k8s/service.yaml`
- `k8s/configmap.yaml`
- `k8s/secret.example.yaml`
- `k8s/ingress.yaml`
- `k8s/hpa.yaml`
- `scripts/deploy.sh`
- `scripts/rollback.sh`

---

# 8. 최종 프로젝트

## 8.1 프로젝트명

**AI 업무 처리 플랫폼**

## 8.2 최종 기능

- 사용자 요청 수신
- 요청 의도 분석
- Router 기반 Agent 선택
- Planner가 작업 계획 수립
- Research Agent가 문서 검색
- Developer Agent가 코드 작성
- Reviewer Agent가 코드 검토
- QA Agent가 테스트
- RAG 기반 내부 문서 활용
- Tool Calling을 통한 외부 기능 실행
- Human Approval
- 실행 로그 저장
- 평가 지표 수집
- Docker 배포
- Kubernetes 배포

## 8.3 최종 아키텍처

```text
사용자
  │
  ▼
FastAPI Gateway
  │
  ▼
요청 검증
  │
  ▼
Router
  ├── Rule Router
  ├── Semantic Router
  └── LLM Router
  │
  ▼
LangGraph Orchestrator
  ├── Planner Agent
  ├── Research Agent
  ├── Developer Agent
  ├── Reviewer Agent
  ├── QA Agent
  └── DevOps Agent
  │
  ├── RAG
  │    ├── Loader
  │    ├── Chunker
  │    ├── Embedding
  │    ├── Retriever
  │    └── Reranker
  │
  ├── Tool Calling
  │    ├── MCP Server
  │    ├── File Tool
  │    ├── Git Tool
  │    ├── Docker Tool
  │    └── System Tool
  │
  ▼
Evaluation & Observability
  │
  ▼
Docker / Kubernetes
```

---

# 9. 실습 환경 기준

## 9.1 운영체제

기본:

- Windows 10 또는 Windows 11
- WSL2
- Ubuntu 22.04 LTS 또는 24.04 LTS
- Docker Desktop

대안:

- Ubuntu Linux
- macOS

## 9.2 개발 도구

- Visual Studio Code
- VSCode WSL Extension
- Git
- Python 3.12 이상
- Anaconda Distribution과 `conda` (Python 3.12 교재 전용 환경)
- Docker
- Docker Compose
- kubectl
- kind 또는 minikube

## 9.3 Python 핵심 패키지

예시 기준:

```text
openai
python-dotenv
pydantic
pydantic-settings
fastapi
uvicorn
httpx
tenacity
qdrant-client
sentence-transformers
langgraph
langchain-core
redis
psycopg
pytest
pytest-asyncio
ruff
mypy
```

패키지 버전은 프로젝트 생성 시점의 안정 버전을 확인하고 고정한다.

## 9.4 외부 서비스

필수:

- GitHub

선택:

- OpenAI API
- Ollama
- Anthropic API
- 기타 OpenAI 호환 API

유료 API 없이도 가능한 실습 경로를 함께 제공한다.

---

# 10. 저장소 구조

Codex는 다음 구조로 프로젝트를 생성한다.

```text
ai-platform-engineering-book/
├── README.md
├── PRD.md
├── CONTRIBUTING.md
├── CHANGELOG.md
├── pyproject.toml
├── environment.yml
├── .gitignore
├── .env.example
├── Makefile
├── docs/
│   ├── index.md
│   ├── glossary.md
│   ├── setup/
│   │   ├── windows.md
│   │   ├── wsl.md
│   │   ├── linux.md
│   │   ├── docker.md
│   │   └── vscode.md
│   ├── volume01-llm-fundamentals/
│   ├── volume02-prompt-engineering/
│   ├── volume03-tool-calling-mcp/
│   ├── volume04-embedding-vector-db/
│   ├── volume05-rag/
│   ├── volume06-reranker/
│   ├── volume07-multi-agent/
│   ├── volume08-router/
│   ├── volume09-langgraph/
│   ├── volume10-evaluation/
│   └── volume11-kubernetes-ai-platform/
├── src/
│   └── ai_platform/
│       ├── core/
│       ├── prompts/
│       ├── tools/
│       ├── mcp/
│       ├── embeddings/
│       ├── rag/
│       ├── reranker/
│       ├── agents/
│       ├── router/
│       ├── graph/
│       ├── evaluation/
│       └── api/
├── tests/
│   ├── unit/
│   ├── integration/
│   └── evaluation/
├── data/
│   ├── sample_docs/
│   ├── evaluation/
│   └── generated/
├── scripts/
├── docker/
├── k8s/
├── reports/
└── examples/
```

---

# 11. 권별 문서 구조

각 Volume은 다음 파일 구조를 기본으로 한다.

```text
volumeXX-topic/
├── README.md
├── 01-learning-objectives.md
├── 02-why-it-matters.md
├── 03-theory.md
├── 04-environment-setup.md
├── 05-guided-practice.md
├── 06-applied-practice.md
├── 07-mini-project.md
├── 08-troubleshooting.md
├── 09-exercises.md
├── 10-interview-questions.md
├── 11-summary.md
└── checklist.md
```

필요하면 장을 더 나눌 수 있다.

---

# 12. 장별 작성 템플릿

모든 장은 다음 형식을 따른다.

```markdown
# 장 제목

## 1. 학습 목표

이 장을 완료한 뒤 할 수 있어야 하는 일을 작성한다.

## 2. 왜 필요한가

기존 문제와 기술의 필요성을 설명한다.

## 3. 핵심 개념

초보자가 이해할 수 있도록 설명한다.

## 4. 동작 구조

ASCII 또는 Mermaid 다이어그램을 사용한다.

## 5. 실습 환경

필요한 운영체제, 패키지, 파일 경로를 작성한다.

## 6. 단계별 실습

모든 명령어와 코드를 실행 순서대로 작성한다.

## 7. 코드 설명

핵심 코드의 역할을 줄 단위 또는 블록 단위로 설명한다.

## 8. 정상 실행 결과

예상되는 출력과 확인 방법을 작성한다.

## 9. 오류 해결

자주 발생하는 오류, 원인, 확인 방법, 해결 방법을 작성한다.

## 10. 응용 실습

학습자가 일부를 직접 수정하거나 확장하게 한다.

## 11. 실무 적용

실제 서비스에서 사용할 때의 고려사항을 작성한다.

## 12. 과제

기본, 응용, 심화 단계로 나누어 작성한다.

## 13. 완료 체크리스트

학습 목표 달성 여부를 확인한다.

## 14. 핵심 정리

가장 중요한 내용을 요약한다.
```

---

# 13. 문체 및 설명 규칙

## 13.1 기본 언어

- 모든 교재 본문은 한국어로 작성한다.
- 기술 용어는 최초 등장 시 한글과 영어를 함께 표기한다.
- 이후에는 업계에서 일반적으로 사용하는 표현을 사용한다.

예:

```text
검색 증강 생성(Retrieval-Augmented Generation, RAG)
```

## 13.2 문체

- 설명은 담백하고 명확하게 작성한다.
- 의미 없는 과장 표현을 사용하지 않는다.
- 초보자에게 말을 거는 듯한 지나친 구어체를 피한다.
- 한 문장은 지나치게 길지 않게 작성한다.
- 정의만 나열하지 말고 원인과 결과를 연결한다.
- 중요한 주의사항은 `> [!WARNING]` 형식으로 작성한다.
- 참고사항은 `> [!NOTE]` 형식으로 작성한다.
- 실무 팁은 `> [!TIP]` 형식으로 작성한다.

## 13.3 금지 표현

다음과 같은 표현은 최소화한다.

- 매우 쉽습니다.
- 그냥 하면 됩니다.
- 당연히
- 무조건
- 이것만 알면 됩니다.
- 마법처럼
- 완벽한
- 혁신적인

---

# 14. 코드 작성 규칙

## 14.1 Python

- Python 3.12 이상 기준
- Type Hint 필수
- 함수와 클래스에 Docstring 작성
- 예외 처리 포함
- 환경 변수는 코드에 하드코딩하지 않는다.
- 비밀 값은 `.env` 또는 Secret으로 관리한다.
- `pydantic`을 이용한 입력 검증을 우선한다.
- 외부 API 호출에는 Timeout을 지정한다.
- Retry는 무한 반복하지 않는다.
- Logging을 사용하고 `print()`에만 의존하지 않는다.
- 비동기 처리가 필요한 경우 `async/await`를 사용한다.
- 테스트 가능한 구조로 작성한다.

## 14.2 테스트

- 모든 핵심 모듈에 단위 테스트를 작성한다.
- 외부 API는 Mocking 가능한 구조로 작성한다.
- 테스트 함수명은 목적이 드러나게 작성한다.
- 정상 사례와 실패 사례를 모두 포함한다.
- 명령 한 번으로 테스트가 실행되어야 한다.

```bash
pytest
```

## 14.3 품질 검사

다음 명령이 성공해야 한다.

```bash
ruff check .
mypy src
pytest
```

---

# 15. 명령어 작성 규칙

모든 명령어는 실행 환경을 표시한다.

예:

```bash
# 실행 위치: WSL Ubuntu 터미널
mkdir -p ~/projects/ai-platform-engineering-book
cd ~/projects/ai-platform-engineering-book
```

PowerShell 명령은 별도 표시한다.

```powershell
# 실행 위치: Windows PowerShell 관리자 권한
wsl --install
```

각 명령 뒤에는 다음 내용을 설명한다.

- 명령의 목적
- 생성되는 파일 또는 폴더
- 정상 결과
- 오류 발생 시 확인할 내용

---

# 16. 보안 요구사항

- API Key를 Git에 커밋하지 않는다.
- `.env`는 `.gitignore`에 포함한다.
- `.env.example`에는 실제 키를 넣지 않는다.
- Tool Calling으로 시스템 명령을 실행할 때 Allowlist를 사용한다.
- 파일 Tool은 허용된 작업 디렉터리 밖에 접근하지 못하게 한다.
- 삭제, 배포, 메일 발송 등 위험 작업은 사용자 승인을 요구한다.
- Prompt Injection으로 Tool 권한이 상승하지 않게 한다.
- 외부 문서의 지시문과 시스템 지시문을 분리한다.
- 로그에 API Key와 개인정보를 기록하지 않는다.
- Kubernetes Secret 예제에는 실제 값을 넣지 않는다.

---

# 17. Codex 작업 수행 규칙

## 17.1 작업 단위

Codex는 전체 11권을 한 번에 생성하지 않는다.

다음 단위로 작업한다.

1. 저장소 기본 구조
2. 공통 환경 설정
3. Volume별 목차
4. Chapter별 문서
5. Chapter별 실습 코드
6. 테스트
7. 문서 검수
8. Volume 완료 보고
9. 다음 Volume 진행

## 17.2 작업 순서

```text
Phase 0: 저장소 초기화
Phase 1: 공통 개발 환경 및 문서 템플릿
Phase 2: Volume 01 작성
Phase 3: Volume 02 작성
Phase 4: Volume 03 작성
Phase 5: Volume 04 작성
Phase 6: Volume 05 작성
Phase 7: Volume 06 작성
Phase 8: Volume 07 작성
Phase 9: Volume 08 작성
Phase 10: Volume 09 작성
Phase 11: Volume 10 작성
Phase 12: Volume 11 작성
Phase 13: 최종 통합 및 검수
```

## 17.3 작업 전 확인

각 작업 전에 다음을 확인한다.

- 기존 파일 구조
- 이전 Volume의 결과물
- 현재 작업의 의존성
- 패키지 버전
- 중복 설명 여부
- 이전 코드와 호환 여부

## 17.4 작업 후 보고

각 작업 완료 후 다음 형식으로 보고한다.

```text
작업명:
생성한 파일:
수정한 파일:
실행한 테스트:
테스트 결과:
미완료 항목:
다음 작업:
```

---

# 18. Definition of Done

각 Chapter는 다음 조건을 모두 만족해야 완료로 처리한다.

- [ ] 학습 목표가 명확하다.
- [ ] 기술이 필요한 이유가 설명되어 있다.
- [ ] 초보자 기준 이론 설명이 있다.
- [ ] 구조 다이어그램이 있다.
- [ ] 환경 구성 방법이 있다.
- [ ] 모든 명령어의 실행 위치가 표시되어 있다.
- [ ] 실행 가능한 코드가 있다.
- [ ] 코드 설명이 있다.
- [ ] 정상 실행 결과가 있다.
- [ ] 오류 해결 항목이 있다.
- [ ] 응용 실습이 있다.
- [ ] 과제가 있다.
- [ ] 완료 체크리스트가 있다.
- [ ] 예제 코드 테스트가 통과한다.
- [ ] 문서 내부 링크가 정상이다.
- [ ] 비밀 값이 포함되어 있지 않다.
- [ ] 이전 Chapter와 내용이 자연스럽게 연결된다.

각 Volume은 다음 조건을 만족해야 완료로 처리한다.

- [ ] 모든 Chapter가 완료되었다.
- [ ] Volume README가 있다.
- [ ] 전체 실습을 처음부터 다시 실행할 수 있다.
- [ ] Volume별 미니 프로젝트가 동작한다.
- [ ] 테스트가 통과한다.
- [ ] 다음 Volume에서 사용할 결과물이 정리되어 있다.
- [ ] 학습자 체크리스트가 있다.
- [ ] 주요 용어가 Glossary에 추가되어 있다.

---

# 19. 자동 검증 요구사항

다음 검증 스크립트를 작성한다.

```text
scripts/
├── validate_docs.py
├── validate_links.py
├── validate_code_blocks.py
├── run_all_tests.sh
└── check_secrets.py
```

## 검증 항목

- Markdown 링크 오류
- 빈 문서
- 필수 섹션 누락
- 실행 불가능한 Python 예제
- 코드 블록 언어 누락
- 실제 API Key 포함 여부
- `.env` 커밋 여부
- 테스트 실패
- 중복된 제목
- 목차와 실제 파일 불일치

---

# 20. README 요구사항

루트 `README.md`는 다음 내용을 포함한다.

1. 프로젝트 소개
2. 대상 독자
3. 학습 목표
4. 전체 커리큘럼
5. 예상 학습 기간
6. 실습 환경
7. 빠른 시작
8. 저장소 구조
9. 학습 진행 방법
10. 테스트 실행 방법
11. 문제 해결
12. 보안 주의사항
13. 기여 방법
14. 라이선스

---

# 21. 초기 생성 작업

Codex는 첫 실행에서 다음 작업만 수행한다.

## Task 1. 저장소 기본 구조 생성

- 디렉터리 생성
- 기본 설정 파일 생성
- `.gitignore` 생성
- `.env.example` 생성
- `pyproject.toml` 생성
- `README.md` 생성
- `CONTRIBUTING.md` 생성
- `CHANGELOG.md` 생성

## Task 2. 공통 개발 환경 작성

다음 문서를 생성한다.

- Windows 사전 준비
- WSL2 설치
- Ubuntu 초기 설정
- Docker Desktop 설치 및 WSL 연동
- VSCode WSL 연결
- Git 설정
- Python 가상환경
- 프로젝트 설치
- 환경 변수 설정
- 테스트 실행

## Task 3. 전체 목차 생성

11개 Volume의 README와 장 목록을 생성한다.

이 단계에서는 교재 본문을 모두 작성하지 않는다.

## Task 4. Volume 01 상세 계획 생성

Volume 01의 각 장에 대해 다음을 작성한다.

- 목표
- 이론 범위
- 실습 범위
- 생성 파일
- 테스트 항목
- 완료 기준

## Task 5. 검증

다음 명령이 성공하도록 구성한다.

```bash
ruff check .
mypy src
pytest
```

---

# 22. Codex 시작 프롬프트

아래 프롬프트를 Codex에 전달하여 프로젝트를 시작한다.

```text
현재 디렉터리에 있는 PRD.md를 프로젝트의 최상위 요구사항으로 사용해 주세요.

먼저 PRD 전체를 읽고 요구사항을 분석한 뒤, Phase 0과 초기 생성 작업만 수행하세요.

이번 작업 범위:
1. 저장소 기본 구조 생성
2. 공통 설정 파일 생성
3. 공통 개발 환경 문서 생성
4. 전체 11개 Volume 목차 생성
5. Volume 01 상세 작업 계획 생성
6. 기본 테스트 및 문서 검증 구조 생성

중요 규칙:
- 모든 문서는 한국어로 작성하세요.
- 코드와 명령어는 실제 실행 가능해야 합니다.
- 비밀 값을 하드코딩하지 마세요.
- 사용자 승인 없이 외부 서비스 호출, 배포, 파일 삭제를 수행하지 마세요.
- 전체 교재 본문을 한 번에 생성하지 마세요.
- 작업 완료 후 생성 파일, 테스트 결과, 미완료 항목, 다음 작업을 보고하세요.
- 요구사항이 충돌하면 PRD.md를 우선하세요.
```

---

# 23. 최종 성공 기준

이 프로젝트는 다음 조건을 모두 만족할 때 최종 완료로 처리한다.

- 11개 Volume이 모두 작성되어 있다.
- 모든 교재 본문이 한국어로 작성되어 있다.
- 초보자가 처음부터 환경을 구성할 수 있다.
- 모든 주요 개념에 실행 가능한 실습이 있다.
- 하나의 AI Platform 프로젝트가 단계적으로 완성된다.
- RAG, Reranker, Multi-Agent, Router, LangGraph가 통합되어 있다.
- Docker Compose 환경에서 전체 시스템이 실행된다.
- Kubernetes 로컬 클러스터에 배포할 수 있다.
- 자동 테스트가 통과한다.
- 문서 검증이 통과한다.
- 실제 비밀 값이 저장소에 포함되지 않는다.
- 학습자는 결과물의 구조와 동작 원리를 설명할 수 있다.
- 학습자는 새로운 Tool, Agent, Route를 직접 추가할 수 있다.
- 학습자는 검색 및 라우팅 성능을 측정하고 개선할 수 있다.
- 학습자는 장애 발생 시 로그를 확인하고 문제를 해결할 수 있다.

---

# 24. 프로젝트 비전

본 프로젝트의 목적은 단순한 LLM 개념 요약집을 제작하는 것이 아니다.

Hermes와 Codex를 사용해 본 개발자가 LLM의 기본 원리부터 시작하여 RAG, Multi-Agent, Router, LangGraph, Evaluation, Kubernetes까지 직접 구현하도록 돕는 실무 교재를 제작한다.

최종 결과물은 다음 세 가지 역할을 동시에 수행해야 한다.

1. **입문 교재**  
   LLM을 처음 배우는 개발자가 개념을 이해할 수 있어야 한다.

2. **실습 매뉴얼**  
   명령어와 코드를 따라 실행하여 시스템을 구축할 수 있어야 한다.

3. **프로젝트 설계서**  
   학습 후 실제 AI Platform 프로젝트를 설계할 때 참고할 수 있어야 한다.
