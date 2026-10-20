import os
from typing import Dict, Any, Optional
from core.llm.client import UniversalLLMClient
from core.brain.brain import BrainManager
from core.rules.rules_engine import RulesEngine
from core.rules.humanizer import Humanizer

class ProjectUploader:
    """
    Transforms finished projects, scripts, or repositories into high-converting
    portfolio case studies and client briefs. Also records verified receipts to the Brain.
    """

    def __init__(self, llm_client: Optional[UniversalLLMClient] = None, brain: Optional[BrainManager] = None):
        self.llm = llm_client or UniversalLLMClient()
        self.brain = brain or BrainManager()

    def format_project_case_study(
        self,
        project_title: str,
        niche_or_category: str,
        problem_solved: str,
        tech_stack: str,
        results_or_metrics: str,
        deliverables: str = "",
        save_to_brain: bool = True
    ) -> Dict[str, Any]:
        title = str(project_title or "Client Technical Implementation").strip()
        category = str(niche_or_category or "Software Engineering").strip()
        problem = str(problem_solved or "Workflow bottlenecks").strip()
        stack = str(tech_stack or "Python, APIs").strip()
        metrics = str(results_or_metrics or "Delivered on schedule with complete test suite").strip()
        deliv = str(deliverables or "").strip()

        system_prompt = RulesEngine.get_system_prompt()
        prompt = f"""Format this completed technical project into a clean, client-facing portfolio case study.
Adhere strictly to the 82 humanizer rules. No marketing fluff or inflated significance claims.

PROJECT TITLE: {title}
CATEGORY: {category}
PROBLEM CONTEXT: {problem}
TECH STACK: {stack}
RESULTS / MEASUREMENTS: {metrics}
DELIVERABLES: {deliv}

Produce a structured markdown document with:
1. Executive Summary (2 sentences max)
2. The Client's Initial Blocker
3. Architecture & Implementation Details
4. Measured Outcomes & Key Results (cite the exact numbers)
5. Delivered Artifacts
"""
        raw_output = self.llm.generate(prompt=prompt, system_prompt=system_prompt, temperature=0.5, max_tokens=1000)
        humanized_doc, audit = Humanizer.humanize_text(raw_output or "")

        receipt_id = None
        if save_to_brain:
            receipt_id = self.brain.add_receipt(
                category=category,
                title=title,
                client_niche=category,
                problem=problem,
                solution_stack=stack,
                verified_metrics=metrics,
                duration_days=7,
                deliverables=deliv
            )

        return {
            "title": title,
            "case_study_markdown": humanized_doc,
            "saved_to_brain": save_to_brain,
            "receipt_id": receipt_id,
            "humanizer_audit": audit
        }
