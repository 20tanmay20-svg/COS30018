"""Session-bound assess_evidence tool."""


def create_assess_evidence_tool(session):
    """Bind the tool to this run's session."""
    from smolagents import tool

    @tool
    def assess_evidence(pmid: str, relevance: str, rationale: str,
                        supporting_quote: str, limitations: str) -> dict:
        """Record a relevance assessment of a retrieved PubMed abstract.

        Args:
            pmid: Identifier returned by the search tool in this run.
            relevance: high, medium, low, or not_relevant.
            rationale: Why this study does or does not address the evidence question.
            supporting_quote: Exact abstract excerpt, or empty for irrelevant material.
            limitations: Study and patient-context limitations requiring verification.
        """
        return session.assess(pmid, relevance, rationale, supporting_quote, limitations)

    return assess_evidence
