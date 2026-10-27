#In-memory session that lets a clinician revise a report across several requests
import uuid
from dataclasses import dataclass, field


@dataclass
class Session:
    session_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    original_request: str | None = None
    sections: dict = field(default_factory=dict)  # last successful output per stage
    revision_requests: list = field(default_factory=list)  # accepted clinician revisions, in order
    report_versions: list = field(default_factory=list)  # every successful report

    @property
    def has_report(self) -> bool:
        return bool(self.report_versions)

    def reset(self, original_request: str) -> None:
        #Start over for a new patient/report
        self.original_request = original_request
        self.sections.clear()
        self.revision_requests.clear()
        self.report_versions.clear()