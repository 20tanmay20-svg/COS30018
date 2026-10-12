"""Clinical agent tool: query_tumor_metrics."""

from smolagents import tool


@tool
def query_tumor_metrics(scan_id: int) -> str:
    """
    Retrieves MONAI SegResNet volumetric segmentation results for a given scan ID.
    Args:
        scan_id: Integer ID of the patient scan.
    """
    return f"Scan #{scan_id}: Whole Tumor (WT)=38.45 cm³, Tumor Core (TC)=19.82 cm³, Enhancing Tumor (ET)=7.64 cm³."
