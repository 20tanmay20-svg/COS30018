"""Tool for assembling source-preserving report sections."""


def create_assemble_report_tool(session):
    from smolagents import tool

    @tool
    def assemble_report(section_order: list[str]) -> dict:
        """Assemble source sections without rewriting their text.

        Args:
            section_order: Every section key once, patient_context first and references last.
        """
        return session.assemble(section_order)

    return assemble_report
