"""Tests for the triple-audit fixes."""

import ast
import inspect
import json
import warnings

import pytest


# === P0-1: Fix llm.generate_json -> get_llm().generate_json in questions.py ===

class TestQuestionsLLMFix:
    """Verify the bare `llm` reference in questions.py is fixed."""

    def test_no_bare_llm_variable_in_questions(self):
        """Ensure questions.py never uses bare `llm.` — always get_llm()."""
        import importlib
        source = inspect.getsource(importlib.import_module("api.questions"))
        # Parse into AST and check for bare 'llm' attribute access
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
                assert node.value.id != "llm", (
                    f"Found bare `llm.{node.attr}` at line {node.lineno}. "
                    "Should use `get_llm().{node.attr}` instead."
                )

    def test_get_llm_is_imported(self):
        """Ensure get_llm is imported in the questions module."""
        from api import questions
        source = inspect.getsource(questions)
        assert "from core.llm import get_llm" in source


# === P0-2: Requirements cleanup ===

class TestRequirements:
    """Verify requirements.txt is clean."""

    def test_no_llama_index(self):
        """llama-index and its sub-packages should be removed."""
        with open("requirements.txt") as f:
            contents = f.read()
        assert "llama-index" not in contents, "llama-index should be removed (unused)"

    def test_no_python_jose(self):
        """python-jose should be removed (JWT auth never implemented)."""
        with open("requirements.txt") as f:
            contents = f.read()
        assert "python-jose" not in contents, "python-jose should be removed (unused)"

    def test_no_websockets(self):
        """websockets should be removed (FastAPI uses Starlette's built-in)."""
        with open("requirements.txt") as f:
            contents = f.read()
        assert "websockets" not in contents, "websockets should be removed (unused)"

    def test_numpy_pinned(self):
        """numpy should be pinned below 2.0 for chromadb compatibility."""
        with open("requirements.txt") as f:
            contents = f.read()
        assert "numpy<2.0" in contents, "numpy<2.0 required for chromadb 0.5.0"


# === P1-4: Profile builder works with flat session rows ===

class TestProfileBuilder:
    """Verify profile builder works with flat session rows + atom scores."""

    def test_empty_history(self):
        from analysis.profile_builder import build_learning_profile
        result = build_learning_profile([])
        assert result["total_sessions"] == 0
        assert result["category_scores"] == {}
        assert result["top_strengths"] == []
        assert result["top_weaknesses"] == []

    def test_flat_session_rows(self):
        """Profile builder should work with flat rows from get_session_history()."""
        from analysis.profile_builder import build_learning_profile
        sessions = [
            {"id": "s1", "overall_score": 0.8, "question_count": 5, "mode": "mock"},
            {"id": "s2", "overall_score": 0.6, "question_count": 3, "mode": "mock"},
        ]
        result = build_learning_profile(sessions)
        assert result["total_sessions"] == 2
        assert result["total_questions"] == 8
        assert 0.69 < result["avg_score"] < 0.71

    def test_with_atom_scores(self):
        """Profile builder should use atom_scores for category breakdowns."""
        from analysis.profile_builder import build_learning_profile
        sessions = [
            {"id": "s1", "overall_score": 0.75, "question_count": 5},
        ]
        atom_scores = [
            {"atom_id": "a1", "atom_name": "Arrays", "category": "DSA", "avg_score": 0.9, "attempts": 3, "times_passed": 2},
            {"atom_id": "a2", "atom_name": "Trees", "category": "DSA", "avg_score": 0.5, "attempts": 2, "times_passed": 0},
            {"atom_id": "a3", "atom_name": "REST APIs", "category": "Backend", "avg_score": 0.8, "attempts": 1, "times_passed": 1},
        ]
        result = build_learning_profile(sessions, atom_scores=atom_scores)
        assert "DSA" in result["category_scores"]
        assert "Backend" in result["category_scores"]
        # DSA average = (0.9 + 0.5) / 2 = 0.7
        assert abs(result["category_scores"]["DSA"] - 0.7) < 0.01
        assert result["category_scores"]["Backend"] == 0.8

    def test_strengths_and_weaknesses_populated(self):
        """With proper atom_scores, strengths/weaknesses should be non-empty."""
        from analysis.profile_builder import build_learning_profile
        sessions = [{"id": "s1", "overall_score": 0.6, "question_count": 10}]
        atom_scores = [
            {"atom_id": "a1", "atom_name": "X", "category": "Strong Cat", "avg_score": 0.85, "attempts": 5, "times_passed": 4},
            {"atom_id": "a2", "atom_name": "Y", "category": "Weak Cat", "avg_score": 0.3, "attempts": 5, "times_passed": 0},
        ]
        result = build_learning_profile(sessions, atom_scores=atom_scores)
        assert len(result["top_strengths"]) > 0
        assert len(result["top_weaknesses"]) > 0
        assert result["top_strengths"][0]["category"] == "Strong Cat"
        assert result["top_weaknesses"][0]["category"] == "Weak Cat"


# === P1-5: Answer FK linkage ===

