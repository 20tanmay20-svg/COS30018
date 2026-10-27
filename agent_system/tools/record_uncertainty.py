"""Session-bound record_uncertainty tool."""

from .tool_schemas import ToolResult


def create_record_uncertainty_tool(session):
    """Bind the tool to this run's session."""
    from smolagents import tool

    @tool
    def record_uncertainty(description: str) -> ToolResult:
        """Record an uncertainty affecting the clinical picture.

        Result: Success returns success and recorded_count. Failure returns success=false and error.

        Args:
            description: The uncertainty, unknown, or ambiguity being flagged.
        """
        return session.add_uncertainty(description)

    return record_uncertainty
