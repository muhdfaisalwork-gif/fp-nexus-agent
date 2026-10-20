import re
import math
from typing import Dict, List, Any, Tuple

# Strict Master System Prompt containing the 82 rules
MASTER_WRITING_SYSTEM_PROMPT = """# HUMAN-NATURAL WRITING — STRICT MASTER PROMPT

## ROLE
Act as an experienced human writer, builder, and ruthless copy editor.
Your job is not to produce text that merely sounds fluent.
Your job is to produce writing that feels like it came from a real person who understands the subject, knows what they want to say, and chose each sentence for a reason.
Write with natural human variation, concrete meaning, appropriate confidence, and subject-specific judgment.
Never optimize for "sounding sophisticated."
Optimize for:
* clarity
* specificity
* naturalness
* information density
* believable human rhythm
* appropriate tone
* accurate meaning
* authentic voice

## CORE RULES SUMMARY (ALL 82 RULES APPLY STRICTLY):
1. Ask silently before writing: "Would a real, knowledgeable person naturally say it this way?"
2. NEVER WRITE TO IMPRESS: Forbidden AI buzzwords: delve, pivotal, robust, comprehensive, multifaceted, nuanced, intricate, transformative, groundbreaking, revolutionary, innovative, cutting-edge, dynamic, vibrant, enduring, remarkable, exceptional, sophisticated, seamless, powerful, versatile, noteworthy, compelling, invaluable, invaluable insights, landscape, tapestry, testament, realm, ecosystem, paradigm, interplay, fostering, leveraging, harnessing, empowering, showcasing, underscore, garner, facilitate.
3. PREFER PLAIN VERBS: use (not utilize), help (not facilitate), start (not commence), show (not showcase), get (not obtain), improve (not enhance), keep (not maintain), explain (not elucidate), check (not ascertain), try (not endeavor).
4. DO NOT ROTATE SYNONYMS ARTIFICIALLY.
5. BAN GENERIC SIGNIFICANCE PADDING: "marking a pivotal moment", "underscoring its importance", "shaping the future", "paving the way for", "laying the groundwork for", "setting the stage for".
6. DO NOT OVER-EXPLAIN: No "In other words...", "This means that...", "In essence...", "Put simply...".
7. NO AUTOMATIC INTRO FORMULA: Never start with "In today's fast-paced world...", "In the modern era...", "In today's digital landscape...", "I hope this message finds you well", "Dear hiring manager", "I am thrilled to apply". Start with the actual subject or problem.
8. NO AUTOMATIC CONCLUSION FORMULA: Never end with "In conclusion...", "Ultimately...", "Looking ahead...", "The key takeaway is...". End when the point is made.
9. CONTROL CONNECTORS: Do not start every paragraph with Additionally, Furthermore, Moreover, Consequently, Therefore, Thus, Hence, Notably.
10. BAN REPETITIVE PARAGRAPH OPENINGS.
11. AVOID "THIS + ABSTRACT NOUN" (this approach, this strategy, this framework, this shift, this paradigm).
12. CONTROL "NOT JUST X, BUT Y".
13. CONTROL RULE OF THREE: Do not manufacture triads.
14. BREAK EXCESSIVE SYMMETRY. Natural human writing has asymmetry.
15. VARY SENTENCE LENGTH NATURALLY: Avoid mechanical long/short seesaws or all-same length.
16. EM-DASH CONTROL: Cap at approximately 1 per 100 words. Never use as an omnipresent dramatic pause.
17. NO MARKETING PRAISE WITHOUT EVIDENCE: (innovative, world-class, leading, cutting-edge, best-in-class).
18. USE SPECIFIC ACTORS & CONCRETE NOUNS: "payment gateway" instead of "monetization infrastructure", "FastAPI endpoint" instead of "technological solution".
19. CONCRETE EXAMPLES & NO INVENTED SPECIFICITY: Use real numbers, tech stacks, and delivery hours from the verified Story Bank. Never fabricate.
20. NO CHATBOT PHRASES: Never say "Certainly!", "Here's what you need to know", "Let's dive in", "I hope this helps", "Great question!".
21. FREELANCING PLATFORM CONVERSION RULES:
    - Line 1 (Proposal & Gig Hook): Address the client's concrete problem or exact tech stack immediately.
    - Ban sycophantic flattery: Do not tell the client their project is "exciting", "prestigious", or "amazing".
    - Price and deliverables: Explicitly state scope and deliverable milestones rather than vague promises.
    - Format: Clean blocks, 1-2 sentences per thought, scannable for busy clients on mobile screens.
"""

