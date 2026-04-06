"""Basic import and functionality tests for InterviewPilot.

Verifies that all modules import correctly and core classes
can be instantiated without errors.
"""

import json
import sys
from pathlib import Path

# Ensure backend is on the path
sys.path.insert(0, str(Path(__file__).parent.parent))


def test_config_imports():
    """Verify all config values are accessible."""
    from config import (
        BASE_DIR,
        DATA_DIR,
        DB_DIR,
        UPLOAD_DIR,
        LLM_PROVIDER,
        OLLAMA_BASE_URL,
        LLM_MODEL,
        EMBED_MODEL,
        GEMINI_API_KEY,
        GEMINI_MODEL,
        SQLITE_DB_PATH,
        CHROMA_DB_PATH,
        LLM_TEMPERATURE,
        LLM_MAX_TOKENS,
        LLM_TIMEOUT,
        ATOM_PASS_THRESHOLD,
        DIFFICULTY_INCREASE_THRESHOLD,
        DIFFICULTY_DECREASE_THRESHOLD,
        API_HOST,
        API_PORT,
        CORS_ORIGINS,
    )
    assert LLM_PROVIDER in ("ollama", "gemini")
    assert ATOM_PASS_THRESHOLD == 0.7
    assert DIFFICULTY_INCREASE_THRESHOLD == 0.85
    assert DIFFICULTY_DECREASE_THRESHOLD == 0.50
    print("  [PASS] config imports")


def test_llm_base_class():
    """Verify LLM abstraction layer."""
    from core.llm import BaseLLM, OllamaLLM, GeminiLLM, get_llm
    assert issubclass(OllamaLLM, BaseLLM)
    assert issubclass(GeminiLLM, BaseLLM)

    # Test OllamaLLM instantiation
    ollama = OllamaLLM()
    assert ollama.model == "qwen3:8b"
    assert "localhost" in ollama.base_url

    # Test get_llm factory
    instance = get_llm("ollama")
    assert isinstance(instance, OllamaLLM)

    # Test JSON cleaning
    cleaned = instance._clean_json_response('```json\n{"key": "value"}\n```')
    assert cleaned == {"key": "value"}

    cleaned = instance._clean_json_response('Some text {"key": "value"} more text')
    assert cleaned == {"key": "value"}

    print("  [PASS] LLM base class and factory")


def test_model_imports():
    """Verify all Pydantic schemas and data models."""
    from models.schemas import (
        DocumentUploadRequest,
        DocumentResponse,
        InterviewStartRequest,
        InterviewStartResponse,
        AnswerSubmitRequest,
        AnswerEvaluationResponse,
        NextQuestionResponse,
        SessionEndResponse,
        PrepGenerateRequest,
        PrepQuestionItem,
        PrepResponse,
        SkillHeatmapItem,
        AnalyticsResponse,
        SessionHistoryItem,
        EvaluateAnswerRequest,
        AtomBreakdownResponse,
    )
    from models.profile import UserProfile
    from models.session import InterviewSession

    # Test basic instantiation
    req = DocumentUploadRequest(text="test", doc_type="resume")
    assert req.text == "test"

    profile = UserProfile(user_id="test_user")
    assert profile.total_sessions == 0

    session = InterviewSession(id="s1", user_id="u1", resume_id="r1", jd_id="j1", mode="mock")
    assert session.status == "active"

    print("  [PASS] model imports")


