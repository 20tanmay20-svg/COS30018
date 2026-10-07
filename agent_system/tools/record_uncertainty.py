"""Session-bound record_uncertainty tool."""


def create_record_uncertainty_tool(session):
    """Bind the tool to this run's session."""
    from smolagents import tool

    @tool
    def record_uncertainty(description: str) -> dict:
        """Record an uncertainty affecting the clinical picture.

        Args:
            description: The uncertainty, unknown, or ambiguity being flagged.
        """
        return session.add_uncertainty(description)

    return record_uncertainty
