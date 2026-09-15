"""
Agent Nodes
===========
Each function below is one node in the LangGraph workflow shown in the
architecture diagram:

    Matching Agent  -> Skill Match / Missing Skills / Experience
    LLM Agent       -> Tailored CV / Cover Letter / Interview Prep

Every node takes the shared `AgentState` dict, does one focused job, and
returns a partial state update (LangGraph merges it in).
"""
from __future__ import annotations

from typing import TypedDict

from app.agents import prompts
from app.config import get_settings
from app.embeddings.embedder import get_embedder, cosine_similarity
from app.llm.client import get_llm_client
from app.parsers.document_parser import chunk_job_description
from app.vectorstore.store import get_vector_store


class AgentState(TypedDict, total=False):
    # --- inputs ---
    cv_text: str
    cv_chunks: list[str]
    job_title: str
    job_description: str

    # --- working state ---
    collection_name: str
    requirements: list[str]
    skill_matches: list[dict]
    skill_gaps: list[str]
    match_score: float

    # --- outputs ---
    tailored_cv_sections: dict
    cover_letter: str
    interview_questions: list[dict]

    # --- bookkeeping ---
    error: str | None


def index_cv_node(state: AgentState) -> dict:
    """Embed the CV chunks and load them into a fresh vector-store collection."""
    store = get_vector_store()
    collection_name = store.new_collection()
    store.add_cv_chunks(collection_name, state["cv_chunks"])
    return {"collection_name": collection_name}


def extract_requirements_node(state: AgentState) -> dict:
    """LLM Agent step: pull the concrete requirements out of the JD."""
    llm = get_llm_client()
    requirements = llm.complete_json(
        prompts.EXTRACT_REQUIREMENTS_SYSTEM,
        prompts.EXTRACT_REQUIREMENTS_USER.format(
            job_description=state["job_description"]
        ),
    )
    if not isinstance(requirements, list):
        requirements = chunk_job_description(state["job_description"])
    return {"requirements": [str(r) for r in requirements]}


def match_skills_node(state: AgentState) -> dict:
    """
    Matching Agent step: for each JD requirement, retrieve the most
    similar chunk(s) from the candidate's CV via the vector store and
    classify the match strength.

    This is the "Skill Match / Missing Skills / Experience" fan-out from
    the architecture diagram, computed here as a single pass that
    produces both matches and gaps together.
    """
    settings = get_settings()
    store = get_vector_store()
    collection_name = state["collection_name"]

    matches: list[dict] = []
    gaps: list[str] = []

    for requirement in state["requirements"]:
        retrieved = store.query_similar(
            collection_name, requirement, top_k=settings.top_k_matches
        )
        if not retrieved:
            gaps.append(requirement)
            continue

        best = max(retrieved, key=lambda r: r.similarity)
        if best.similarity >= settings.match_threshold:
            strength = "strong" if best.similarity >= 0.35 else "partial"
            matches.append(
                {
                    "requirement": requirement,
                    "matched_cv_evidence": best.text,
                    "similarity": round(best.similarity, 3),
                    "strength": strength,
                }
            )
        else:
            gaps.append(requirement)

    total = len(state["requirements"]) or 1
    match_score = round(len(matches) / total * 100, 1)

    return {
        "skill_matches": matches,
        "skill_gaps": gaps,
        "match_score": match_score,
    }


def _matches_summary(state: AgentState) -> str:
    if not state.get("skill_matches"):
        return "(no strong matches found)"
    lines = []
    for m in state["skill_matches"]:
        lines.append(
            f"- Requirement: {m['requirement']}\n"
            f"  Evidence in CV: {m['matched_cv_evidence']}\n"
            f"  Match strength: {m['strength']} ({m['similarity']})"
        )
    return "\n".join(lines)


def _gaps_summary(state: AgentState) -> str:
    if not state.get("skill_gaps"):
        return "(no significant gaps found)"
    return "\n".join(f"- {g}" for g in state["skill_gaps"])


def generate_tailored_cv_node(state: AgentState) -> dict:
    llm = get_llm_client()
    result = llm.complete_json(
        prompts.TAILORED_CV_SYSTEM,
        prompts.TAILORED_CV_USER.format(
            cv_text=state["cv_text"],
            requirements_list="\n".join(f"- {r}" for r in state["requirements"]),
            matches_summary=_matches_summary(state),
            gaps_list=_gaps_summary(state),
        ),
        max_tokens=1500,
    )
    return {"tailored_cv_sections": result}


def generate_cover_letter_node(state: AgentState) -> dict:
    llm = get_llm_client()
    result = llm.complete_json(
        prompts.COVER_LETTER_SYSTEM,
        prompts.COVER_LETTER_USER.format(
            cv_text=state["cv_text"],
            job_title=state.get("job_title") or "the role",
            job_description=state["job_description"],
            matches_summary=_matches_summary(state),
            gaps_list=_gaps_summary(state),
        ),
        max_tokens=900,
    )
    return {"cover_letter": result.get("cover_letter", "")}


def generate_interview_prep_node(state: AgentState) -> dict:
    llm = get_llm_client()
    result = llm.complete_json(
        prompts.INTERVIEW_PREP_SYSTEM,
        prompts.INTERVIEW_PREP_USER.format(
            cv_text=state["cv_text"],
            job_title=state.get("job_title") or "the role",
            job_description=state["job_description"],
            matches_summary=_matches_summary(state),
            gaps_list=_gaps_summary(state),
        ),
        max_tokens=1500,
    )
    if not isinstance(result, list):
        result = []
    return {"interview_questions": result}


def cleanup_node(state: AgentState) -> dict:
    """Drop the ephemeral vector-store collection now that matching is done."""
    store = get_vector_store()
    if state.get("collection_name"):
        store.delete_collection(state["collection_name"])
    return {}
