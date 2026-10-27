"""Session-bound record_clinical_consideration tool."""

from .tool_schemas import PubMedId, ToolResult


def create_record_clinical_consideration_tool(session):
    """Bind the tool to this run's session."""
    from smolagents import tool

    @tool
    def record_clinical_consideration(
        consideration: str, reasoning: str, context_info: str,
        supporting_evidence: list[PubMedId], limitations: str,
        requires_review: bool | None = None,
    ) -> ToolResult:
        """Record one clinical consideration for clinician review.

        Result: Success returns success and recorded_count. Failure returns success=false and error.

        Args:
            consideration: The clinical consideration being raised.
            reasoning: Why this consideration follows from the supplied information.
            context_info: Relevant patient/context information; use "Not specified." when unknown.
            supporting_evidence: PMIDs from available_evidence that support it; empty if none.
            limitations: Limitations, caveats, or unknowns affecting this consideration.
            requires_review: Whether this consideration needs review; null uses the default review policy.
        """
        return session.add_consideration(
            consideration,
            reasoning,
            context_info,
            supporting_evidence,
            limitations,
            True if requires_review is None else requires_review,
        )

    return record_clinical_consideration
