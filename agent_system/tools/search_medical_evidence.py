"""Session-bound search_medical_evidence tool."""

from .tool_schemas import ToolResult


def create_search_medical_evidence_tool(session):
    """Bind the tool to this run's session."""
    from smolagents import tool

    @tool
    def search_medical_evidence(query: str) -> ToolResult:
        """Search PubMed for GBM literature and retrieve source abstracts.

        Result: Success returns success, records, warnings, and remaining_searches.
        Failure returns success=false and error.

        Args:
            query: GBM medical concepts only, at most 500 characters, without patient identifiers.
        """
        return session.search(query)

    return search_medical_evidence
