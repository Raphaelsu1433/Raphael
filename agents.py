"""Integrated Researcher + Manager agent pipeline.

This file keeps the agent logic separate from the UI so it can be tested
from a CLI, a Streamlit app, or another frontend later.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Callable, Dict, List, Any, Optional
import os
import re


# -----------------------------
# Shared log model
# -----------------------------

@dataclass
class AgentLogEntry:
    step: int
    agent: str
    action: str
    message: str
    timestamp: str


class InteractionLogger:
    def __init__(self) -> None:
        self.entries: List[AgentLogEntry] = []

    def add(self, agent: str, action: str, message: str) -> None:
        self.entries.append(
            AgentLogEntry(
                step=len(self.entries) + 1,
                agent=agent,
                action=action,
                message=message,
                timestamp=datetime.now().isoformat(timespec="seconds"),
            )
        )

    def as_dicts(self) -> List[Dict[str, Any]]:
        return [asdict(entry) for entry in self.entries]

    def as_text(self) -> str:
        lines = []
        for entry in self.entries:
            lines.append(
                f"[{entry.step}] {entry.timestamp} | {entry.agent} | "
                f"{entry.action}: {entry.message}"
            )
        return "\n".join(lines)


# -----------------------------
# Researcher Agent
# -----------------------------

class ResearcherAgent:
    """Generates a draft answer.

    Uses Gemini when GEMINI_API_KEY is available. Otherwise, uses a deterministic
    fallback response so the pipeline demo still runs without external services.
    """

    SYSTEM_PROMPT = """
You are a Researcher Agent.
Your job is to answer factual research questions clearly and carefully.

Rules:
1. Give concise, factual answers.
2. If uncertain, say what is uncertain.
3. Do not invent facts.
4. Prefer dates, names, numbers, examples, and concrete details when possible.
5. Include a clear claim, evidence, analysis, limitation, and conclusion.
"""

    def __init__(self, model_name: str = "gemini-2.5-flash") -> None:
        self.model_name = model_name
        self.api_key = os.getenv("GEMINI_API_KEY")
        self._model = None

        if self.api_key:
            try:
                import google.generativeai as genai

                genai.configure(api_key=self.api_key)
                self._model = genai.GenerativeModel(
                    model_name=self.model_name,
                    system_instruction=self.SYSTEM_PROMPT,
                )
            except Exception as exc:  # keep UI usable even if SDK is missing
                self._model = None
                self._init_error = str(exc)
        else:
            self._init_error = "GEMINI_API_KEY not set; using offline fallback."

    def research(self, prompt: str) -> str:
        if self._model is not None:
            response = self._model.generate_content(prompt)
            return response.text.strip()

        return self._fallback_research(prompt)

    def revise(self, prompt: str, draft: str, manager_feedback: str) -> str:
        revision_prompt = f"""
User prompt:
{prompt}

Draft answer:
{draft}

Manager feedback:
{manager_feedback}