def test_reasoning_imports():
    """Verify reasoning engine modules import correctly."""
    from reasoning.atom_of_thoughts import (
        decompose_to_dag,
        evaluate_atoms,
        contract_to_followup,
        generate_atom_feedback_summary,
    )
    from reasoning.tree_of_thoughts import (
        QuestionNode,
        QuestionTree,
        build_question_tree,
        evaluate_frontier_nodes,
        select_next_question,
        personalize_question,
    )
    from reasoning.hybrid_engine import HybridInterviewEngine
    from reasoning.skill_atoms import SkillAtomTracker, load_taxonomy
    from reasoning.adaptive_controller import AdaptiveController

    # Test QuestionNode
    node = QuestionNode(
        node_id="test_1",
        category="Technical",
        subcategory="Arrays",
        question_template="Test question",
        difficulty=3,
        target_atoms=["dsa_arrays"],
    )
    assert node.node_id == "test_1"
    assert not node.visited

    # Test QuestionTree
    tree = QuestionTree()
    tree.add_node(node)
    assert tree.root == node
    assert len(tree.nodes) == 1
    frontier = tree.get_frontier({})
    assert len(frontier) == 1

    tree.mark_visited("test_1", 0.8)
    assert node.visited
    assert node.score == 0.8
    frontier = tree.get_frontier({})
    assert len(frontier) == 0  # No more unvisited nodes

    # Test SkillAtomTracker
    tracker = SkillAtomTracker()
    taxonomy = load_taxonomy()
    assert "categories" in taxonomy
    assert len(taxonomy["categories"]) == 7
    total_atoms = sum(len(c.get("atoms", [])) for c in taxonomy["categories"])
    assert total_atoms == 56
    assert len(tracker.atoms) == total_atoms

    # Test AdaptiveController
    controller = AdaptiveController()
    assert controller.current_difficulty == 3
    assert controller.strategy == "bfs"

    # Simulate high performance → should increase difficulty
    for _ in range(5):
        controller.update(0.9, {"atom_scores": {}})
    assert controller.current_difficulty >= 4
    assert controller.strategy == "dfs"

    # Test HybridInterviewEngine instantiation
    engine = HybridInterviewEngine()
    assert engine.question_tree is None
    assert engine.follow_up_count == 0

    print("  [PASS] reasoning imports")


def test_parser_imports():
    """Verify parser modules."""
    from parsers.resume_parser import extract_text_from_pdf, parse_resume, get_all_skills_flat
    from parsers.jd_parser import parse_job_description, get_required_skills_flat

    # Test skill extraction helpers
    parsed = {
        "skills": {
            "programming_languages": ["Python", "Java"],
            "frameworks": ["FastAPI"],
        }
    }
    skills = get_all_skills_flat(parsed)
    assert set(skills) == {"Python", "Java", "FastAPI"}

    jd_parsed = {
        "required_skills": [
            {"skill": "Python", "importance": "must_have"},
            {"skill": "Docker", "importance": "nice_to_have"},
        ]
    }
    jd_skills = get_required_skills_flat(jd_parsed)
    assert set(jd_skills) == {"Python", "Docker"}

    print("  [PASS] parser imports")


def test_analysis_imports():
    """Verify analysis modules."""
    from analysis.skill_gap import analyze_skill_gap
    from analysis.match_scoring import calculate_match_score
    from analysis.profile_builder import build_learning_profile

    # Test match scoring
    resume = {
        "skills": {
            "programming_languages": ["python", "java"],
            "frameworks": ["fastapi", "react"],
        }
    }
    jd = {
        "required_skills": [
            {"skill": "python", "importance": "must_have"},
            {"skill": "java", "importance": "must_have"},
            {"skill": "kubernetes", "importance": "nice_to_have"},
        ]
    }
    score = calculate_match_score(resume, jd)
    assert score["overall_score"] > 0
    assert "must_have_matched" in score
    assert "python" in score["must_have_matched"]

    # Test empty profile building
    profile = build_learning_profile([])
    assert profile["total_sessions"] == 0
    assert profile["avg_score"] == 0

    print("  [PASS] analysis imports")


def test_api_imports():
    """Verify API route modules import correctly."""
    from api.router import api_router
    from api.documents import router as doc_router
    from api.interview import router as interview_router
    from api.questions import router as questions_router
    from api.evaluation import router as eval_router
    from api.analytics import router as analytics_router
    from api.realtime import router as realtime_router

    # Verify all routers are included in the main router
    route_paths = [r.path for r in api_router.routes]
    assert any("/documents" in str(r) for r in api_router.routes)
    assert any("/interview" in str(r) for r in api_router.routes)

    print("  [PASS] API imports")


