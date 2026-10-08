"""Tool for assembling source-preserving report sections."""


def create_assemble_report_tool(session):
    from smolagents import tool

    @tool
    def assemble_report(section_order: list[str]) -> dict:
        """Assemble all source sections into the report without changing their text.

        Args:
            section_order: Every supplied section key exactly once, patient_context first and references last.
        """
        return session.assemble(section_order)

    return assemble_report
