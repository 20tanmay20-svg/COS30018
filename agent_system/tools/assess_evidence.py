"""Session-bound assess_evidence tool."""

from .tool_schemas import EvidenceRelevance, PubMedId, ToolResult


def create_assess_evidence_tool(session):
    """Bind the tool to this run's session."""
    from smolagents import tool

    @tool
    def assess_evidence(
        pmid: PubMedId,
        relevance: EvidenceRelevance,
        rationale: str,
        supporting_quote: str,
        limitations: str,
    ) -> ToolResult:
        """Record a relevance assessment of a retrieved PubMed abstract.

        Result: Success returns success and assessed_count. Failure returns success=false and error.

        Args:
            pmid: Identifier returned by the search tool in this run.
            relevance: Relevance category (choices: ["high", "medium", "low", "not_relevant"]).
            rationale: Why this study does or does not address the evidence question.
            supporting_quote: Exact abstract excerpt, or empty for irrelevant material.
            limitations: Study and patient-context limitations requiring verification.
        """
        return session.assess(pmid, relevance, rationale, supporting_quote, limitations)

    return assess_evidence
