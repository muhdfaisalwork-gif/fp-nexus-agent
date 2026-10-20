import pytest
from core.rules.rules_engine import RulesEngine, BANNED_AI_WORDS

def test_clean_text_passes():
    text = "We built an asynchronous order processor using FastAPI and Redis. Median latency dropped to 380ms."
    audit = RulesEngine.audit_text(text)
    assert audit["is_compliant"] is True
    assert audit["score"] >= 90
    assert len(audit["violations"]) == 0

def test_banned_words_detected():
    text = "Our transformative and cutting-edge ecosystem delves into multifaceted paradigms."
    audit = RulesEngine.audit_text(text)
    assert audit["is_compliant"] is False
    found = audit["banned_words_found"]
    assert "transformative" in found
    assert "cutting-edge" in found
    assert "ecosystem" in found
    assert "delves" in found or "delve" in found
    assert len(audit["violations"]) >= 4

def test_generic_intro_proposal_detected():
    text = "I hope this proposal finds you well. I am thrilled to apply for your esteemed project."
    audit = RulesEngine.audit_text(text)
    assert any("Rule 7" in v["rule"] for v in audit["violations"])

def test_generic_intro_modern_world_detected():
    text = "In today's rapidly evolving digital world, businesses need automated solutions."
    audit = RulesEngine.audit_text(text)
    assert any("Rule 7" in v["rule"] for v in audit["violations"])

def test_generic_conclusion_detected():
    text = "We can complete the work in 3 days.\n\nIn conclusion, this represents a significant step forward."
    audit = RulesEngine.audit_text(text)
    assert any("Rule 8" in v["rule"] for v in audit["violations"])

def test_em_dash_saturation():
    # Many em-dashes in few words
    text = "This — which is fast — and also this — which is clean — and that — works."
    audit = RulesEngine.audit_text(text)
    assert any("Rule 17" in v["rule"] for v in audit["violations"])

def test_flesch_reading_score():
    simple_text = "The cat sat on the mat. Dogs run fast in the yard."
    score = RulesEngine.calculate_flesch(simple_text)
    assert score >= 70.0
