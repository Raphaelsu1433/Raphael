"""
manager_agent.py

A simple Manager Agent that delegates quality-control checks to specialized reviewer tools,
then approves or critiques a draft based on specific criteria.

Run:
    python3 manager_agent.py

Optional:
    Edit SAMPLE_TEXT or CRITERIA at the bottom to test your own draft.
"""

from dataclasses import dataclass
from typing import Callable, List, Dict, Any
import re


@dataclass
class ReviewResult:
    tool_name: str
    passed: bool
    score: float
    max_score: float
    feedback: str


@dataclass
class Criterion:
    name: str
    description: str
    weight: float
    review_tool: Callable[[str, "Criterion"], ReviewResult]


class ManagerAgent:
    """
    Manager Agent:
    1. Delegates draft review to specialized tools.
    2. Aggregates scores.
    3. Produces final approval or critique.
    """

    def __init__(self, criteria: List[Criterion], approval_threshold: float = 0.8):
        if not criteria:
            raise ValueError("At least one criterion is required.")
        self.criteria = criteria
        self.approval_threshold = approval_threshold

    def evaluate(self, draft: str) -> Dict[str, Any]:
        results = []

        for criterion in self.criteria:
            result = criterion.review_tool(draft, criterion)
            results.append(result)

        total_weight = sum(c.weight for c in self.criteria)
        weighted_score = 0.0

        for criterion, result in zip(self.criteria, results):
            normalized = result.score / result.max_score if result.max_score else 0
            weighted_score += normalized * criterion.weight

        final_score = weighted_score / total_weight
        approved = final_score >= self.approval_threshold and all(r.passed for r in results)

        return {
            "approved": approved,
            "final_score": round(final_score, 3),
            "threshold": self.approval_threshold,
            "results": results,
            "summary": self._build_summary(approved, final_score, results),
        }

    def _build_summary(self, approved: bool, final_score: float, results: List[ReviewResult]) -> str:
        status = "APPROVED" if approved else "NEEDS REVISION"
        lines = [
            f"Manager Agent Decision: {status}",
            f"Final Quality Score: {final_score:.2%}",
            "",
            "Detailed Review:",
        ]

        for result in results:
            marker = "PASS" if result.passed else "FAIL"
            lines.append(f"- [{marker}] {result.tool_name}: {result.feedback}")

        if not approved:
            lines.append("")
            lines.append("Revision Priorities:")
            failed = [r for r in results if not r.passed]
            for i, result in enumerate(failed, start=1):
                lines.append(f"{i}. Improve: {result.tool_name} — {result.feedback}")

        return "\n".join(lines)


# -----------------------------
# Review Tools
# -----------------------------

def clarity_tool(draft: str, criterion: Criterion) -> ReviewResult:
    """
    Checks whether the draft is readable and avoids overly long sentences.
    """
    sentences = split_sentences(draft)
    if not sentences:
        return ReviewResult(
            tool_name=criterion.name,
            passed=False,
            score=0,
            max_score=10,
            feedback="No clear sentences were found."
        )

    long_sentences = [s for s in sentences if len(s.split()) > 30]
    average_length = sum(len(s.split()) for s in sentences) / len(sentences)

    score = 10
    if average_length > 25:
        score -= 3
    if long_sentences:
        score -= min(4, len(long_sentences) * 2)

    score = max(score, 0)
    passed = score >= 7

    feedback = (
        f"Average sentence length is {average_length:.1f} words. "
        f"{len(long_sentences)} sentence(s) are longer than 30 words."
    )

    if passed:
        feedback += " The draft is generally clear."
    else:
        feedback += " Shorten long sentences and simplify the wording."

    return ReviewResult(criterion.name, passed, score, 10, feedback)


def evidence_tool(draft: str, criterion: Criterion) -> ReviewResult:
    """
    Checks whether the draft contains evidence indicators such as data, citations,
    examples, or source references.
    """
    evidence_patterns = [
        r"\baccording to\b",
        r"\bresearch\b",
        r"\bstudy\b",
        r"\bdata\b",
        r"\bexample\b",
        r"\bsurvey\b",
        r"\binterview\b",
        r"\bsource\b",
        r"\[[0-9]+\]",
        r"\([A-Za-z]+,\s?\d{4}\)",
        r"https?://",
        r"\d+%",
    ]

    matches = sum(1 for pattern in evidence_patterns if re.search(pattern, draft, re.IGNORECASE))
    score = min(10, matches * 2.5)
    passed = score >= 5

    if passed:
        feedback = f"Found {matches} evidence signal(s). The draft has some support."
    else:
        feedback = (
            f"Found only {matches} evidence signal(s). Add citations, examples, data, "
            "or interview/source references."
        )

    return ReviewResult(criterion.name, passed, score, 10, feedback)


