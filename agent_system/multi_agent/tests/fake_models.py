"""Stand-in for the Verification Agent's language model, so the tests run with no model.

OFFLINE (default): the Verification Agent is real but its judge is a scripted model that
follows simple keyword rules. This checks the code around the model (rules, status
handling), NOT the quality of model answers.

LIVE (`LIVE=1`): nothing is replaced, so the real models and PubMed are used.
"""

import json
import os

from smolagents import Model
from smolagents.models import ChatMessage, ChatMessageToolCall, ChatMessageToolCallFunction

LIVE = bool(os.getenv("LIVE"))
MODE = "live" if LIVE else "offline (stand-in models)"


# ---------------------------------------------------------
# Scripted judge for the Verification Agent

def judge_claim(text):
    """Return (verdict, reason) for a claim using keyword rules."""
    text = text.lower()
    if any(word in text for word in ("does not", "no benefit")):
        return "unsupported", "This contradicts the cited abstract and the other claim."
    if any(word in text for word in ("cures", "curative", "always")):
        return "unsupported", "The abstract reports an association with survival, not a cure."
    if "every" in text:
        return "partial", "The abstract supports a general association, not every population."
    return "supported", "The abstract reports improved survival with temozolomide and radiotherapy."


def _flatten(message):
    content = message.content if hasattr(message, "content") else message.get("content")
    if isinstance(content, list):
        return " ".join(part.get("text", "") for part in content if isinstance(part, dict))
    return content or ""


class FakeJudgeModel(Model):
    """Acts like the verification LLM: read each item's evidence, record a verdict, finish."""

    def __init__(self):
        super().__init__(model_id="fake-judge")

    def generate(self, messages, stop_sequences=None, response_format=None, tools_to_call_from=None, **kwargs):
        steps_done = sum(1 for m in messages if str(getattr(m, "role", "")).lower().endswith("assistant"))
        items = self._items(messages)
        if steps_done == 0 and items:
            calls = [("get_cited_evidence", {"item_type": i["item_type"], "number": i["number"]}) for i in items]
        elif steps_done == 1 and items:
            calls = [("record_verdict", {"item_type": i["item_type"], "number": i["number"],
                                         **dict(zip(("verdict", "reason"), judge_claim(i["text"])))}) for i in items]
        else:
            calls = [("final_answer", {"answer": "All items checked."})]
        return ChatMessage(role="assistant", content="", tool_calls=[
            ChatMessageToolCall(id=f"call_{steps_done}_{n}", type="function",
                                function=ChatMessageToolCallFunction(name=name, arguments=args))
            for n, (name, args) in enumerate(calls)])

    @staticmethod
    def _items(messages):
        marker = "Verify each of these items:"
        for message in messages:
            text = _flatten(message)
            if marker in text:
                return json.JSONDecoder().raw_decode(text.split(marker, 1)[1].strip())[0]
        return []


def judge_model():
    """The model to pass to run_verification_agent: None means the real configured model."""
    return None if LIVE else FakeJudgeModel()
