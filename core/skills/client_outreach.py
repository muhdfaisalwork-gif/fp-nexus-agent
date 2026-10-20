from typing import Dict, Any, Optional
from core.llm.client import UniversalLLMClient
from core.brain.brain import BrainManager
from core.rules.rules_engine import RulesEngine
from core.rules.humanizer import Humanizer

class ClientOutreach:
    """
    Finds and drafts high-conversion, non-spammy cold outreach to prospective clients.
    Focuses on identifying specific bugs, architecture bottlenecks, or quick wins.
    """

    def __init__(self, llm_client: Optional[UniversalLLMClient] = None, brain: Optional[BrainManager] = None):
        self.llm = llm_client or UniversalLLMClient()
        self.brain = brain or BrainManager()

    def draft_outreach(
        self,
        prospect_name_or_company: str,
        prospect_problem_or_tech: str,
        outreach_channel: str = "direct_message",
        specific_observation: str = ""
    ) -> Dict[str, Any]:
        prospect = str(prospect_name_or_company or "Prospective Client").strip()
        problem_tech = str(prospect_problem_or_tech or "Backend Architecture").strip()
        channel = str(outreach_channel or "direct_message").strip()
        obs = str(specific_observation or "Identified potential performance and latency improvements in your workflow.").strip()
        receipts = self.brain.get_receipts(query=problem_tech[:80], limit=2)
        receipts_text = self.brain.format_receipts_for_prompt(receipts)

        system_prompt = RulesEngine.get_system_prompt()
        prompt = f"""Draft a short, direct, value-first outreach message to a potential freelance client.
Follow the 82 Humanizer Rules strictly.

PROSPECT: {prospect}
PROBLEM / TECH FOCUS: {problem_tech}
OBSERVATION / AUDIT NOTE: {obs}
CHANNEL: {channel}

{receipts_text}

OUTREACH PRINCIPLES:
1. Do NOT start with "Hope you are doing well" or "My name is X and I am an expert".
2. Open with the specific observation regarding their site, repo, or API.
3. Share a concrete, free suggestion or benchmark.
4. Mention a similar problem you solved without bragging.
5. Close with a frictionless question (e.g. "Want me to send over the 2-minute diagnostic script?").
6. Keep under 140 words.
"""
        raw_output = self.llm.generate(prompt=prompt, system_prompt=system_prompt, temperature=0.6, max_tokens=600)
        humanized_text, audit = Humanizer.humanize_text(raw_output or "")

        return {
            "prospect": prospect,
            "channel": channel,
            "outreach_text": humanized_text,
            "humanizer_audit": audit
        }
