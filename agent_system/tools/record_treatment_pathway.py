"""Session-bound record_treatment_pathway tool."""


def create_record_treatment_pathway_tool(session):
    """Bind the tool to this run's session."""
    from smolagents import tool

    @tool
    def record_treatment_pathway(
        option: str, when_considered: str, supporting_evidence: list[str],
        unknown_patient_factors: str, risks_and_limitations: str
    ) -> dict:
        """Record one treatment or management pathway for clinician review.

        Args:
            option: The treatment or management option.
            when_considered: The circumstances under which it may be considered.
            supporting_evidence: PMIDs from available_evidence that support it; empty if none.
            unknown_patient_factors: Patient-specific factors that are unknown but relevant.
            risks_and_limitations: Risks or limitations of this option.
        """
        return session.add_treatment_pathway(option, when_considered, supporting_evidence, unknown_patient_factors, risks_and_limitations)

    return record_treatment_pathway
