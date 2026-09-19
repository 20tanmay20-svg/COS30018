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