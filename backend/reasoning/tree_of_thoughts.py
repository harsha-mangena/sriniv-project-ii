"""Tree of Thoughts (ToT) — Strategic reasoning layer.

Implements branching question selection from:
Yao et al. (2023) "Tree of Thoughts: Deliberate Problem Solving with LLMs" (NeurIPS 2023)

ToT maintains a question tree, evaluates which branch is most informative
for the candidate, and supports backtracking when difficulty is mismatched.
"""

import logging
import random
from typing import Any, Optional

from core.llm import llm

logger = logging.getLogger(__name__)


class QuestionNode:
    """A node in the ToT question tree."""

    def __init__(
        self,
        node_id: str,
        category: str,
        subcategory: str,
        question_template: str,
        difficulty: int,
        target_atoms: list[str],
        children: Optional[list["QuestionNode"]] = None,
        parent_id: Optional[str] = None,
    ):
        self.node_id = node_id
        self.category = category
        self.subcategory = subcategory
        self.question_template = question_template
        self.difficulty = difficulty  # 1-5
        self.target_atoms = target_atoms
        self.children = children or []
        self.parent_id = parent_id
        self.visited = False
        self.score: Optional[float] = None  # LLM evaluation score

    def to_dict(self) -> dict:
        return {
            "node_id": self.node_id,
            "category": self.category,
            "subcategory": self.subcategory,
            "question_template": self.question_template,
            "difficulty": self.difficulty,
            "target_atoms": self.target_atoms,
            "visited": self.visited,
            "score": self.score,
        }


class QuestionTree:
    """ToT question tree for interview navigation."""

    def __init__(self):
        self.root: Optional[QuestionNode] = None
        self.nodes: dict[str, QuestionNode] = {}
        self.visit_history: list[str] = []

    def add_node(self, node: QuestionNode) -> None:
        self.nodes[node.node_id] = node
        if self.root is None:
            self.root = node

    def get_frontier(self, skill_profile: dict[str, float]) -> list[QuestionNode]:
        """Get unvisited nodes at the current frontier (BFS-style).

        Frontier = unvisited nodes whose parents (if any) have been visited,
        OR root-level category nodes that haven't been explored.
        """
        frontier = []
        for node in self.nodes.values():
            if node.visited:
                continue
            if node.parent_id is None:
                frontier.append(node)
            elif node.parent_id in self.nodes and self.nodes[node.parent_id].visited:
                frontier.append(node)
        return frontier

    def mark_visited(self, node_id: str, score: float) -> None:
        if node_id in self.nodes:
            self.nodes[node_id].visited = True
            self.nodes[node_id].score = score
            self.visit_history.append(node_id)

    def backtrack(self) -> Optional[QuestionNode]:
        """Backtrack to the parent of the last visited node."""
        if not self.visit_history:
            return None
        last_id = self.visit_history[-1]
        last_node = self.nodes.get(last_id)
        if last_node and last_node.parent_id:
            parent = self.nodes.get(last_node.parent_id)
            if parent:
                # Find unvisited siblings
                siblings = [
                    n for n in self.nodes.values()
                    if n.parent_id == last_node.parent_id and not n.visited
                ]
                if siblings:
                    return siblings[0]
        return None

    def get_coverage_stats(self) -> dict:
        visited = sum(1 for n in self.nodes.values() if n.visited)
        total = len(self.nodes)
        categories = set(n.category for n in self.nodes.values())
        covered_cats = set(
            n.category for n in self.nodes.values() if n.visited
        )
        return {
            "visited": visited,
            "total": total,
            "coverage_pct": visited / max(total, 1),
            "categories_total": len(categories),
            "categories_covered": len(covered_cats),
        }


async def build_question_tree(
    jd_context: str,
    resume_context: str,
    role_type: str = "Software Engineer",
    templates: list[dict] | None = None,
) -> QuestionTree:
    """Build a personalized question tree based on JD and resume.

    Uses LLM to generate role-specific question branches, then
    organizes them into a navigable tree structure.
    """
    tree = QuestionTree()

    # If templates are provided, use them to build the tree
    if templates:
        return _build_tree_from_templates(templates, jd_context)

    # Otherwise, generate questions via LLM
    prompt = f"""You are an expert interview designer. Create a structured interview question tree for:

ROLE: {role_type}
JOB DESCRIPTION SUMMARY: {jd_context[:1000]}
CANDIDATE RESUME SUMMARY: {resume_context[:1000]}

Generate a hierarchical question tree with these categories:
1. Behavioral (STAR format questions)
2. Technical (Data structures, algorithms, coding)
3. System Design
4. Role-Specific (based on the JD)

For each category, generate 3-5 questions at varying difficulty levels (1-5).

Return JSON:
{{
  "categories": [
    {{
      "name": "Behavioral",
      "questions": [
        {{
          "id": "beh_1",
          "subcategory": "Leadership",
          "question": "...",
          "difficulty": 2,
          "target_skills": ["leadership", "communication"]
        }}
      ]
    }}
  ]
}}"""

    result = await llm.generate_json(prompt)
    categories = result.get("categories", [])

    node_counter = 0
    for cat in categories:
        cat_name = cat.get("name", f"Category_{node_counter}")
        questions = cat.get("questions", [])
        for q in questions:
            node = QuestionNode(
                node_id=q.get("id", f"node_{node_counter}"),
                category=cat_name,
                subcategory=q.get("subcategory", "General"),
                question_template=q.get("question", ""),
                difficulty=q.get("difficulty", 3),
                target_atoms=q.get("target_skills", []),
            )
            tree.add_node(node)
            node_counter += 1

    logger.info("Built question tree with %d nodes across %d categories", len(tree.nodes), len(categories))
    return tree


