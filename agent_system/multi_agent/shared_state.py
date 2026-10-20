from typing import Any

#create the shared state for a new user request
def create_initial_state(user_request: str) -> dict[str, Any]:
    
    
    return {
        
        #original user request
        "user_request": user_request,

        #-----------------------------------------------------------
        #patient information agent

        "patient_information": {
            "request_type": None,
            "requested_task": None,
            "patient_data": [],
            "data_source": None,
            "status": "pending",
            "error": None
        },

        #-----------------------------------------------------------
        #medical evidence retrieval agent

        "medical_evidence": {
            "search_queries": [],
            "retrieved_evidence": [],
            "search_attempts": 0,
            "evidence_relevance": [],
            "status": "pending",
            "error": None
        },

        #-----------------------------------------------------------
        #clinical decision support agent

        "clinical_decision_support": {
            "clinical_considerations": [],
            "treatment_pathways": [],
            "supporting_evidence": [],
            "uncertainties": [],
            "doctor_review_items": [],
            "status": "pending",
            "error": None
        },


        #-----------------------------------------------------------
        #verification agent
      
        "verification": {
            "verification_status": "pending",
            "issues": [],
            "revision_required": False,
            "status": "pending",
            "error": None
        },

        #-----------------------------------------------------------
        #report generation agent

        "report": {
            "content": None,
            "status": "pending",
            "error": None
        },


        #-----------------------------------------------------------
        #system info

        "errors": [],
        "current_agent": None
    }

import time
_LAST_GEMINI_CALL = 0.0
_MIN_GEMINI_INTERVAL = 4.2

def throttle_gemini(min_interval: float = _MIN_GEMINI_INTERVAL):
    global _LAST_GEMINI_CALL
    elapsed = time.monotonic() - _LAST_GEMINI_CALL
    if elapsed < min_interval:
        time.sleep(min_interval - elapsed)
    _LAST_GEMINI_CALL = time.monotonic()
