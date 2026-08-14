# 02. Local Collection, Payload, and Vector Search

## 1. Learning objectives

By the end of this chapter, you can distinguish a vector collection from a point, store a document vector with payload metadata, search it with a query vector, and explain why payload filters are applied before interpreting ranked results. You will do so with a deterministic, local in-memory mock; this chapter does **not** start Docker or contact Qdrant.

## 2. Why this is needed

An embedding alone is only a list of numbers. A useful search system also needs an ID to identify the source document and metadata to filter, authorize, display, or re-index it. For example, a result about an API retry policy must retain its document ID, topic, and version so a later RAG system can retrieve the source rather than just an anonymous vector.

A vector database organizes this data in a collection. The later Qdrant exercise will put the same boundaries behind a server. First, the local mock makes the data contract testable without a container, network, API key, or model download.

## 3. Key concepts

- **Vector database**: a database optimized to store vectors and find nearby vectors.
- **Collection**: a named group of points with one fixed vector dimension and distance rule.
- **Point**: one stored record: a unique ID, a vector, and payload.
- **Payload / metadata**: values stored beside the vector, such as `topic`, `version`, source ID, or access label.
- **Upsert**: insert a new point or replace the point with the same ID.
- **Query vector**: the embedding of the user's search text, produced by the same model and dimensions as indexed vectors.
- **Metadata filter**: a condition that restricts candidates, for example `{"topic": "api"}`.
- **Index**: an internal data structure that accelerates nearest-neighbor search. The local mock linearly compares every eligible point; production Qdrant configures an index for larger collections.

> [!WARNING]
> `InMemoryVectorStore` is a deterministic teaching mock, not a production database. It has no persistence, distributed index, authentication, backup, or Qdrant network protocol. Its contents disappear when the Python process stops.

## 4. Flow

```text
Documents ─> DeterministicEmbeddingModel ─> vectors ─┐
                                                       ├─> collection "platform_docs"
IDs + payload (topic, version) ───────────────────────┘             │
                                                                     ▼
Query text ─> same embedding model ─> query vector ─> metadata filter + cosine ranking
                                                                     │
                                                                     ▼
                                                 ID, score, payload returned to caller
```

The collection is created with `vector_size=64`; every stored and query vector must therefore contain 64 finite, non-zero numbers. This protects against comparing vectors from incompatible embedding spaces.

## 5. Environment and files

Run all commands from the repository root in Windows PowerShell, Git Bash, or WSL. Python 3.12+ and `uv` are required. No environment variable, API key, internet connection, Docker daemon, Qdrant service, or external model is used.

Files in this exercise:

- `src/ai_platform/embeddings/vector_store.py`
- `examples/volume04/vector_store_search.py`
- `tests/unit/test_volume04_vector_store.py`

```bash
uv run python examples/volume04/vector_store_search.py
uv run pytest tests/unit/test_volume04_vector_store.py -q
```

If the project environment does not exist yet, run `uv sync --group dev` from the repository root, then repeat the commands.

## 6. Step-by-step practice

1. Create `InMemoryVectorStore()`; it contains no collections initially.
2. Create `platform_docs` with `vector_size=64`.
3. Use `DeterministicEmbeddingModel(dimensions=64)` for every document and query.
4. Wrap each vector in `VectorPoint(id=..., vector=..., payload=...)`.
5. Call `upsert` to write the three points. A repeated ID replaces its old vector and payload.
6. Embed `Python API 오류 처리 방법` and pass the result to `search`.
7. Pass `metadata_filter={"topic": "api"}` to keep only API documents.
8. Inspect each returned `id`, `score`, and `payload`, rather than treating the score alone as a final answer.

The example deliberately assigns a small scalar-only payload. A production schema might add a source URI, document version, tenant ID, and access-control label, but it must not casually duplicate secret material into metadata.

## 7. Code walkthrough

`create_collection("platform_docs", vector_size=64)` fixes the vector contract before any data is written. `upsert` accepts a non-empty `list[VectorPoint]` or `tuple[VectorPoint, ...]`, not a single point, string, bytes value, or arbitrary iterable. It validates the complete batch first, so a malformed point cannot leave a half-written batch. It copies vectors and payloads into immutable stored records, preventing later caller mutations from silently changing indexed data.

`search` validates the query dimension, then filters points whose payload contains every requested key/value **with the same scalar type** before it calculates cosine similarity. Payload values must be the built-in JSON scalar types `str`, `int`, `float`, `bool`, or `None`; an `IntEnum` or another scalar subclass is rejected rather than being silently stored with ambiguous filter semantics. A missing key does not match a `null`/`None` filter, and Python's `True == 1` shortcut does not allow a boolean filter to match an integer payload. Cosine calculation scales each finite vector before multiplying components, so valid large values do not overflow a temporary dot product or norm. Its underlying dot summation uses compensated `math.fsum`, preserving a small finite residual after large positive and negative terms cancel. Euclidean-distance demonstrations use `math.hypot` for the same reason, instead of squaring large finite deltas. Scores are clamped to the closed `[-1.0, 1.0]` range so a floating-point rounding artifact cannot leak an out-of-range score to a no-answer gate. It then sorts candidates by `score` descending. Equal scores use point ID ascending as a tie-breaker so local runs and tests remain deterministic. The `limit` is applied only after sorting.

