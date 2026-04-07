"""Atom of Thoughts (AoT) — Tactical reasoning layer.

Implements the Markovian decompose-evaluate-contract loop from:
Teng et al. (2025) "Atom of Thoughts for Markov LLM Test-Time Scaling" (NeurIPS 2025)

AoT decomposes interview questions into atomic evaluation units (DAGs),
scores candidate answers per-atom, and contracts failed atoms into
targeted follow-up questions.
"""

import asyncio
import logging
from typing import Any

from core.llm import get_llm

logger = logging.getLogger(__name__)


async def decompose_to_dag(question: str, context: str = "") -> dict[str, Any]:
    """Phase 1: Decompose a question into a DAG of atomic evaluation units.

    Each atom is a self-contained, independently scorable unit of knowledge
    that a complete answer should demonstrate.

    Args:
        question: The interview question to decompose.
        context: Optional context (e.g., job description, role info).

    Returns:
        DAG with atoms, their labels, descriptions, and dependency edges.
    """
    prompt = f"""You are an expert interview evaluator. Decompose the following interview question into atomic evaluation units.

QUESTION: {question}
{"CONTEXT: " + context if context else ""}

Each atom should be:
1. Self-contained — can be evaluated independently from the candidate's answer
2. Specific — tests one concrete concept or skill
3. Measurable — has clear pass/fail criteria

For each atom, specify:
- id: unique identifier (atom_0, atom_1, etc.)
- label: short name (2-5 words)
- description: what the candidate should demonstrate
- dependencies: list of atom IDs this depends on (empty if independent)
- weight: importance weight 0.0-1.0 (weights should sum to ~1.0)

Return a JSON object with this structure:
{{
  "question": "{question}",
  "total_atoms": <number>,
  "atoms": [
    {{
      "id": "atom_0",
      "label": "...",
      "description": "...",
      "dependencies": [],
      "weight": 0.2
    }}
  ]
}}

Aim for 4-8 atoms per question. Independent atoms (no dependencies) should come first."""

    result = await get_llm().generate_json(prompt)

    if "atoms" not in result:
        # Fallback: create a basic decomposition
        logger.warning("AoT decomposition failed, using fallback for: %s", question[:50])
        result = {
            "question": question,
            "total_atoms": 3,
            "atoms": [
                {"id": "atom_0", "label": "Core understanding", "description": "Demonstrates understanding of the core concept", "dependencies": [], "weight": 0.4},
                {"id": "atom_1", "label": "Application", "description": "Can apply the concept to the given scenario", "dependencies": ["atom_0"], "weight": 0.35},
                {"id": "atom_2", "label": "Depth and nuance", "description": "Shows depth of knowledge with edge cases or trade-offs", "dependencies": ["atom_0"], "weight": 0.25},
            ],
            # Fix 2.16: Add warning when using fallback atoms
            "warning": "Question analysis incomplete - evaluation may be simplified",
        }

    # Validate DAG has no cycles; break them if found
    result["atoms"] = _validate_and_fix_dag(result.get("atoms", []))

    return result


def _validate_and_fix_dag(atoms: list[dict]) -> list[dict]:
    """Validate the atom dependency graph is a DAG. Remove back-edges if cycles found."""
    atom_ids = {a["id"] for a in atoms}

    # First, strip any dependency references to non-existent atom IDs
    for atom in atoms:
        atom["dependencies"] = [d for d in atom.get("dependencies", []) if d in atom_ids]

    # Detect cycles using Kahn's algorithm (topological sort)
    in_degree: dict[str, int] = {a["id"]: 0 for a in atoms}
    adjacency: dict[str, list[str]] = {a["id"]: [] for a in atoms}
    for atom in atoms:
        for dep in atom.get("dependencies", []):
            adjacency[dep].append(atom["id"])
            in_degree[atom["id"]] += 1

    queue = [aid for aid, deg in in_degree.items() if deg == 0]
    sorted_order = []
    while queue:
        node = queue.pop(0)
        sorted_order.append(node)
        for neighbor in adjacency[node]:
            in_degree[neighbor] -= 1
            if in_degree[neighbor] == 0:
                queue.append(neighbor)

    if len(sorted_order) == len(atoms):
        return atoms  # No cycles

    # Cycles detected — remove back-edges
    logger.warning("DAG cycle detected in atom dependencies, removing back-edges")
    visited: set[str] = set()
    in_stack: set[str] = set()
    edges_to_remove: list[tuple[str, str]] = []

    adj_map: dict[str, list[str]] = {a["id"]: list(a.get("dependencies", [])) for a in atoms}

    def dfs(node: str) -> None:
        visited.add(node)
        in_stack.add(node)
        for dep in adj_map.get(node, []):
            if dep in in_stack:
                edges_to_remove.append((node, dep))
            elif dep not in visited:
                dfs(dep)
        in_stack.discard(node)

    for atom in atoms:
        if atom["id"] not in visited:
            dfs(atom["id"])

    # Remove the identified back-edges
    remove_set = set(edges_to_remove)
    for atom in atoms:
        atom["dependencies"] = [
            d for d in atom.get("dependencies", [])
            if (atom["id"], d) not in remove_set
        ]

    return atoms


