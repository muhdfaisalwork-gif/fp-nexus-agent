#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Copies the fp-nexus-agent skill to Antigravity global skills directory.
"""

import os
import shutil

def install_skill():
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    source_skill = os.path.join(repo_root, "skill", "SKILL.md")

    target_dir = os.path.expanduser(r"~\.gemini\config\skills\fp-nexus-agent")
    os.makedirs(target_dir, exist_ok=True)
    target_skill = os.path.join(target_dir, "SKILL.md")

    shutil.copy2(source_skill, target_skill)
    print(f"Installed fp-nexus-agent skill to:\n{target_skill}")

if __name__ == "__main__":
    install_skill()
