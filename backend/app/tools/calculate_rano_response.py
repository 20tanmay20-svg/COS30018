"""Clinical agent tool: calculate_rano_response."""

from smolagents import tool


@tool
def calculate_rano_response(baseline_cm3: float, follow_up_cm3: float) -> str:
    """
    Calculates percentage volumetric change according to RANO neuro-oncology guidelines.
    Args:
        baseline_cm3: Baseline lesion volume in cm³.
        follow_up_cm3: Follow-up lesion volume in cm³.
    """
    pct_change = ((follow_up_cm3 - baseline_cm3) / baseline_cm3) * 100.0
    status = "Progression" if pct_change >= 25 else "Regression / Response" if pct_change <= -50 else "Stable"
    return f"Volumetric change: {pct_change:+.1f}%. RANO assessment status: {status}."