Revise the answer so it is clearer, more complete, evidence-based, specific,
and includes a limitation plus a conclusion.
""".strip()

        if self._model is not None:
            response = self._model.generate_content(revision_prompt)
            return response.text.strip()

        return self._fallback_revision(prompt, draft, manager_feedback)

    def _fallback_research(self, prompt: str) -> str:
        return (
            f"This answer argues that the best response to the prompt '{prompt}' is to give a "
            "structured, evidence-based explanation rather than a vague opinion. For example, "
            "a useful research answer should define the topic, give concrete examples, explain "
            "why those examples matter, and separate confirmed facts from uncertainty. This "
            "suggests that a Researcher Agent should produce a first draft with a claim, evidence, "
            "analysis, and practical conclusion. However, one limitation is that this offline demo "
            "does not access live web data or an external language model, so factual claims should "
            "be verified with reliable sources before final use. Overall, the answer should be "
            "clear, specific, and transparent about uncertainty."
        )

    def _fallback_revision(self, prompt: str, draft: str, manager_feedback: str) -> str:
        return (
            f"This revised answer argues that '{prompt}' should be answered through a clear "
            "research workflow: identify the main claim, provide evidence or examples, explain "
            "the meaning of that evidence, mention limitations, and finish with a practical "
            "conclusion. For example, in this integrated system, the UI receives the user's prompt, "
            "the Researcher Agent creates a draft, and the Manager Agent checks clarity, evidence, "
            "completeness, and specificity. This means the final answer is not shown immediately; "
            "it is first reviewed against explicit quality criteria. However, one limitation is that "
            "the offline demo uses a deterministic fallback unless GEMINI_API_KEY is configured. "
            "Overall, the pipeline improves reliability because it logs every step and only displays "
            "the final answer after Manager approval."
        )


# -----------------------------
# Manager Agent and review tools
# -----------------------------

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
    def __init__(self, criteria: List[Criterion], approval_threshold: float = 0.75):
        if not criteria:
            raise ValueError("At least one criterion is required.")
        self.criteria = criteria
        self.approval_threshold = approval_threshold

    def evaluate(self, draft: str) -> Dict[str, Any]:
        results = [criterion.review_tool(draft, criterion) for criterion in self.criteria]
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


def split_sentences(text: str) -> List[str]:
    return [s.strip() for s in re.split(r"[.!?。！？]+", text) if s.strip()]


def clarity_tool(draft: str, criterion: Criterion) -> ReviewResult:
    sentences = split_sentences(draft)
    if not sentences:
        return ReviewResult(criterion.name, False, 0, 10, "No clear sentences were found.")

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
    feedback += " The draft is generally clear." if passed else " Shorten long sentences."
    return ReviewResult(criterion.name, passed, score, 10, feedback)


def evidence_tool(draft: str, criterion: Criterion) -> ReviewResult:
    evidence_patterns = [
        r"\baccording to\b", r"\bresearch\b", r"\bstudy\b", r"\bdata\b",
        r"\bexample\b", r"\bsurvey\b", r"\binterview\b", r"\bsource\b",
        r"\[[0-9]+\]", r"\([A-Za-z]+,\s?\d{4}\)", r"https?://", r"\d+%",
    ]
    matches = sum(1 for pattern in evidence_patterns if re.search(pattern, draft, re.IGNORECASE))
    score = min(10, matches * 2.5)
    passed = score >= 5
    feedback = (
        f"Found {matches} evidence signal(s). The draft has some support."
        if passed
        else f"Found only {matches} evidence signal(s). Add citations, examples, data, or source references."
    )
    return ReviewResult(criterion.name, passed, score, 10, feedback)


def completeness_tool(draft: str, criterion: Criterion) -> ReviewResult:
    expected_elements = {
        "claim/thesis": [r"\bargue\b", r"\bclaim\b", r"\bmain point\b", r"\bthesis\b"],
        "supporting evidence": [r"\bevidence\b", r"\bdata\b", r"\bexample\b", r"\bstudy\b", r"\bsource\b"],
        "analysis": [r"\bbecause\b", r"\btherefore\b", r"\bthis suggests\b", r"\bthis means\b", r"\bas a result\b"],
        "limitation/counterpoint": [r"\bhowever\b", r"\blimitation\b", r"\balthough\b", r"\bon the other hand\b"],
        "conclusion/recommendation": [r"\bin conclusion\b", r"\boverall\b", r"\brecommend\b", r"\bshould\b", r"\btherefore\b"],
    }
    found, missing = [], []
    for element, patterns in expected_elements.items():
        (found if any(re.search(p, draft, re.IGNORECASE) for p in patterns) else missing).append(element)
    score = len(found) / len(expected_elements) * 10
    passed = score >= 7
    feedback = (
        f"Found {len(found)}/{len(expected_elements)} key elements: {', '.join(found)}."
        if passed
        else f"Found {len(found)}/{len(expected_elements)} key elements. Missing: {', '.join(missing)}."
    )
    return ReviewResult(criterion.name, passed, score, 10, feedback)


def specificity_tool(draft: str, criterion: Criterion) -> ReviewResult:
    vague_words = ["things", "stuff", "many", "some", "very", "good", "bad", "important", "interesting", "a lot", "nice"]
    vague_count = sum(len(re.findall(rf"\b{re.escape(word)}\b", draft, re.IGNORECASE)) for word in vague_words)
    numbers_count = len(re.findall(r"\b\d+(\.\d+)?%?\b", draft))
    proper_noun_count = len(re.findall(r"\b[A-Z][a-z]+(?:\s[A-Z][a-z]+)*\b", draft))
    score = 7 + min(3, numbers_count + proper_noun_count // 3) - min(5, vague_count)
    score = max(0, min(10, score))
    passed = score >= 7
    feedback = (
        f"Draft is reasonably specific. Detected {numbers_count} numeric detail(s) and {proper_noun_count} possible named reference(s)."
        if passed
        else f"Draft may be too vague. Detected {vague_count} vague phrase(s), {numbers_count} numeric detail(s), and {proper_noun_count} possible named reference(s)."
    )
    return ReviewResult(criterion.name, passed, score, 10, feedback)


def default_manager() -> ManagerAgent:
    criteria = [
        Criterion("Clarity Review", "Readable, direct, not overloaded with long sentences.", 1.0, clarity_tool),
        Criterion("Evidence Review", "Includes evidence, examples, data, or source references.", 1.3, evidence_tool),
        Criterion("Completeness Review", "Includes claim, evidence, analysis, limitation, and conclusion.", 1.5, completeness_tool),
        Criterion("Specificity Review", "Uses concrete details instead of vague wording.", 1.0, specificity_tool),
    ]
    return ManagerAgent(criteria=criteria, approval_threshold=0.75)


# -----------------------------
# Integrated pipeline
# -----------------------------

class AgentPipeline:
    def __init__(self, researcher: Optional[ResearcherAgent] = None, manager: Optional[ManagerAgent] = None):
        self.researcher = researcher or ResearcherAgent()
        self.manager = manager or default_manager()

    def run(self, prompt: str, max_revision_rounds: int = 1) -> Dict[str, Any]:
        if not prompt.strip():
            raise ValueError("Prompt cannot be empty.")

        logger = InteractionLogger()
        logger.add("UI", "received_prompt", prompt)

        logger.add("Pipeline", "route", "Sending user prompt to Researcher Agent.")
        draft = self.researcher.research(prompt)
        logger.add("Researcher", "draft_created", draft[:500])

        current_answer = draft
        report = self.manager.evaluate(current_answer)
        logger.add("Manager", "review_completed", report["summary"])

        rounds_used = 0
        while not report["approved"] and rounds_used < max_revision_rounds:
            rounds_used += 1
            logger.add("Pipeline", "revision_requested", "Manager rejected draft; sending feedback to Researcher.")
            current_answer = self.researcher.revise(prompt, current_answer, report["summary"])
            logger.add("Researcher", "revision_created", current_answer[:500])
            report = self.manager.evaluate(current_answer)
            logger.add("Manager", "review_completed", report["summary"])

        status = "approved" if report["approved"] else "not_approved_after_revision_limit"
        logger.add("UI", "display_final_answer", f"Final status: {status}; score={report['final_score']}.")

        return {
            "prompt": prompt,
            "final_answer": current_answer,
            "approved": report["approved"],
            "manager_report": report,
            "log": logger.as_dicts(),
            "log_text": logger.as_text(),
        }