class TestAnswerFKLinkage:
    """Verify interview.py uses DB question IDs, not ToT node IDs."""

    def test_current_db_question_ids_dict_exists(self):
        from api import interview
        assert hasattr(interview, "current_db_question_ids")
        assert isinstance(interview.current_db_question_ids, dict)

    def test_submit_answer_uses_db_question_id(self):
        """The submit_answer function should reference current_db_question_ids."""
        from api import interview
        source = inspect.getsource(interview.submit_answer)
        assert "current_db_question_ids" in source
        # Should NOT use node_id for the question FK
        assert 'get("node_id"' not in source


# === P1-6: Pydantic model_answer renamed to sample_answer ===

class TestPydanticModelAnswerFix:
    """Verify model_answer renamed to sample_answer in PrepQuestionItem."""

    def test_no_model_answer_field(self):
        from models.schemas import PrepQuestionItem
        fields = PrepQuestionItem.model_fields
        assert "model_answer" not in fields, "model_answer should be renamed to sample_answer"

    def test_sample_answer_field_exists(self):
        from models.schemas import PrepQuestionItem
        fields = PrepQuestionItem.model_fields
        assert "sample_answer" in fields

    def test_no_pydantic_warning(self):
        """Creating PrepQuestionItem should not trigger model_ namespace warnings."""
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            from models.schemas import PrepQuestionItem
            item = PrepQuestionItem(
                question="Test?",
                category="Technical",
                difficulty=3,
                sample_answer="Answer",
                talking_points=["a", "b"],
                target_skills=["c"],
            )
            model_warnings = [x for x in w if "model_" in str(x.message)]
            assert len(model_warnings) == 0, f"Got Pydantic model_ warnings: {model_warnings}"


# === P2-7: DAG cycle validation ===

class TestDAGCycleValidation:
    """Verify DAG cycle detection and back-edge removal."""

    def test_acyclic_dag_unchanged(self):
        from reasoning.atom_of_thoughts import _validate_and_fix_dag
        atoms = [
            {"id": "a0", "label": "X", "dependencies": []},
            {"id": "a1", "label": "Y", "dependencies": ["a0"]},
            {"id": "a2", "label": "Z", "dependencies": ["a0", "a1"]},
        ]
        result = _validate_and_fix_dag(atoms)
        # No changes needed
        assert result[0]["dependencies"] == []
        assert result[1]["dependencies"] == ["a0"]
        assert result[2]["dependencies"] == ["a0", "a1"]

    def test_cycle_detected_and_broken(self):
        from reasoning.atom_of_thoughts import _validate_and_fix_dag
        # Create a cycle: a0 -> a1 -> a2 -> a0
        atoms = [
            {"id": "a0", "label": "X", "dependencies": ["a2"]},
            {"id": "a1", "label": "Y", "dependencies": ["a0"]},
            {"id": "a2", "label": "Z", "dependencies": ["a1"]},
        ]
        result = _validate_and_fix_dag(atoms)
        # After fixing, at least one back-edge should be removed
        # Verify the result is now a valid DAG (topological sort succeeds)
        in_degree = {a["id"]: 0 for a in result}
        for a in result:
            for dep in a["dependencies"]:
                in_degree[a["id"]] += 1
        queue = [aid for aid, deg in in_degree.items() if deg == 0]
        sorted_nodes = []
        adj = {a["id"]: [] for a in result}
        for a in result:
            for dep in a["dependencies"]:
                adj[dep].append(a["id"])
        queue = [aid for aid, deg in in_degree.items() if deg == 0]
        while queue:
            node = queue.pop(0)
            sorted_nodes.append(node)
            for neighbor in adj[node]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)
        assert len(sorted_nodes) == len(result), "DAG should be acyclic after fix"

    def test_nonexistent_dependency_stripped(self):
        from reasoning.atom_of_thoughts import _validate_and_fix_dag
        atoms = [
            {"id": "a0", "label": "X", "dependencies": ["nonexistent"]},
            {"id": "a1", "label": "Y", "dependencies": ["a0"]},
        ]
        result = _validate_and_fix_dag(atoms)
        assert result[0]["dependencies"] == []
        assert result[1]["dependencies"] == ["a0"]

    def test_self_cycle_broken(self):
        from reasoning.atom_of_thoughts import _validate_and_fix_dag
        atoms = [
            {"id": "a0", "label": "X", "dependencies": ["a0"]},
        ]
        result = _validate_and_fix_dag(atoms)
        assert "a0" not in result[0]["dependencies"]


# === P2-8: Setup.sh ===

class TestSetupScript:
    """Verify setup.sh doesn't reference removed dependencies."""

    def test_setup_script_exists(self):
        import os
        assert os.path.exists("../scripts/setup.sh")

    def test_setup_no_tauri(self):
        """Rust/Tauri install should be removed (not needed for web app)."""
        with open("../scripts/setup.sh") as f:
            contents = f.read()
        assert "cargo" not in contents, "Tauri/Rust install removed — web app only"
        assert "rustup" not in contents, "Tauri/Rust install removed — web app only"
