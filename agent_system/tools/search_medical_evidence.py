"""Session-bound search_medical_evidence tool."""


def create_search_medical_evidence_tool(session):
    """Bind the tool to this run's session."""
    from smolagents import tool

    @tool
    def search_medical_evidence(query: str) -> dict:
        """Search PubMed for GBM literature and retrieve source abstracts.

        Args:
            query: Short PubMed medical concept query without patient identifiers.
        """
        return session.search(query)

    return search_medical_evidence