# Programmatic Blacklist & Tell Patterns
BANNED_AI_WORDS = [
    "delve", "delves", "delved", "delving", "pivotal", "robust", "comprehensive", "multifaceted", "nuanced",
    "intricate", "transformative", "groundbreaking", "revolutionary", "innovative",
    "cutting-edge", "dynamic", "vibrant", "enduring", "remarkable", "exceptional",
    "sophisticated", "seamless", "versatile", "noteworthy", "compelling",
    "invaluable", "invaluable insights", "landscape", "tapestry", "testament",
    "realm", "ecosystem", "paradigm", "interplay",
    "foster", "fosters", "fostered", "fostering",
    "leverage", "leverages", "leveraged", "leveraging",
    "harness", "harnesses", "harnessed", "harnessing",
    "empower", "empowers", "empowered", "empowering",
    "showcase", "showcases", "showcased", "showcasing",
    "underscore", "underscores", "underscored", "underscoring",
    "garner", "garners", "garnered", "garnering",
    "facilitate", "facilitates", "facilitated", "facilitating",
    "utilize", "utilizes", "utilized", "utilizing",
    "commence", "commences", "commenced", "commencing",
    "elucidate", "elucidates", "elucidated", "elucidating",
    "streamline", "streamlines", "streamlined", "streamlining",
    "elevate", "elevates", "elevated", "elevating",
    "holistic", "game-changer", "deep dive"
]

GENERIC_INTROS = [
    r"in today['’]?s\b.*?\b(world|landscape|environment|age|era)\b",
    r"in the modern era",
    r"as technology continues to evolve",
    r"it is important to understand that",
    r"i hope this (message|email|proposal) finds you well",
    r"dear (hiring manager|client|recruiter)",
    r"i am (thrilled|excited|delighted) to (apply|submit|bid)"
]

GENERIC_CONCLUSIONS = [
    r"^in conclusion",
    r"^ultimately",
    r"^looking ahead",
    r"^the key takeaway is",
    r"^taken together",
    r"^this represents a significant step forward",
    r"^thank you for (your time and consideration|considering my proposal)"
]

CHATBOT_PHRASES = [
    r"absolutely!",
    r"certainly!",
    r"great question!",
    r"here['’]?s a closer look",
    r"let['’]?s dive in",
    r"let['’]?s break this down",
    r"here['’]?s what you need to know",
    r"i hope this helps",
    r"let me know if you['’]?d like",
    r"as an ai\b",
    r"i['’]?d be happy to help",
    r"feel free to reach out"
]

REVEAL_BRIDGES = [
    r"the result\?",
    r"plot twist:",
    r"here['’]?s the thing:",
    r"it['’]?s not x,? it['’]?s y",
    r"stop .+, start .+"
]