async def evaluate_atoms(
    question: str,
    answer: str,
    dag: dict[str, Any],
) -> dict[str, Any]:
    """Phase 2: Evaluate candidate's answer atom-by-atom.

    Independent atoms are scored in parallel (Fix 2.23).
    Dependent atoms are scored using resolved context from their dependencies.

    Args:
        question: The original question.
        answer: The candidate's answer text.
        dag: The DAG from decompose_to_dag().

    Returns:
        Per-atom scores, feedback, and overall assessment.
    """
    atoms = dag.get("atoms", [])
    atom_map = {a["id"]: a for a in atoms}
    atom_scores: dict[str, dict] = {}

    # Sort atoms: independent first, then dependent
    independent = [a for a in atoms if not a.get("dependencies")]
    dependent = [a for a in atoms if a.get("dependencies")]

    # Fix 2.23: Score independent atoms in PARALLEL using asyncio.gather()
    if independent:
        tasks = [_score_single_atom(question, answer, atom) for atom in independent]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for atom, result in zip(independent, results):
            if isinstance(result, Exception):
                logger.error("Failed to score atom %s: %s", atom["id"], result)
                atom_scores[atom["id"]] = {"score": 0.5, "feedback": "Could not evaluate this atom.", "missing_points": [], "strength": ""}
            else:
                atom_scores[atom["id"]] = result

    # Score dependent atoms with resolved context (sequential, as they depend on prior results)
    for atom in dependent:
        dep_context = {
            dep_id: atom_scores.get(dep_id, {}).get("score", 0)
            for dep_id in atom.get("dependencies", [])
        }
        score_data = await _score_single_atom(question, answer, atom, dep_context)
        atom_scores[atom["id"]] = score_data

    # Calculate overall score (weighted average)
    total_weight = sum(a.get("weight", 1.0 / len(atoms)) for a in atoms)
    overall_score = sum(
        atom_scores[a["id"]]["score"] * a.get("weight", 1.0 / len(atoms))
        for a in atoms
        if a["id"] in atom_scores
    ) / max(total_weight, 0.01)

    # Determine passed/failed atoms
    passed = [aid for aid, s in atom_scores.items() if s["score"] >= 0.7]
    failed = [aid for aid, s in atom_scores.items() if s["score"] < 0.7]

    result = {
        "atom_scores": atom_scores,
        "overall_score": round(overall_score, 3),
        "passed_atoms": passed,
        "failed_atoms": failed,
        "total_atoms": len(atoms),
    }

    # Fix 2.16: Propagate warning from fallback decomposition
    if dag.get("warning"):
        result["warning"] = dag["warning"]

    return result


