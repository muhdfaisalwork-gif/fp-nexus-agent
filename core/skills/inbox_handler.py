import re
import json
from typing import Dict, Any, Optional
from core.llm.client import UniversalLLMClient
from core.brain.brain import BrainManager
from core.rules.rules_engine import RulesEngine
from core.rules.humanizer import Humanizer

class InboxHandler:
    """
    Handles client messages in Fiverr and Upwork inboxes.
    Classifies buyer intent and drafts persuasive, professional, human-natural responses.
    """

    def __init__(self, llm_client: Optional[UniversalLLMClient] = None, brain: Optional[BrainManager] = None):
        self.llm = llm_client or UniversalLLMClient()
        self.brain = brain or BrainManager()

    def reply_to_client(
        self,
        client_message: str,
        conversation_context: str = "",
        gig_or_project_name: str = "",
        freelancer_rate: Optional[float] = None
    ) -> Dict[str, Any]:
        client_msg_clean = (client_message or "").strip()
        if not client_msg_clean:
            default_reply = "I reviewed your inquiry. Could you share your detailed project specifications or files so I can provide an exact timeline and fixed price?"
            return {
                "detected_intent": "general_consultation",
                "recommended_action": "clarify_requirements",
                "reply_text": default_reply,
                "suggested_price": freelancer_rate or 50,
                "humanizer_audit": RulesEngine.audit_text(default_reply)
            }

        system_prompt = RulesEngine.get_system_prompt()
        prompt = f"""You are a top-rated freelance developer handling an incoming client message in your inbox.
Adhere strictly to the 82 Humanizer rules. No corporate robot speech. Be direct, clear, reassuring, and helpful.

CLIENT MESSAGE:
\"\"\"{client_msg_clean}\"\"\"

PROJECT / GIG CONTEXT: {gig_or_project_name or 'Custom Software Development'}
CONVERSATION HISTORY / CONTEXT: {conversation_context or 'First contact'}
STANDARD RATE: ${freelancer_rate or 50}/hr or fixed milestones

TASKS:
1. Detect Intent: One of ['pricing_inquiry', 'scope_clarification', 'urgent_deadline', 'revision_request', 'upset_client', 'general_consultation']
2. Draft a human reply that:
   - Acknowledges their specific point immediately without filler ("Thanks for reaching out!").
   - Explains clearly what is possible, what requirements are needed, or what the price/timeline is.
   - Proposes a concrete next step (e.g. sending a custom offer or reviewing their sample file).

OUTPUT JSON ONLY:
{{
  "detected_intent": "pricing_inquiry",
  "recommended_action": "send_custom_offer",
  "reply_text": "...",
  "suggested_price": 100
}}
"""
        raw_output = self.llm.generate(prompt=prompt, system_prompt=system_prompt, temperature=0.6, max_tokens=800)

        data = {}
        match = re.search(r'\{[\s\S]*\}', str(raw_output or ""))
        if match:
            try:
                data = json.loads(match.group(0))
            except Exception:
                pass

        if not data:
            data = {
                "detected_intent": "general_consultation",
                "recommended_action": "clarify_requirements",
                "reply_text": "I reviewed your message. Could you share the sample input data or API documentation so I can give you an exact timeline and fixed price?",
                "suggested_price": 50
            }

        # Normalize suggested_actions to recommended_action if needed
        if not data.get("recommended_action") and data.get("suggested_actions"):
            actions = data["suggested_actions"]
            if isinstance(actions, list) and actions:
                data["recommended_action"] = str(actions[0])
            else:
                data["recommended_action"] = str(actions)

        # Safe numeric parsing for suggested_price
        if "suggested_price" in data:
            try:
                data["suggested_price"] = float(re.sub(r'[^\d.]', '', str(data["suggested_price"])))
            except Exception:
                data["suggested_price"] = 50.0
        else:
            data["suggested_price"] = 50.0

        clean_reply, audit = Humanizer.humanize_text(data.get("reply_text") or "")
        data["reply_text"] = clean_reply
        data["humanizer_audit"] = audit
        return data