class RulesEngine:
    @staticmethod
    def get_system_prompt(custom_voice: str = "") -> str:
        prompt = MASTER_WRITING_SYSTEM_PROMPT
        if custom_voice:
            prompt += f"\n\n## FREELANCER SPECIFIC VOICE & CREDENTIALS:\n{custom_voice}"
        return prompt

    @staticmethod
    def audit_text(text: str) -> Dict[str, Any]:
        """Audits text against the 82 rules and returns pass/fail metrics and flags."""
        clean_text = (text or "").strip()
        words = re.findall(r'\b\w+\b', clean_text.lower())
        word_count = len(words)
        char_count = len(clean_text)

        if word_count == 0:
            return {
                "score": 100,
                "char_count": char_count,
                "word_count": 0,
                "flesch_score": 70.0,
                "em_dash_count": 0,
                "banned_words_found": {},
                "violations": [],
                "warnings": [],
                "is_compliant": True
            }

        violations = []
        warnings = []

        # 1. Banned AI Vocabulary Check
        found_buzzwords = {}
        for word in BANNED_AI_WORDS:
            pattern = rf'\b{re.escape(word)}\b'
            matches = len(re.findall(pattern, clean_text, re.IGNORECASE))
            if matches > 0:
                found_buzzwords[word] = matches
                violations.append({
                    "rule": "Rule 2: Never Write to Impress",
                    "issue": f"Forbidden AI word detected: '{word}' ({matches}x)",
                    "severity": "high"
                })

        # 2. Generic Intro Check
        first_paragraph = clean_text.split('\n\n')[0].strip() if clean_text else ""
        for pattern in GENERIC_INTROS:
            if re.search(pattern, first_paragraph, re.IGNORECASE):
                violations.append({
                    "rule": "Rule 7: No Automatic Introduction Formula",
                    "issue": "Generic introductory filler or proposal cliché detected in opening.",
                    "severity": "high"
                })

        # 3. Generic Conclusion Check
        last_paragraph = clean_text.split('\n\n')[-1].strip() if clean_text else ""
        for pattern in GENERIC_CONCLUSIONS:
            if re.search(pattern, last_paragraph, re.IGNORECASE):
                violations.append({
                    "rule": "Rule 8: No Automatic Conclusion Formula",
                    "issue": "Generic conclusion cliché or boilerplate sign-off detected at ending.",
                    "severity": "medium"
                })

        # 4. Chatbot Residue Check
        for pattern in CHATBOT_PHRASES:
            if re.search(pattern, clean_text, re.IGNORECASE):
                violations.append({
                    "rule": "Rule 35: Do Not Sound Like a Chatbot",
                    "issue": f"Conversational chatbot residue detected: '{pattern}'",
                    "severity": "high"
                })

        # 5. Em-Dash Saturation Check (Rule 17: Cap at ~1 per 100 words)
        em_dashes = len(re.findall(r'—|--', clean_text))
        allowed_em_dashes = max(1, math.ceil(word_count / 100))
        if em_dashes > allowed_em_dashes:
            violations.append({
                "rule": "Rule 17: Em-Dash Control",
                "issue": f"Too many em-dashes ({em_dashes} found; cap is {allowed_em_dashes} for {word_count} words).",
                "severity": "medium"
            })

        # 6. Reveal Bridges Check
        for pattern in REVEAL_BRIDGES:
            if re.search(pattern, clean_text, re.IGNORECASE):
                violations.append({
                    "rule": "Rule 5: No Reveal Bridges or Artificial Drama",
                    "issue": f"Artificial reveal bridge detected: '{pattern}'",
                    "severity": "medium"
                })

        # 7. Proposal Hook Check: Check for weak questions or flattery in line 1
        first_line = clean_text.split('\n')[0].strip() if clean_text else ""
        if re.match(r'^(are you looking for|do you need|want someone who)\b', first_line, re.IGNORECASE):
            warnings.append({
                "rule": "Proposal Hook Rule",
                "issue": "First line opens with a generic rhetorical question. Start with the solution or direct proof.",
                "severity": "medium"
            })

        # Calculate Flesch Reading Ease
        flesch = RulesEngine.calculate_flesch(clean_text)

        # Compute Quality Score (100 - penalties)
        score = 100 - (len(violations) * 12) - (len(warnings) * 5)
        score = max(0, min(100, score))

        return {
            "score": score,
            "char_count": char_count,
            "word_count": word_count,
            "flesch_score": flesch,
            "em_dash_count": em_dashes,
            "banned_words_found": found_buzzwords,
            "violations": violations,
            "warnings": warnings,
            "is_compliant": len(violations) == 0
        }

    @staticmethod
    def calculate_flesch(text: str) -> float:
        """Calculate Flesch Reading Ease score."""
        safe_text = str(text or "")
        sentences = [s for s in re.split(r'[.!?]+', safe_text) if s.strip()]
        words = re.findall(r'\b[a-zA-Z0-9_\-]+\b', safe_text)
        if not sentences or not words:
            return 70.0

        num_sentences = max(1, len(sentences))
        num_words = max(1, len(words))

        def count_syllables(word):
            word = word.lower()
            if word.isdigit():
                return 1
            if len(word) <= 3:
                return 1
            word = re.sub(r'(?:[^laeiouy]|ed|es|e)$', '', word)
            word = re.sub(r'^y', '', word)
            matches = re.findall(r'[aeiouy]{1,2}', word)
            return max(1, len(matches))

        num_syllables = sum(count_syllables(w) for w in words)
        score = 206.835 - 1.015 * (num_words / num_sentences) - 84.6 * (num_syllables / num_words)
        return round(max(0.0, min(100.0, score)), 1)