def _build_tree_from_templates(templates: list[dict], jd_context: str) -> QuestionTree:
    """Build tree from predefined question templates."""
    tree = QuestionTree()
    for t in templates:
        node = QuestionNode(
            node_id=t["id"],
            category=t.get("category", "General"),
            subcategory=t.get("subcategory", ""),
            question_template=t.get("template_text", t.get("question", "")),
            difficulty=t.get("difficulty", 3),
            target_atoms=t.get("target_atoms", []),
            parent_id=t.get("parent_id"),
        )
        tree.add_node(node)
    return tree


async def evaluate_frontier_nodes(
    frontier: list[QuestionNode],
    skill_profile: dict[str, float],
    session_history: list[str],
) -> list[tuple[QuestionNode, float]]:
    """Use LLM to score each frontier node's informativeness.

    Implements ToT's state evaluation: "How informative is this question
    for assessing this candidate's gaps?"

    Args:
        frontier: Candidate question nodes.
        skill_profile: Current skill atom scores.
        session_history: Previously asked question IDs.

    Returns:
        List of (node, score) tuples, sorted by score descending.
    """
    if not frontier:
        return []

    # For efficiency, evaluate in a single LLM call
    nodes_desc = "\n".join(
        f"  {i+1}. [{n.node_id}] ({n.category}/{n.subcategory}, diff={n.difficulty}): {n.question_template[:100]}"
        for i, n in enumerate(frontier)
    )

    weak_skills = [k for k, v in skill_profile.items() if v < 0.6]
    strong_skills = [k for k, v in skill_profile.items() if v >= 0.8]

    prompt = f"""You are an expert interview strategist. Score each candidate question for how INFORMATIVE it would be to ask this candidate.

CANDIDATE PROFILE:
- Weak areas: {weak_skills if weak_skills else 'None identified yet'}
- Strong areas: {strong_skills if strong_skills else 'None identified yet'}
- Already asked: {len(session_history)} questions

CANDIDATE QUESTIONS:
{nodes_desc}

Score each from 1-10 on informativeness. Consider:
- Does it target a known weak area? (higher score)
- Is the difficulty appropriate? (higher score)
- Does it avoid redundancy with already-assessed topics? (higher score)
- Does it cover an unexplored category? (higher score)

Return JSON:
{{
  "scores": [
    {{"id": "...", "score": <1-10>, "reason": "..."}}
  ]
}}"""

    result = await llm.generate_json(prompt)
    scores_list = result.get("scores", [])
    score_map = {s["id"]: s.get("score", 5) for s in scores_list}

    scored = []
    for node in frontier:
        s = score_map.get(node.node_id, 5.0 + random.uniform(-1, 1))
        scored.append((node, float(s)))

    scored.sort(key=lambda x: x[1], reverse=True)
    return scored


async def select_next_question(
    tree: QuestionTree,
    skill_profile: dict[str, float],
    session_history: list[str],
    strategy: str = "bfs",
) -> Optional[QuestionNode]:
    """Select the next question using ToT search strategy.

    BFS: Evaluate all frontier nodes, pick the best.
    DFS: Go deeper into the current best branch.

    Args:
        tree: The question tree.
        skill_profile: Current skill scores.
        session_history: Already asked question IDs.
        strategy: "bfs" or "dfs".

    Returns:
        The selected QuestionNode, or None if tree is exhausted.
    """
    frontier = tree.get_frontier(skill_profile)
    if not frontier:
        logger.info("Question tree exhausted — no more frontier nodes.")
        return None

    if strategy == "dfs" and tree.visit_history:
        # DFS: prefer children of the last visited node
        last_id = tree.visit_history[-1]
        children_in_frontier = [n for n in frontier if n.parent_id == last_id]
        if children_in_frontier:
            frontier = children_in_frontier

    scored = await evaluate_frontier_nodes(frontier, skill_profile, session_history)
    if scored:
        selected = scored[0][0]
        logger.info("ToT selected: %s (score=%.1f, category=%s)", selected.node_id, scored[0][1], selected.category)
        return selected

    return frontier[0] if frontier else None


async def personalize_question(
    template: str,
    resume_context: str,
    jd_context: str,
) -> str:
    """Personalize a question template using resume and JD context.

    Uses RAG-retrieved context to make generic templates specific
    to the candidate's background.
    """
    prompt = f"""You are an expert interviewer. Personalize this question template for the specific candidate.

TEMPLATE: {template}
CANDIDATE BACKGROUND: {resume_context[:500]}
JOB REQUIREMENTS: {jd_context[:500]}

Rewrite the question to:
1. Reference specific technologies/projects from their resume when relevant
2. Align with the job requirements
3. Sound natural and conversational
4. Maintain the same difficulty level and intent

Return ONLY the personalized question text."""

    return (await llm.generate(prompt)).strip()
