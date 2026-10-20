import re
from typing import Dict, Any, List, Optional
from core.llm.client import UniversalLLMClient
from core.brain.brain import BrainManager
from core.rules.rules_engine import RulesEngine
from core.rules.humanizer import Humanizer
from core.platforms.factory import PlatformFactory

class ProposalWriter:
    """
    Crafts high-converting, human-natural proposals for job postings & buyer briefs.
    Eliminates robotic cover-letter clichés and grounds proposals in verified project receipts.
    """

    def __init__(self, llm_client: Optional[UniversalLLMClient] = None, brain: Optional[BrainManager] = None):
        self.llm = llm_client or UniversalLLMClient()
        self.brain = brain or BrainManager()

    def draft_proposal(
        self,
        job_description: str,
        client_budget: Optional[str] = None,
        platform_name: str = "upwork",
        hook_angle: str = "solution_first",
        specific_stack_or_approach: str = ""
    ) -> Dict[str, Any]:
        job_desc_safe = str(job_description or "")
        platform = PlatformFactory.get_platform(platform_name)

        # Pull relevant project receipts
        receipts = self.brain.get_receipts(query=job_desc_safe[:100], limit=2)
        receipts_text = self.brain.format_receipts_for_prompt(receipts)

        system_prompt = RulesEngine.get_system_prompt()
        prompt = f"""You are an expert senior software engineer and freelancer drafting a high-converting proposal for a client on {platform.platform_name.upper()}.

CRITICAL RULES (ENFORCED BY 82-RULE AUDIT):
1. ZERO SALUTATION FLUFF: NEVER write "Dear Hiring Manager", "I hope this finds you well", "I was excited to see your job post", or "I am thrilled to apply".
2. LINE 1 HOOK: Start immediately with the client's core problem, architectural choice, or exact technical bottleneck. For Upwork, the first 2 sentences are what the client sees in their inbox before clicking.
3. CONCRETE ACTION PLAN: Outline 2-3 clear technical steps on how you will implement their requirements.
4. VERIFIED PROOF: Cite past metrics from the Story Bank below. Never invent fake client statistics.
5. CLOSING: Close with one specific technical question to prompt a reply, followed by a direct sign-off.
6. NO BUZZWORDS: Never use 'delve', 'robust', 'seamless', 'game-changer', 'cutting-edge', 'innovative', 'tapestry', 'landscape'.

CLIENT JOB POSTING:
\"\"\"{job_desc_safe}\"\"\"

CLIENT BUDGET: {client_budget or 'Not specified'}
APPROACH / TECH HIGHLIGHT: {specific_stack_or_approach or 'Fast, maintainable, production-ready solution'}

{receipts_text}

Draft the complete proposal text now. Write in clean, scannable paragraphs (1-3 sentences per block).
"""
        raw_output = self.llm.generate(prompt=prompt, system_prompt=system_prompt, temperature=0.6, max_tokens=1200)

        # Clean and humanize
        humanized_text, audit = Humanizer.humanize_text(raw_output or "")

        # Validate with platform
        is_valid, validation_errors = platform.validate_proposal(humanized_text)

        # Calculate word count & first-two-lines preview
        lines = [l.strip() for l in humanized_text.split('\n') if l.strip()]
        preview_hook = " ".join(lines[:2]) if lines else humanized_text[:150]

        return {
            "platform": platform.platform_name,
            "proposal_text": humanized_text,
            "preview_hook": preview_hook[:200],
            "word_count": len(re.findall(r'\b\w+\b', humanized_text)),
            "flesch_score": audit.get("flesch_score", 70.0),
            "humanizer_audit": audit,
            "is_valid": is_valid,
            "validation_errors": validation_errors
        }