def completeness_tool(draft: str, criterion: Criterion) -> ReviewResult:
    """
    Checks whether the draft addresses key expected elements.
    For research quality control, the expected elements are:
    - claim or thesis
    - supporting evidence
    - analysis/explanation
    - limitation or counterpoint
    - conclusion/recommendation
    """
    expected_elements = {
        "claim/thesis": [r"\bargue\b", r"\bclaim\b", r"\bmain point\b", r"\bthesis\b", r"\bthis paper\b"],
        "supporting evidence": [r"\bevidence\b", r"\bdata\b", r"\bexample\b", r"\bstudy\b", r"\bsource\b"],
        "analysis": [r"\bbecause\b", r"\btherefore\b", r"\bthis suggests\b", r"\bthis means\b", r"\bas a result\b"],
        "limitation/counterpoint": [r"\bhowever\b", r"\blimitation\b", r"\balthough\b", r"\bon the other hand\b", r"\bcounterargument\b"],
        "conclusion/recommendation": [r"\bin conclusion\b", r"\boverall\b", r"\brecommend\b", r"\bshould\b", r"\btherefore\b"],
    }

    found = []
    missing = []

    for element, patterns in expected_elements.items():
        if any(re.search(pattern, draft, re.IGNORECASE) for pattern in patterns):
            found.append(element)
        else:
            missing.append(element)

    score = len(found) / len(expected_elements) * 10
    passed = score >= 7

    if passed:
        feedback = f"Found {len(found)}/{len(expected_elements)} key elements: {', '.join(found)}."
    else:
        feedback = (
            f"Found {len(found)}/{len(expected_elements)} key elements. "
            f"Missing: {', '.join(missing)}."
        )

    return ReviewResult(criterion.name, passed, score, 10, feedback)


def specificity_tool(draft: str, criterion: Criterion) -> ReviewResult:
    """
    Checks whether the draft avoids vague language and includes concrete details.
    """
    vague_words = [
        "things", "stuff", "many", "some", "very", "good", "bad",
        "important", "interesting", "a lot", "nice"
    ]

    vague_count = sum(len(re.findall(rf"\b{re.escape(word)}\b", draft, re.IGNORECASE)) for word in vague_words)
    numbers_count = len(re.findall(r"\b\d+(\.\d+)?%?\b", draft))
    proper_noun_count = len(re.findall(r"\b[A-Z][a-z]+(?:\s[A-Z][a-z]+)*\b", draft))

    score = 7 + min(3, numbers_count + proper_noun_count // 3) - min(5, vague_count)
    score = max(0, min(10, score))
    passed = score >= 7

    if passed:
        feedback = (
            f"Draft is reasonably specific. Detected {numbers_count} numeric detail(s) "
            f"and {proper_noun_count} possible named reference(s)."
        )
    else:
        feedback = (
            f"Draft may be too vague. Detected {vague_count} vague phrase(s), "
            f"{numbers_count} numeric detail(s), and {proper_noun_count} possible named reference(s)."
        )

    return ReviewResult(criterion.name, passed, score, 10, feedback)


# -----------------------------
# Helper Functions
# -----------------------------

def split_sentences(text: str) -> List[str]:
    return [s.strip() for s in re.split(r"[.!?。！？]+", text) if s.strip()]


def print_report(report: Dict[str, Any]) -> None:
    print(report["summary"])


# -----------------------------
# Sample Test
# -----------------------------

if __name__ == "__main__":
    CRITERIA = [
        Criterion(
            name="Clarity Review",
            description="The draft should be readable, direct, and not overloaded with long sentences.",
            weight=1.0,
            review_tool=clarity_tool,
        ),
        Criterion(
            name="Evidence Review",
            description="The draft should include evidence, examples, data, or source references.",
            weight=1.3,
            review_tool=evidence_tool,
        ),
        Criterion(
            name="Completeness Review",
            description="The draft should include claim, evidence, analysis, limitation, and conclusion.",
            weight=1.5,
            review_tool=completeness_tool,
        ),
        Criterion(
            name="Specificity Review",
            description="The draft should use concrete details instead of vague wording.",
            weight=1.0,
            review_tool=specificity_tool,
        ),
    ]

    SAMPLE_TEXT = """
    This paper argues that AI tools can improve student learning when they are used as guided tutors
    instead of simple answer machines. For example, a student can ask an AI system to explain each step
    of a thermodynamics problem, compare different solution methods, and generate practice questions.
    This suggests that AI is most useful when it supports active recall and feedback rather than passive copying.
    However, one limitation is that AI may produce incorrect explanations, so students should verify important
    claims with textbooks, class notes, or instructor feedback. Overall, students should use AI as a study partner
    that helps them think, not as a replacement for thinking.
    """

    manager = ManagerAgent(criteria=CRITERIA, approval_threshold=0.75)
    report = manager.evaluate(SAMPLE_TEXT)
    print_report(report)
