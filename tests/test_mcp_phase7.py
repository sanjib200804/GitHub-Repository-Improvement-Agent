"""Phase 7 Test: README Generator Verification.

Demonstrates and verifies:
1. Synthesizing repository evidence and analysis report into an improved README.
2. Checking presence of all 12 required sections:
   - Project Title
   - Description
   - Features
   - Tech Stack
   - Architecture
   - Installation
   - Environment Variables
   - Usage
   - Project Structure
   - API / MCP Tools
   - Examples
   - Future Improvements
3. Verifying grounding against real repository details.
"""

import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.readme_generator import generate_improved_readme, REQUIRED_README_SECTIONS


def test_readme_generator():
    print("=" * 60)
    print("  PHASE 7: README GENERATOR VERIFICATION")
    print("=" * 60)

    repo_url = "octocat/Hello-World"
    print(f"\n[1] Generating Improved README for '{repo_url}'...")

    readme_markdown = generate_improved_readme(repo_url)

    print("\n[2] Generated README Excerpt:")
    lines = readme_markdown.splitlines()
    for line in lines[:25]:
        print(f"    {line}")
    if len(lines) > 25:
        print(f"    ... [{len(lines) - 25} more lines] ...")

    # 3. Verify all 12 required sections are present
    print("\n[3] Validating 12 Required Sections:")
    lower_readme = readme_markdown.lower()

    # Section 1: Project Title (Must start with an H1 header '# <Title>')
    has_h1 = readme_markdown.strip().startswith("# ")
    print(f"    - Section: Project Title (H1 Header) {'[FOUND]' if has_h1 else '[MISSING]'}")
    assert has_h1, "README must begin with an H1 Project Title (# <Title>)"

    # Sections 2-12: The specific H2 sections
    h2_sections = [
        "Description",
        "Features",
        "Tech Stack",
        "Architecture",
        "Installation",
        "Environment Variables",
        "Usage",
        "Project Structure",
        "API",
        "Examples",
        "Future Improvements",
    ]

    for section in h2_sections:
        section_key = section.lower()
        found = section_key in lower_readme
        print(f"    - Section: {section:<25} {'[FOUND]' if found else '[MISSING]'}")
        assert found, f"Missing required README section: {section}"

    # 4. Verify grounding
    assert "octocat" in lower_readme or "hello-world" in lower_readme
    assert len(readme_markdown) > 500

    print("\n" + "=" * 60)
    print("  ALL PHASE 7 README GENERATOR CHECKS PASSED SUCCESSFULLY!")
    print("=" * 60)


if __name__ == "__main__":
    test_readme_generator()