def test_db_imports():
    """Verify database module imports."""
    from db.database import (
        init_db,
        get_db,
        save_document,
        get_document,
        create_session,
        get_session,
        update_session,
        save_question,
        save_answer,
        get_session_history,
        get_skill_atom_scores,
        upsert_skill_atom,
    )
    from db.vector_store import index_document, search_context, clear_document

    print("  [PASS] database imports")


def test_data_files():
    """Verify JSON data files are valid and well-structured."""
    data_dir = Path(__file__).parent.parent / "data"

    # Skill taxonomy
    with open(data_dir / "skill_taxonomy.json") as f:
        taxonomy = json.load(f)
    assert "categories" in taxonomy
    categories = taxonomy["categories"]
    assert len(categories) == 7
    total_atoms = sum(len(c["atoms"]) for c in categories)
    assert total_atoms == 56
    # Verify all atom IDs are unique
    all_ids = [a["id"] for c in categories for a in c["atoms"]]
    assert len(all_ids) == len(set(all_ids)), "Duplicate atom IDs found"

    # Question templates
    with open(data_dir / "question_templates.json") as f:
        templates = json.load(f)
    assert len(templates["templates"]) == 30
    # Verify all target atoms reference valid taxonomy IDs
    for t in templates["templates"]:
        for atom_id in t.get("target_atoms", []):
            assert atom_id in all_ids, f"Template {t['id']} references unknown atom {atom_id}"

    # Rubrics
    with open(data_dir / "rubrics.json") as f:
        rubrics = json.load(f)
    assert len(rubrics["rubrics"]) == 5
    for rubric_name, rubric in rubrics["rubrics"].items():
        total_weight = sum(d["weight"] for d in rubric["dimensions"])
        assert abs(total_weight - 1.0) < 0.01, f"Rubric {rubric_name} weights sum to {total_weight}"

    print("  [PASS] data files")


def test_core_imports():
    """Verify core module imports."""
    from core.llm import BaseLLM, OllamaLLM, GeminiLLM, get_llm
    from core.embeddings import generate_embedding, generate_embeddings
    from core.rag import get_chroma_client, get_collection, add_document, query_documents, chunk_text
    from core.stt import get_whisper_model, transcribe_audio

    # Test text chunking
    text = " ".join(["word"] * 1000)
    chunks = chunk_text(text, chunk_size=100, overlap=10)
    assert len(chunks) > 1
    assert all(len(c.split()) <= 100 for c in chunks)

    print("  [PASS] core imports")


def test_fastapi_app():
    """Verify FastAPI app can be created."""
    from main import app
    assert app.title == "InterviewPilot"
    assert app.version == "0.1.0"

    # Check routes exist
    routes = [r.path for r in app.routes]
    assert "/api/health" in routes
    assert "/api/settings" in routes

    print("  [PASS] FastAPI app")


if __name__ == "__main__":
    print("\n=== InterviewPilot Import & Functionality Tests ===\n")

    tests = [
        test_config_imports,
        test_llm_base_class,
        test_model_imports,
        test_reasoning_imports,
        test_parser_imports,
        test_analysis_imports,
        test_api_imports,
        test_db_imports,
        test_data_files,
        test_core_imports,
        test_fastapi_app,
    ]

    passed = 0
    failed = 0
    errors = []

    for test_func in tests:
        try:
            test_func()
            passed += 1
        except Exception as e:
            failed += 1
            errors.append((test_func.__name__, str(e)))
            print(f"  [FAIL] {test_func.__name__}: {e}")

    print(f"\n{'='*50}")
    print(f"Results: {passed} passed, {failed} failed out of {len(tests)} tests")

    if errors:
        print("\nFailed tests:")
        for name, err in errors:
            print(f"  - {name}: {err}")

    sys.exit(0 if failed == 0 else 1)
