"""Tool for assembling source-preserving report sections."""

from .tool_schemas import ReportSection, ToolResult


def create_assemble_report_tool(session):
    from smolagents import tool

    @tool
    def assemble_report(section_order: list[ReportSection]) -> ToolResult:
        """Assemble all source sections into the report without changing their text.

        Result: Success returns success and sections_included. Failure returns success=false and error.

        Args:
            section_order: Every report section exactly once, with patient_context first and references last.
        """
        return session.assemble(section_order)
    return assemble_report