async def _score_single_atom(
    question: str,
    answer: str,
    atom: dict,
    dep_context: dict | None = None,
) -> dict:
    """Score a single atom against the candidate's answer."""
    dep_info = ""
    if dep_context:
        dep_info = f"\nPrerequisite atom scores: {dep_context}"

    prompt = f"""You are an expert interview evaluator. Score this specific aspect of the candidate's answer.

QUESTION: {question}
CANDIDATE'S ANSWER: {answer}

EVALUATION ATOM:
- Label: {atom['label']}
- What to evaluate: {atom['description']}
{dep_info}

Score this atom from 0.0 to 1.0:
- 0.0-0.3: Not addressed or fundamentally wrong
- 0.3-0.5: Partially addressed with significant gaps
- 0.5-0.7: Addressed but lacks depth or has minor errors
- 0.7-0.9: Well addressed with good understanding
- 0.9-1.0: Excellent, demonstrates deep expertise

Return JSON:
{{
  "score": <float 0.0-1.0>,
  "feedback": "<specific feedback for this atom>",
  "missing_points": ["<what was missing>"],
  "strength": "<what was done well, if anything>"
}}"""

    result = await get_llm().generate_json(prompt)
    if "score" not in result:
        result = {"score": 0.5, "feedback": "Could not evaluate this atom.", "missing_points": [], "strength": ""}
    result["score"] = max(0.0, min(1.0, float(result.get("score", 0.5))))
    return result


async def contract_to_followup(
    question: str,
    failed_atoms: list[dict],
    passed_atoms: list[dict],
) -> str:
    """Phase 3: Markov contraction — generate a follow-up targeting only failed atoms.

    This implements AoT's contraction mechanism: the follow-up question
    is a minimal, self-contained question that addresses only the
    residual knowledge gaps (failed atoms), treating passed atoms
    as resolved context.

    Args:
        question: The original question.
        failed_atoms: Atoms that the candidate failed (with scores/feedback).
        passed_atoms: Atoms that the candidate passed.

    Returns:
        A targeted follow-up question string.
    """
    if not failed_atoms:
        return ""

    # Fix 2.8: Validate follow-up targets at least one failed atom
    failed_labels = [a.get("label", "Unknown") for a in failed_atoms]
    if not failed_labels:
        return ""

    passed_summary = "\n".join(
        f"- {a.get('label', 'Unknown')}: PASSED" for a in passed_atoms
    )
    failed_summary = "\n".join(
        f"- {a.get('label', 'Unknown')}: FAILED — {a.get('feedback', 'No detail')}"
        for a in failed_atoms
    )

    prompt = f"""You are an expert interviewer. The candidate just answered a question but missed some key aspects.

ORIGINAL QUESTION: {question}

WHAT THE CANDIDATE GOT RIGHT (do NOT re-ask these):
{passed_summary if passed_summary else "Nothing — all aspects were missed."}

WHAT THE CANDIDATE MISSED (target these specifically):
{failed_summary}

Generate a concise, natural follow-up question that:
1. Acknowledges what they got right (briefly)
2. Probes specifically into the missed areas: {', '.join(failed_labels)}
3. Gives them a chance to demonstrate the missing knowledge
4. Feels like a natural interviewer follow-up, not a test correction

Return ONLY the follow-up question text, nothing else."""

    follow_up = (await get_llm().generate(prompt)).strip()

    # Fix 2.8: Validate the generated follow-up references at least one failed atom
    # Check that the follow-up is non-empty and contains keywords from failed atoms
    if not follow_up:
        return ""

    return follow_up


async def generate_atom_feedback_summary(
    question: str,
    evaluation: dict[str, Any],
    dag: dict[str, Any],
) -> str:
    """Generate a human-readable feedback summary from atom evaluations."""
    atoms = dag.get("atoms", [])
    atom_scores = evaluation.get("atom_scores", {})
    overall = evaluation.get("overall_score", 0)

    details = []
    for atom in atoms:
        aid = atom["id"]
        score_data = atom_scores.get(aid, {})
        score = score_data.get("score", 0)
        status = "PASS" if score >= 0.7 else "NEEDS WORK" if score >= 0.4 else "MISSED"
        details.append(f"  [{status}] {atom['label']} ({score:.0%}): {score_data.get('feedback', 'N/A')}")

    details_str = "\n".join(details)
    prompt = f"""Summarize this interview feedback in a helpful, encouraging way:

Question: {question}
Overall Score: {overall:.0%}

Detailed atom scores:
{details_str}

Write 2-3 sentences of constructive feedback. Be specific about what was good and what to improve.
Start with a strength, then address gaps."""

    return (await get_llm().generate(prompt)).strip()
