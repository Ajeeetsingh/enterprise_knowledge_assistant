"""Public Knowledge Graph service API."""

from __future__ import annotations

import time

from app.knowledge_graph.builders.builder import KnowledgeGraphBuilder
from app.knowledge_graph.diagnostics.report import GraphDiagnostics
from app.knowledge_graph.expansion.expander import GraphExpander
from app.knowledge_graph.graph.store import InMemoryGraph
from app.knowledge_graph.metrics.metrics import GraphMetrics
from app.knowledge_graph.models.enums import EdgeType, NodeType
from app.knowledge_graph.models.types import GraphEvidence, TraversalResult
from app.knowledge_graph.traversal.engine import GraphTraverser
from app.knowledge_graph.validators.graph_validator import GraphValidator
from app.knowledge_graph.version import KNOWLEDGE_GRAPH_PIPELINE_VERSION
from app.knowledge_index.models.types import IndexDocument
from app.knowledge_registry.types import RegistryEntry
from app.knowledge_relationships.types import KnowledgeRelationshipRecord


class KnowledgeGraphService:
    """Clean graph API for traversal and expansion (Shadow Mode consumers)."""

    def __init__(self, graph: InMemoryGraph | None = None) -> None:
        self._graph = graph or InMemoryGraph()
        self._builder = KnowledgeGraphBuilder()
        self._traveller = GraphTraverser()
        self._expander = GraphExpander(traveller=self._traveller)
        self._validator = GraphValidator()
        self._diagnostics = GraphDiagnostics(self._validator)
        self._metrics = GraphMetrics()
        self._last_build_ms = 0.0

    @property
    def version(self) -> str:
        return KNOWLEDGE_GRAPH_PIPELINE_VERSION

    @property
    def graph(self) -> InMemoryGraph:
        return self._graph

    @property
    def available(self) -> bool:
        return len(self._graph.node_ids()) > 0

    def rebuild(
        self,
        *,
        registry_entries: list[RegistryEntry],
        relationships: list[KnowledgeRelationshipRecord] | None = None,
        index_documents: list[IndexDocument] | None = None,
    ) -> dict:
        started = time.perf_counter()
        self._graph = self._builder.build(
            registry_entries=registry_entries,
            relationships=relationships,
            index_documents=index_documents,
        )
        self._last_build_ms = (time.perf_counter() - started) * 1000
        self._metrics.record_build(self._last_build_ms)
        return self.statistics()

    def upsert(
        self,
        entry: RegistryEntry,
        *,
        index_document: IndexDocument | None = None,
        relationships: list[KnowledgeRelationshipRecord] | None = None,
    ) -> None:
        self._builder.upsert_entry(
            self._graph,
            entry,
            index_document=index_document,
            relationships=relationships,
        )

    def expand_node(
        self,
        node_id: str,
        *,
        mode: str = "neighbors",
        max_depth: int = 2,
        edge_types: set[str] | None = None,
        min_confidence: float = 0.0,
    ) -> GraphEvidence:
        evidence = self._expander.expand(
            self._graph,
            [node_id],
            mode=mode,
            max_depth=max_depth,
            edge_types=edge_types,
            min_confidence=min_confidence,
        )
        self._metrics.record_expansion(evidence.elapsed_ms)
        return evidence

    def find_neighbors(self, node_id: str, *, edge_types: set[str] | None = None) -> list[str]:
        return self._traveller.neighbors(self._graph, node_id, edge_types=edge_types)

    def find_related(self, node_id: str, *, max_depth: int = 2) -> GraphEvidence:
        return self.expand_node(node_id, mode="relationship", max_depth=max_depth)

    def find_versions(self, node_id: str) -> GraphEvidence:
        return self.expand_node(node_id, mode="version", max_depth=2)

    def find_entities(self, node_id: str) -> GraphEvidence:
        return self.expand_node(node_id, mode="entity", max_depth=1)

    def find_policies(self, node_id: str) -> GraphEvidence:
        return self.expand_node(
            node_id,
            mode="relationship",
            max_depth=2,
            edge_types={
                EdgeType.GOVERNS.value,
                EdgeType.REFERENCES.value,
                EdgeType.RELATED_TO.value,
                EdgeType.SAME_TAXONOMY.value,
            },
        )

    def traverse(
        self,
        node_id: str,
        *,
        max_depth: int = 2,
        edge_types: set[str] | None = None,
        node_types: set[str] | None = None,
        min_confidence: float = 0.0,
        budget: int = 100,
        direction: str = "out",
    ) -> TraversalResult:
        result = self._traveller.traverse(
            self._graph,
            node_id,
            max_depth=max_depth,
            budget=budget,
            min_confidence=min_confidence,
            edge_types=edge_types,
            node_types=node_types,
            direction=direction,
            weighted=True,
        )
        self._metrics.record_traversal(result.elapsed_ms)
        return result

    def inspect_node(self, node_id: str) -> dict | None:
        node = self._graph.get_node(node_id)
        if node is None:
            return None
        return {
            "node": node.to_dict(),
            "neighbors": self.find_neighbors(node_id),
            "incoming": [edge.to_dict() for edge in self._graph.incoming_edges(node_id)],
            "outgoing": [edge.to_dict() for edge in self._graph.outgoing_edges(node_id)],
            "relationship_types": sorted(
                {
                    edge.type
                    for edge in self._graph.incoming_edges(node_id) + self._graph.outgoing_edges(node_id)
                }
            ),
        }

    def statistics(self) -> dict:
        stats = self._validator.statistics(self._graph, build_time_ms=self._last_build_ms)
        return stats.to_dict()

    def diagnostics(self) -> dict:
        return self._diagnostics.report(self._graph)

    def metrics(self) -> dict:
        return self._metrics.to_dict()

    @staticmethod
    def knowledge_object_node_id(knowledge_id: str) -> str:
        return f"ko:{knowledge_id}"
