"""Session-bound record_clinical_consideration tool."""


def create_record_clinical_consideration_tool(session):
    """Bind the tool to this run's session."""
    from smolagents import tool

    @tool
    def record_clinical_consideration(
        consideration: str, reasoning: str, context_info: str,
        supporting_evidence: list[str], limitations: str, requires_review: bool = True
    ) -> dict:
        """Record one clinical consideration for clinician review.

        Args:
            consideration: The clinical consideration being raised.
            reasoning: Why this consideration follows from the supplied information.
            context_info: The relevant patient/context information behind it.
            supporting_evidence: PMIDs from available_evidence that support it; empty if none.
            limitations: Limitations, caveats, or unknowns affecting this consideration.
            requires_review: Whether this consideration specifically needs clinician review.
        """
        return session.add_consideration(consideration, reasoning, context_info, supporting_evidence, limitations, requires_review)

    return record_clinical_consideration
