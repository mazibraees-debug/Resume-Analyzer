"""
Agent Graph
===========
Wires the individual nodes (app.agents.nodes) into the LangGraph
StateGraph shown in the architecture diagram:

    index_cv -> extract_requirements -> match_skills
                                             |
                    ┌────────────────────────┼────────────────────────┐
                    v                        v                        v
            generate_tailored_cv   generate_cover_letter   generate_interview_prep
                    └────────────────────────┼────────────────────────┘
                                             v
                                         cleanup -> END

The three "LLM Agent" nodes fan out from match_skills and run
independently (LangGraph executes nodes with no data dependency on each
other concurrently), then join at `cleanup` before the graph finishes.
"""
from __future__ import annotations

from langgraph.graph import StateGraph, START, END

from app.agents.nodes import (
    AgentState,
    index_cv_node,
    extract_requirements_node,
    match_skills_node,
    generate_tailored_cv_node,
    generate_cover_letter_node,
    generate_interview_prep_node,
    cleanup_node,
)


def build_graph():
    graph = StateGraph(AgentState)

    graph.add_node("index_cv", index_cv_node)
    graph.add_node("extract_requirements", extract_requirements_node)
    graph.add_node("match_skills", match_skills_node)
    graph.add_node("generate_tailored_cv", generate_tailored_cv_node)
    graph.add_node("generate_cover_letter", generate_cover_letter_node)
    graph.add_node("generate_interview_prep", generate_interview_prep_node)
    graph.add_node("cleanup", cleanup_node)

    graph.add_edge(START, "index_cv")
    graph.add_edge("index_cv", "extract_requirements")
    graph.add_edge("extract_requirements", "match_skills")

    # Fan-out: three LLM generation nodes run off the same matching result.
    graph.add_edge("match_skills", "generate_tailored_cv")
    graph.add_edge("match_skills", "generate_cover_letter")
    graph.add_edge("match_skills", "generate_interview_prep")

    # Fan-in: all three must complete before cleanup runs.
    graph.add_edge("generate_tailored_cv", "cleanup")
    graph.add_edge("generate_cover_letter", "cleanup")
    graph.add_edge("generate_interview_prep", "cleanup")

    graph.add_edge("cleanup", END)

    return graph.compile()


_compiled_graph = None


def get_agent_graph():
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = build_graph()
    return _compiled_graph


def run_pipeline(
    cv_text: str, cv_chunks: list[str], job_title: str, job_description: str
) -> AgentState:
    """Convenience wrapper: run the full graph synchronously and return final state."""
    graph = get_agent_graph()
    initial_state: AgentState = {
        "cv_text": cv_text,
        "cv_chunks": cv_chunks,
        "job_title": job_title or "",
        "job_description": job_description,
    }
    final_state = graph.invoke(initial_state)
    return final_state
