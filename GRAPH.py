"""
Knowledge Graph

A directed graph where nodes are concepts and edges encode dependencies.

Design decisions:
- Graph is held in memory during runtime (NetworkX) for fast traversal
- Persisted to PostgreSQL for durability
- Seeded from JSON domain files in learning/knowledge_graph/seeds/
- Traversal algorithms are separated from storage (graph.py vs traversal.py)
"""

import networkx as nx
from dataclasses import dataclass, field
from typing import Optional
import json
import logging

logger = logging.getLogger(__name__)


@dataclass
class Concept:
    id: str
    name: str
    domain: str
    difficulty: float = 0.5          # [0, 1]
    estimated_minutes: int = 20
    description: str = ""
    core_explanation: str = ""
    common_misconceptions: list = field(default_factory=list)
    tags: list = field(default_factory=list)


@dataclass
class ConceptEdge:
    source_id: str
    target_id: str
    relation_type: str = "prerequisite"   # prerequisite | related | application_of
    strength: float = 1.0


class KnowledgeGraph:
    """
    In-memory knowledge graph backed by NetworkX.
    
    Convention: edge A -> B means "A is a prerequisite of B"
    i.e., you should know A before learning B.
    """

    def __init__(self):
        self._graph: nx.DiGraph = nx.DiGraph()
        self._concepts: dict[str, Concept] = {}

    def add_concept(self, concept: Concept) -> None:
        self._concepts[concept.id] = concept
        self._graph.add_node(
            concept.id,
            name=concept.name,
            domain=concept.domain,
            difficulty=concept.difficulty,
        )

    def add_edge(self, edge: ConceptEdge) -> None:
        if edge.source_id not in self._graph:
            raise ValueError(f"Source concept not found: {edge.source_id}")
        if edge.target_id not in self._graph:
            raise ValueError(f"Target concept not found: {edge.target_id}")
        
        self._graph.add_edge(
            edge.source_id,
            edge.target_id,
            relation_type=edge.relation_type,
            strength=edge.strength,
        )

    def get_concept(self, concept_id: str) -> Optional[Concept]:
        return self._concepts.get(concept_id)

    def get_prerequisites(self, concept_id: str, direct_only: bool = True) -> list[str]:
        """
        Returns concepts that must be known before concept_id.
        If direct_only=False, returns all transitive prerequisites.
        """
        if direct_only:
            return list(self._graph.predecessors(concept_id))
        else:
            # All ancestors in the prerequisite graph
            return list(nx.ancestors(self._graph, concept_id))

    def get_dependents(self, concept_id: str) -> list[str]:
        """Returns concepts that have concept_id as a prerequisite."""
        return list(self._graph.successors(concept_id))

    def get_learning_path(
        self,
        goal_concept_id: str,
        known_concept_ids: set[str],
        max_path_length: int = 20,
    ) -> list[str]:
        """
        Returns an ordered list of concepts to learn, starting from the learner's
        current knowledge state and ending at the goal concept.
        
        Algorithm:
        1. Find all prerequisites of goal (transitive)
        2. Remove concepts already known
        3. Topological sort remaining concepts
        4. Return the ordered sequence
        
        This is the core curriculum synthesis operation.
        """
        if goal_concept_id not in self._graph:
            raise ValueError(f"Goal concept not in graph: {goal_concept_id}")

        all_prerequisites = nx.ancestors(self._graph, goal_concept_id)
        all_prerequisites.add(goal_concept_id)
        
        # Remove what learner already knows
        unknown = all_prerequisites - known_concept_ids
        
        if not unknown:
            return []  # Learner already knows everything needed
        
        # Subgraph of only the unknown concepts
        subgraph = self._graph.subgraph(unknown)
        
        # Topological sort gives a valid learning order
        try:
            ordered = list(nx.topological_sort(subgraph))
        except nx.NetworkXUnfeasible:
            logger.warning(f"Cycle detected in knowledge graph for goal {goal_concept_id}")
            ordered = list(unknown)
        
        return ordered[:max_path_length]

    def get_next_learnable_concepts(
        self,
        known_concept_ids: set[str],
        domain: Optional[str] = None,
        top_n: int = 5,
    ) -> list[str]:
        """
        Returns concepts where all prerequisites are satisfied.
        These are the frontier: learnable now given current knowledge state.
        
        Sorted by difficulty (easiest first) to minimize frustration.
        """
        candidates = []
        
        for concept_id in self._graph.nodes:
            if concept_id in known_concept_ids:
                continue
            
            if domain and self._graph.nodes[concept_id].get("domain") != domain:
                continue
            
            prerequisites = set(self._graph.predecessors(concept_id))
            if prerequisites.issubset(known_concept_ids):
                difficulty = self._graph.nodes[concept_id].get("difficulty", 0.5)
                candidates.append((concept_id, difficulty))
        
        candidates.sort(key=lambda x: x[1])
        return [cid for cid, _ in candidates[:top_n]]

    def find_blocking_concept(
        self,
        target_concept_id: str,
        known_concept_ids: set[str],
    ) -> Optional[str]:
        """
        Given a concept the learner is struggling with, find the most likely
        prerequisite gap causing the struggle.
        
        Returns the deepest unfulfilled prerequisite — the root cause,
        not the immediate symptom.
        """
        direct_prereqs = self.get_prerequisites(target_concept_id, direct_only=True)
        unknown_prereqs = [p for p in direct_prereqs if p not in known_concept_ids]
        
        if not unknown_prereqs:
            return None  # Prerequisites are met; the issue is with the concept itself
        
        # Recurse to find the deepest gap
        for prereq_id in unknown_prereqs:
            deeper = self.find_blocking_concept(prereq_id, known_concept_ids)
            if deeper:
                return deeper
        
        # Return the unknown prereq with highest difficulty (most likely to be the issue)
        unknown_prereqs.sort(
            key=lambda p: self._graph.nodes[p].get("difficulty", 0),
            reverse=True,
        )
        return unknown_prereqs[0]

    def domain_coverage(self, known_concept_ids: set[str], domain: str) -> float:
        """Returns fraction of domain concepts known. [0, 1]"""
        domain_concepts = {
            n for n in self._graph.nodes
            if self._graph.nodes[n].get("domain") == domain
        }
        if not domain_concepts:
            return 0.0
        known_in_domain = domain_concepts & known_concept_ids
        return len(known_in_domain) / len(domain_concepts)

    def load_from_dict(self, data: dict) -> None:
        """
        Load a knowledge graph from the seed JSON format.
        See learning/knowledge_graph/seeds/ for format examples.
        """
        for c in data.get("concepts", []):
            self.add_concept(Concept(
                id=c["id"],
                name=c["name"],
                domain=data.get("domain", "unknown"),
                difficulty=c.get("difficulty", 0.5),
                estimated_minutes=c.get("estimated_minutes", 20),
                description=c.get("description", ""),
                core_explanation=c.get("core_explanation", ""),
                common_misconceptions=c.get("common_misconceptions", []),
                tags=c.get("tags", []),
            ))
        
        for e in data.get("edges", []):
            self.add_edge(ConceptEdge(
                source_id=e["from"],
                target_id=e["to"],
                relation_type=e.get("type", "prerequisite"),
                strength=e.get("strength", 1.0),
            ))
        
        logger.info(
            f"Loaded knowledge graph: {len(self._concepts)} concepts, "
            f"{self._graph.number_of_edges()} edges"
        )

    def load_from_json(self, path: str) -> None:
        with open(path) as f:
            data = json.load(f)
        self.load_from_dict(data)

    def stats(self) -> dict:
        return {
            "concept_count": len(self._concepts),
            "edge_count": self._graph.number_of_edges(),
            "domains": list({c.domain for c in self._concepts.values()}),
            "max_depth": (
                nx.dag_longest_path_length(self._graph)
                if nx.is_directed_acyclic_graph(self._graph) else "cyclic"
            ),
        }


# Singleton instance — shared across the application
_graph_instance: Optional[KnowledgeGraph] = None


def get_knowledge_graph() -> KnowledgeGraph:
    global _graph_instance
    if _graph_instance is None:
        _graph_instance = KnowledgeGraph()
    return _graph_instance
