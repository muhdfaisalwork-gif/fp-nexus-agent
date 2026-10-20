import pytest
from core.rules.humanizer import Humanizer

def test_extract_clean_candidate():
    raw = """
<think>
Let me analyze the prompt and write a good proposal.
</think>
```markdown
We can implement your scraping bot using Playwright and Python.
```
"""
    cleaned = Humanizer.extract_clean_candidate(raw)
    assert "<think>" not in cleaned
    assert "Let me analyze" not in cleaned
    assert "We can implement your scraping bot" in cleaned

def test_humanize_buzzword_replacement():
    raw = "We utilize Redis to facilitate rapid order processing and elevate overall performance."
    humanized, audit = Humanizer.humanize_text(raw)
    assert "utilize" not in humanized.lower()
    assert "facilitate" not in humanized.lower()
    assert "elevate" not in humanized.lower()
    assert "use" in humanized.lower()
    assert "help" in humanized.lower()

def test_humanize_strips_proposal_fluff():
    raw = "I hope this proposal finds you well. We can configure your Docker containers today."
    humanized, audit = Humanizer.humanize_text(raw)
    assert "hope this proposal finds you well" not in humanized.lower()
    assert "We can configure your Docker containers today" in humanized

def test_humanize_caps_em_dashes():
    raw = "We deploy with Docker — which is fast — and configure Nginx — which routes traffic — safely."
    humanized, audit = Humanizer.humanize_text(raw)
    dashes_count = humanized.count("—") + humanized.count("--")
    assert dashes_count <= 1