`delete` accepts a non-empty batch of point IDs, removes known IDs, and reports the actual number removed. Rejecting an empty batch or a single string prevents an accidental no-op or character-by-character deletion request. This return value makes a re-index workflow observable: delete stale IDs, verify the count, then upsert the new document version.

## 8. Expected result and interpretation

The example begins with:

```text
collection_size=3
1. id=retry-guide score=... topic=api
```

Only one result is printed because the `topic=api` filter excludes the vector and infrastructure documents. `retry-guide` should be first because it shares the deterministic mock's query tokens. The decimal score is illustrative; verify the collection size, returned ID, payload topic, and order instead of hard-coding a rounded score.

The test command must report all tests passed. It covers ranking and payload return, metadata filtering, ID replacement, caller-mutation isolation, atomic batch rejection, deletion, validation errors, and deterministic tie ordering.

## 9. Troubleshooting

| Symptom | Likely cause | Check and fix |
|---|---|---|
| `collection not found` | `create_collection` was skipped or the name differs | Create the collection first and use the exact same name. |
| `vector must have dimension 64` | A different model dimension was used for a point or query | Use the same embedding configuration for creation, indexing, and search. |
| `vector must not be a zero vector` | A manually supplied empty-signal vector was used | Embed non-empty text or supply a meaningful, non-zero numeric vector. |
| `points must be a non-empty sequence of VectorPoint instances` | `upsert` received an empty batch, a single value, string, bytes value, or non-sequence | Wrap one or more points in a `list[VectorPoint]` or `tuple[VectorPoint, ...]`, for example `[VectorPoint(...)]`. |
| `point_ids must be a non-empty sequence of strings` | `delete` received an empty list, a single string, bytes, or a non-batch value | Pass one or more non-empty IDs in a `list[str]` or `tuple[str, ...]`, for example `["retry-guide"]`. |
| No results | The metadata filter does not exactly match any payload key, value, and scalar type | Print the stored payload keys, values, and types; a missing key does not match `None`, and `true` does not match integer `1`. |
| `payload values must be built-in JSON scalar values` | An enum or custom scalar subclass was supplied as metadata | Convert it deliberately to `str`, `int`, `float`, `bool`, or `None` before `upsert`; this keeps stored and filter types predictable. |
| An indexed record unexpectedly changed after `upsert` | Caller code mutated the original vector or payload object | Do not rely on caller-owned mutable input after writing. The local store copies inputs into immutable stored records; query again and inspect the returned payload. |
| The expected document is not first | This is a token-hash educational mock, not semantic AI | Check shared tokens and use a real evaluated embedding model only in a later explicit integration. |

## 10. Extension exercise

Add a point with `id="retry-guide"` and `payload={"topic": "api", "version": 2}`. Verify that `collection_size` stays at 3 after upsert and a `metadata_filter={"version": 2}` search returns the replacement. Then delete the point, verify that `delete` returns 1, and re-index it. This mirrors a controlled document-update cycle without a live database.

## 11. Production notes

When switching to Qdrant, retain the same explicit contracts: collection name, distance metric, embedding model/version, vector size, point ID, payload schema, filters, and delete/re-index policy. Configure Qdrant connection details and credentials outside source code, do not log raw sensitive documents or API keys, enforce authorization filters before returning results, and measure retrieval quality with representative test queries. A dimension or model change requires a coordinated new collection or full re-index, not mixed vectors.

Qdrant, pgvector, and Chroma make different operational trade-offs: Qdrant specializes in vector collections and payload filtering; pgvector keeps vectors in PostgreSQL; Chroma is often convenient for local prototyping. The application-level ID/vector/payload contract remains necessary in all three.

## 12. Exercises

- **Basic**: Explain why `topic` belongs in payload but the dense vector does not replace the document ID.
- **Applied**: Add a test proving that an invalid point in a two-point batch does not write the valid point.
- **Advanced**: Define a payload schema for a multi-tenant document collection. State which key is required for authorization filtering and how a re-index changes `embedding_model_version`.

## 13. Completion checklist

- [x] I can name the ID, vector, and payload fields of a point.
- [x] I created a collection with a fixed vector dimension.
- [x] I upserted document vectors with metadata using a local mock.
- [x] I searched with a query vector and interpreted ID, score, and payload.
- [x] I filtered results by metadata.
- [x] I tested replacement, deletion, malformed input, and deterministic ordering.
- [ ] I have run the separate Qdrant Docker exercise. This is intentionally deferred to a later, explicitly local integration slice.

## 14. Summary

A vector collection stores points, not just vectors: every point needs a stable ID and useful payload metadata. Upsert makes document versions replaceable; filtering limits eligible candidates; cosine search ranks the remaining points. The deterministic in-memory implementation verifies these application contracts safely before a later Qdrant integration.
