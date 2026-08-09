"""Application configuration via environment variables."""

from functools import lru_cache
from pathlib import Path
from typing import Annotated

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

BACKEND_ROOT = Path(__file__).resolve().parent.parent

# Placeholder JWT secret shipped as the default for local development
# convenience only. Any non-development environment must override it via the
# JWT_SECRET environment variable — see `Settings._require_real_jwt_secret`.
_DEFAULT_JWT_SECRET = "change-me-in-production"


class Settings(BaseSettings):
    """Central settings for the Knowra backend."""

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "Knowra"
    app_version: str = "0.1.0"
    app_env: str = "development"
    debug: bool = False

    # Database
    database_url: str = (
        "postgresql+psycopg://postgres:postgres@localhost:5432/eka"
    )

    # Logging
    log_level: str = "INFO"

    # Embeddings — set True in production when model is pre-cached (skips HF hub checks)
    embedding_local_only: bool = False

    # Single-tenant MVP placeholder
    tenant_id: str = "default"
    # Tenant branding / routing aliases (comma-separated in env: ORG_ALIASES).
    # Example: ORG_ALIASES=Acme Corp,Acme,ACME — never hardcode customer names in code.
    org_display_name: str = ""
    # NoDecode: allow comma-separated env values without JSON parsing first.
    org_aliases: Annotated[list[str], NoDecode] = []
    # Temporary Phase-1 acceptance logging for routing/RAG diagnostics.
    routing_debug_logging: bool = True
    # Phase-2B: full RAG retrieval diagnostics (reports under storage/diagnostics).
    rag_diagnostics_enabled: bool = True

    @field_validator("org_aliases", mode="before")
    @classmethod
    def _split_org_aliases(cls, value: object) -> object:
        """Accept JSON lists or comma-separated ORG_ALIASES env values."""
        if value is None or value == "":
            return []
        if isinstance(value, str):
            stripped = value.strip()
            if stripped.startswith("[") and stripped.endswith("]"):
                import json

                try:
                    parsed = json.loads(stripped)
                except json.JSONDecodeError:
                    parsed = None
                if isinstance(parsed, list):
                    return [str(part).strip() for part in parsed if str(part).strip()]
            return [part.strip() for part in value.split(",") if part.strip()]
        return value

    # Local filesystem storage (MVP)
    storage_path: Path = BACKEND_ROOT / "storage"
    documents_path: Path = BACKEND_ROOT / "storage" / "documents"
    indexes_path: Path = BACKEND_ROOT / "storage" / "indexes"

    # API
    api_v1_prefix: str = "/api/v1"
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    # JWT (Phase 2.3 token service — consumed by app.auth.jwt)
    jwt_secret: str = _DEFAULT_JWT_SECRET
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30
    jwt_refresh_token_expire_days: int = 7

    # LLM answer generation (provider-agnostic)
    llm_provider: str = "none"  # groq | openai | gemini | ollama | none
    llm_model: str = "llama-3.3-70b-versatile"
    llm_temperature: float = 0.1
    llm_max_tokens: int = 1024
    llm_timeout_seconds: float = 60.0
    llm_fallback_enabled: bool = True

    groq_api_key: str | None = None
    openai_api_key: str | None = None
    gemini_api_key: str | None = None
    ollama_base_url: str = "http://localhost:11434"

    # Document normalization (Phase 12.3A — pre-chunking cleaning)
    normalization_enable_boilerplate_removal: bool = True
    normalization_enable_unicode_cleanup: bool = True
    normalization_enable_ocr_cleanup: bool = True
    normalization_minimum_header_frequency: int = 2
    normalization_minimum_footer_frequency: int = 2
    normalization_maximum_header_lines: int = 4
    normalization_maximum_footer_lines: int = 3
    normalization_boilerplate_min_page_ratio: float = 0.4

    # Document structure extraction (Phase 12.3B — pre-chunking structure)
    structure_extraction_enabled: bool = True
    structure_max_heading_length: int = 200
    structure_min_table_columns: int = 2
    structure_min_table_rows: int = 2
    structure_max_table_columns: int = 6
    structure_max_stacked_table_rows: int = 25
    structure_table_column_gap_spaces: int = 2
    structure_table_confidence_threshold: float = 0.55
    structure_max_list_nesting_depth: int = 6

    # Semantic chunk generation (Phase 12.4)
    semantic_max_preferred_chunk_size: int = 1200
    semantic_min_chunk_size: int = 80
    semantic_soft_max_chunk_size: int = 1500
    semantic_absolute_max_chunk_size: int = 1800
    semantic_max_table_chunk_size: int = 1800
    semantic_max_paragraph_merge: int = 2
    semantic_section_merge_threshold: int = 1800
    semantic_overlap_enabled: bool = True
    semantic_include_hierarchy_in_overlap: bool = True

    # Metadata-aware retrieval (Phase 12.5)
    metadata_retrieval_enabled: bool = True
    metadata_candidate_multiplier: int = 15
    metadata_max_bonus: float = 0.15
    metadata_heading_similarity_weight: float = 0.04
    metadata_section_title_similarity_weight: float = 0.05
    metadata_hierarchy_similarity_weight: float = 0.03
    metadata_chunk_type_match_weight: float = 0.04
    metadata_table_intent_boost: float = 0.05
    metadata_list_intent_boost: float = 0.05
    metadata_section_header_intent_boost: float = 0.04
    metadata_paragraph_intent_boost: float = 0.04
    metadata_numeric_intent_boost: float = 0.03
    metadata_section_continuity_weight: float = 0.03
    metadata_document_continuity_weight: float = 0.02
    metadata_reading_order_continuity_weight: float = 0.02

    # Hybrid retrieval (Phase 12.7)
    hybrid_enabled: bool = True
    sparse_weight: float = 1.0
    dense_weight: float = 1.0
    rrf_k: int = 60
    bm25_k1: float = 1.5
    bm25_b: float = 0.75
    top_k_dense: int = 20
    top_k_sparse: int = 20
    top_k_final: int = 5
    hybrid_stemming_enabled: bool = False
    hybrid_stopwords_enabled: bool = True

    # Cross-encoder reranking (Phase 12.8)
    reranking_enabled: bool = True
    # Phase 3B: 40 so strong mid-merge evidence (e.g. metadata taxonomy at
    # merge rank ~26) still enters the CrossEncoder pool (was truncated at 20).
    rerank_top_n: int = 40
    rerank_model: str = "ms-marco-minilm-l6-v2"
    rerank_max_batch_size: int = 16
    rerank_max_sequence_length: int = 512
    # Weight given to the metadata bonus (heading/section similarity, continuity,
    # intent) when combined with the normalized cross-encoder score to produce
    # the final ranking. 0 disables blending and reproduces prior behaviour.
    rerank_metadata_bonus_weight: float = 0.25

    # Heading-aware semantic representation for retrieval quality.
    # Repeats a chunk's known section heading ahead of its body when building
    # embedding/BM25/reranker input so thematically-close sections stay
    # distinguishable. Citation/LLM `content` is never modified.
    heading_weighting_enabled: bool = True
    heading_weight_repetitions: int = 2

    # Query intelligence (Phase 12.9)
    query_intelligence_enabled: bool = True
    query_expansion_enabled: bool = True
    multi_query_enabled: bool = True
    max_generated_queries: int = 8
    entity_normalization_enabled: bool = True
    synonym_expansion_enabled: bool = True
    strategy_selection_enabled: bool = True

    # Knowledge Intelligence Engine (Phase 13.1) — Shadow Mode
    # When enabled, generates DocumentKnowledge objects in parallel with
    # legacy ingestion. Fail-open: never alters upload/API/retrieval behavior.
    knowledge_engine_shadow_enabled: bool = True
    knowledge_engine_llm_enrichment_enabled: bool = False

    # Knowledge Registry (Phase 13.2) — Shadow Mode organizational layer.
    # Registers Knowledge Objects into collections/taxonomy/health. Fail-open.
    # Nothing in production retrieval consumes registry data yet.
    knowledge_registry_shadow_enabled: bool = True

    # Knowledge Relationship Engine (Phase 13.3) — Shadow Mode.
    # Discovers relationships between Registry entries. Fail-open.
    # Nothing in production retrieval consumes relationship data yet.
    knowledge_relationship_shadow_enabled: bool = True

    # Hybrid Knowledge Index (Phase 13.4) — Shadow Mode.
    # Indexes Knowledge Objects / Registry / Relationships. Fail-open.
    # Nothing in production retrieval consumes these indexes yet.
    knowledge_index_shadow_enabled: bool = True

    # Intelligent Query Planner (Phase 13.5) — Shadow Mode.
    # Builds retrieval execution plans only. Never retrieves / never alters answers.
    query_planner_shadow_enabled: bool = True

    # Knowledge Execution Engine (Phase 13.6) — Shadow Mode.
    # Executes QueryExecutionPlans against Hybrid Indexes only. Fail-open.
    # Never calls FAISS/BM25/LLM; never influences production answers.
    knowledge_execution_shadow_enabled: bool = True

    # Knowledge Graph (Phase 13.7) — Shadow Mode.
    # Typed graph traversal/expansion for Shadow consumers only. Fail-open.
    knowledge_graph_shadow_enabled: bool = True

    # Worker Orchestration (Phase 13.8) — Shadow Mode.
    # Coordinates workers wrapping existing providers. Fail-open.
    # Not an AI agent runtime; never influences production answers.
    knowledge_orchestration_shadow_enabled: bool = True

    @model_validator(mode="after")
    def _require_real_jwt_secret(self) -> "Settings":
        """Fail startup if a non-development environment keeps the placeholder secret.

        The default `jwt_secret` value exists purely for local development
        convenience. Any other `app_env` must set a real `JWT_SECRET` via the
        environment — running with the placeholder (or an empty secret)
        outside development would let anyone forge valid access tokens.
        """
        if self.app_env != "development" and (
            not self.jwt_secret or self.jwt_secret == _DEFAULT_JWT_SECRET
        ):
            raise ValueError(
                "JWT_SECRET is missing or still set to the default placeholder "
                f"value. Set a unique, secret JWT_SECRET environment variable "
                f"before starting the application outside development "
                f"(APP_ENV={self.app_env!r})."
            )
        return self


@lru_cache
def get_settings() -> Settings:
    """Return cached settings instance."""
    return Settings()
