import asyncio
import time
from typing import List, Dict, Any, Optional

from knowledge_base.vector_store import VectorStore
from knowledge_base.embeddings import EmbeddingProvider
from knowledge_base.reranking import Reranker, PassThroughReranker, CrossEncoderReranker
from knowledge_base.schemas import KnowledgeSearchResultItem, KnowledgeSearchResponse
from knowledge_base.security import SecurityManager
from knowledge_base.metrics import kb_metrics
from knowledge_base.chunking import estimate_token_count
from app.utils.logging import logger


class KnowledgeRetrievalEngine:
    """Production RAG retrieval engine handling query normalization, vector search, reranking, confidence gating, context budgeting, and metrics."""

    def __init__(
        self,
        vector_store: VectorStore,
        embedding_provider: EmbeddingProvider,
        reranker: Optional[Reranker] = None,
        min_score: float = 0.70,
        max_context_tokens: int = 2500,
        collection_name: str = "sharyx_kb_vectors",
        cache_enabled: bool = False,
    ):
        self.vector_store = vector_store
        self.embedding_provider = embedding_provider
        self.reranker = reranker or PassThroughReranker()
        self.min_score = min_score
        self.max_context_tokens = max_context_tokens
        self.collection_name = collection_name
        self.cache_enabled = cache_enabled
        self._cache: Dict[str, Dict[str, Any]] = {}

    def _normalize_query(self, query: str) -> str:
        clean = query.strip().lower()
        clean = " ".join(clean.split())
        return clean

    async def search(
        self,
        query: str,
        tenant_id: str,
        knowledge_base_id: Optional[str] = None,
        top_k: int = 5,
        category: Optional[str] = None,
    ) -> KnowledgeSearchResponse:
        start_time = time.time()
        normalized_q = self._normalize_query(query)

        # 1. MANDATORY TENANT CHECK
        if not tenant_id:
            logger.error("[RETRIEVAL][SECURITY] Search attempt without tenant_id rejected.")
            kb_metrics.record_search(success=False, found=False, latency_ms=0.0, confidence=0.0)
            return KnowledgeSearchResponse(
                success=False,
                found=False,
                query=query,
                confidence=0.0,
                message="Tenant isolation error: tenant_id required.",
                error_code="TENANT_ID_REQUIRED",
            )

        # 2. Check query cache if enabled
        cache_key = f"{tenant_id}:{knowledge_base_id or 'all'}:{normalized_q}"
        if self.cache_enabled and cache_key in self._cache:
            cached_data = self._cache[cache_key]
            logger.info(f"[RETRIEVAL][CACHE-HIT] Served query '{query}' from cache")
            return KnowledgeSearchResponse(**cached_data)

        try:
            # 3. Embed Search Query
            query_vector = await self.embedding_provider.embed_query(normalized_q)

            # 4. Perform Similarity Search in Vector Store (MANDATORY tenant_id filter)
            filters = {}
            if category:
                filters["category"] = category

            raw_hits = await self.vector_store.search(
                collection_name=self.collection_name,
                query_vector=query_vector,
                tenant_id=tenant_id,
                kb_id=knowledge_base_id,
                top_k=max(top_k, 10),  # Retrieve candidate pool for reranking & score filtering
                score_threshold=0.0,
                filters=filters,
            )

            if not raw_hits:
                duration_ms = (time.time() - start_time) * 1000
                kb_metrics.record_search(success=True, found=False, latency_ms=duration_ms, confidence=0.0)
                return KnowledgeSearchResponse(
                    success=True,
                    found=False,
                    query=query,
                    confidence=0.0,
                    latency_ms=round(duration_ms, 2),
                    results=[],
                    message="No relevant knowledge found for the query.",
                )

            # 5. Rerank candidates if reranker active
            reranked_hits = await self.reranker.rerank(query=normalized_q, candidate_chunks=raw_hits)

            # 6. Confidence threshold gating (KB_MIN_SCORE)
            passing_hits = [h for h in reranked_hits if h["score"] >= self.min_score]

            if not passing_hits:
                duration_ms = (time.time() - start_time) * 1000
                top_score = reranked_hits[0]["score"] if reranked_hits else 0.0
                logger.info(f"[RETRIEVAL][CONFIDENCE-GATED] Query '{query}' top score {top_score:.2f} failed threshold ({self.min_score})")
                kb_metrics.record_search(success=True, found=False, latency_ms=duration_ms, confidence=top_score)
                return KnowledgeSearchResponse(
                    success=True,
                    found=False,
                    query=query,
                    confidence=top_score,
                    latency_ms=round(duration_ms, 2),
                    results=[],
                    message="No sufficiently relevant knowledge was found.",
                )

            # 7. Context Budget Trimming (KB_MAX_CONTEXT_TOKENS)
            final_results: List[KnowledgeSearchResultItem] = []
            accumulated_tokens = 0

            for hit in passing_hits[:top_k]:
                payload = hit["payload"]
                raw_content = payload.get("content", "")
                sanitized_content = SecurityManager.sanitize_retrieved_content(raw_content)

                tokens = estimate_token_count(sanitized_content)
                if accumulated_tokens + tokens > self.max_context_tokens and final_results:
                    logger.info(f"[RETRIEVAL][CONTEXT-BUDGET-TRIM] Stopped context accumulation at {accumulated_tokens} tokens")
                    break

                accumulated_tokens += tokens
                item = KnowledgeSearchResultItem(
                    document_id=payload.get("document_id", "unknown"),
                    document_name=payload.get("source_name", "document"),
                    chunk_id=hit["id"],
                    content=sanitized_content,
                    score=hit["score"],
                    page=payload.get("page_number", 1),
                    section=payload.get("section", "General"),
                    metadata=payload,
                )
                final_results.append(item)

            duration_ms = (time.time() - start_time) * 1000
            top_confidence = final_results[0].score if final_results else 0.0

            res = KnowledgeSearchResponse(
                success=True,
                found=True,
                query=query,
                confidence=top_confidence,
                latency_ms=round(duration_ms, 2),
                results=final_results,
            )

            # Cache response if enabled
            if self.cache_enabled:
                self._cache[cache_key] = res.model_dump()

            kb_metrics.record_search(success=True, found=True, latency_ms=duration_ms, confidence=top_confidence)
            logger.info(f"[RETRIEVAL][SUCCESS] Query '{query}' retrieved {len(final_results)} chunks (confidence: {top_confidence:.2f}, latency: {duration_ms:.1f}ms)")
            return res

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            logger.exception(f"[RETRIEVAL][ERROR] Retrieval failed for query '{query}': {e}")
            kb_metrics.record_search(success=False, found=False, latency_ms=duration_ms, confidence=0.0)
            return KnowledgeSearchResponse(
                success=False,
                found=False,
                query=query,
                confidence=0.0,
                latency_ms=round(duration_ms, 2),
                message="Knowledge base search failed due to internal error.",
                error_code="KNOWLEDGE_BASE_UNAVAILABLE",
            )
