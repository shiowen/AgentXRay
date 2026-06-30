"""Parse evaluator feedback into structured problem records."""

import json
import logging
import re
from typing import Any, Dict, List, Optional, Tuple

from .problem_types import (
    InterfaceType,
    LogicType,
    Problem,
    ProblemCategory,
    ProblemList,
    SemanticType,
    SeverityLevel,
)

logger = logging.getLogger(__name__)


class EvaluationTextParser:
    """Convert similarity-analysis text into a ``ProblemList``."""

    def __init__(self):
        self.category_mappings: Dict[str, ProblemCategory] = {
            "interface": ProblemCategory.INTERFACE_DIFFERENCE,
            "api": ProblemCategory.INTERFACE_DIFFERENCE,
            "signature": ProblemCategory.INTERFACE_DIFFERENCE,
            "function": ProblemCategory.INTERFACE_DIFFERENCE,
            "class": ProblemCategory.INTERFACE_DIFFERENCE,
            "module": ProblemCategory.INTERFACE_DIFFERENCE,
            "logic": ProblemCategory.LOGIC_DIFFERENCE,
            "algorithm": ProblemCategory.LOGIC_DIFFERENCE,
            "control flow": ProblemCategory.LOGIC_DIFFERENCE,
            "implementation": ProblemCategory.LOGIC_DIFFERENCE,
            "semantic": ProblemCategory.SEMANTIC_DIFFERENCE,
            "naming": ProblemCategory.SEMANTIC_DIFFERENCE,
            "intent": ProblemCategory.SEMANTIC_DIFFERENCE,
            "overall": ProblemCategory.OVERALL_DIFFERENCE,
        }
        self.problem_type_mappings: Dict[str, str] = {
            "signature": InterfaceType.FUNCTION_SIGNATURE_DIFF.value,
            "function": InterfaceType.MISSING_FUNCTIONS.value,
            "class": InterfaceType.CLASS_STRUCTURE_DIFF.value,
            "module": InterfaceType.MODULE_ORGANIZATION_DIFF.value,
            "missing": InterfaceType.MISSING_FUNCTIONS.value,
            "algorithm": LogicType.ALGORITHM_PATTERN_DIFF.value,
            "control flow": LogicType.CONTROL_FLOW_DIFF.value,
            "logic": LogicType.COMPUTATIONAL_LOGIC_DIFF.value,
            "implementation": LogicType.IMPLEMENTATION_METHOD_DIFF.value,
            "naming": SemanticType.NAMING_SEMANTICS_DIFF.value,
            "variable": SemanticType.VARIABLE_NAMING_DIFF.value,
            "intent": SemanticType.CODE_INTENT_DIFF.value,
        }
        self.severity_patterns: Dict[SeverityLevel, List[str]] = {
            SeverityLevel.CRITICAL: [r"\bcritical\b", r"\bfatal\b", r"\bsevere\b"],
            SeverityLevel.HIGH: [r"\bhigh\b", r"\bmajor\b", r"\bmissing\b"],
            SeverityLevel.MEDIUM: [r"\bmedium\b", r"\bmoderate\b", r"\bdifferent\b"],
            SeverityLevel.LOW: [r"\blow\b", r"\bminor\b", r"\bsmall\b"],
        }

    def parse_evaluation_result(self, similarity_score: float, analysis_text: str) -> ProblemList:
        problems: List[Problem] = []
        try:
            problems.extend(self._extract_from_json_differences(analysis_text))
            problems.extend(self._extract_from_marked_sections(analysis_text))
            problems.extend(self._extract_from_summary_text(analysis_text, similarity_score))
            merged = self._merge_similar_problems(problems)
            return ProblemList(
                problems=merged,
                source_evaluation_score=similarity_score,
            ).merge_similar_problems()
        except Exception as exc:
            logger.warning("Failed to parse evaluation output: %s", exc)
            return self._create_fallback_problem_list(similarity_score)

    def _extract_from_json_differences(self, text: str) -> List[Problem]:
        json_text = self._find_first_json_object(text)
        if not json_text:
            return []

        try:
            differences = json.loads(json_text)
        except json.JSONDecodeError:
            return []

        problems: List[Problem] = []
        if not isinstance(differences, dict):
            return problems

        for category_key, category_data in differences.items():
            category = self._parse_category(str(category_key))
            if isinstance(category_data, dict):
                for issue_type, issue_details in category_data.items():
                    problem = self._create_problem_from_json_data(
                        category,
                        str(issue_type),
                        issue_details,
                    )
                    if problem:
                        problems.append(problem)
            else:
                problems.append(
                    Problem(
                        category=category,
                        specific_type=self._determine_problem_type(str(category_key), category),
                        severity=self._determine_severity_from_data(str(category_key), category_data),
                        description=f"{category_key}: {category_data}",
                        count=self._count_issues_in_data(category_data),
                        raw_data={"data": category_data},
                    )
                )
        return problems

    @staticmethod
    def _find_first_json_object(text: str) -> Optional[str]:
        start = text.find("{")
        if start == -1:
            return None

        depth = 0
        in_string = False
        escape = False
        for index in range(start, len(text)):
            char = text[index]
            if in_string:
                if escape:
                    escape = False
                elif char == "\\":
                    escape = True
                elif char == '"':
                    in_string = False
                continue
            if char == '"':
                in_string = True
            elif char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    return text[start : index + 1]
        return None

    def _extract_from_marked_sections(self, text: str) -> List[Problem]:
        patterns = [
            r"(?:critical issues|main issues|main problems)\s*:?\s*\n(.*?)(?=\n\n|recommendations|$)",
            r"(?:recommendations|improvement recommendations)\s*:?\s*\n(.*?)(?=\n\n|$)",
        ]
        problems: List[Problem] = []
        for pattern in patterns:
            for match in re.finditer(pattern, text, flags=re.IGNORECASE | re.DOTALL):
                for issue_text in self._iter_issue_lines(match.group(1)):
                    category = self._categorize_issue_text(issue_text)
                    problems.append(
                        Problem(
                            category=category,
                            specific_type=self._determine_problem_type(issue_text, category),
                            severity=self._determine_severity_from_text(issue_text),
                            description=issue_text,
                            keywords=self._extract_keywords_from_text(issue_text),
                        )
                    )
        return problems

    @staticmethod
    def _iter_issue_lines(section: str) -> List[str]:
        issues = []
        for line in section.splitlines():
            clean_line = re.sub(r"^\s*(?:[-*]|\d+[.)])\s*", "", line).strip()
            if clean_line and len(clean_line) > 3:
                issues.append(clean_line)
        return issues

    def _extract_from_summary_text(self, text: str, score: float) -> List[Problem]:
        severity = self._severity_from_score(score)
        if severity is None:
            return []

        issues = self._extract_specific_issues_from_text(text)
        if not issues:
            return [
                Problem(
                    category=ProblemCategory.OVERALL_DIFFERENCE,
                    specific_type="general_functionality_difference",
                    severity=severity,
                    description=f"Similarity score {score:.3f} indicates a functional gap.",
                )
            ]

        problems = []
        for issue in issues:
            category = self._categorize_issue_text(issue)
            problems.append(
                Problem(
                    category=category,
                    specific_type=self._determine_problem_type(issue, category),
                    severity=severity,
                    description=issue,
                    keywords=self._extract_keywords_from_text(issue),
                )
            )
        return problems

    @staticmethod
    def _severity_from_score(score: float) -> Optional[SeverityLevel]:
        if score < 0.35:
            return SeverityLevel.CRITICAL
        if score < 0.50:
            return SeverityLevel.HIGH
        if score < 0.70:
            return SeverityLevel.MEDIUM
        return None

    def _create_problem_from_json_data(
        self,
        category: ProblemCategory,
        issue_type: str,
        issue_details: Any,
    ) -> Optional[Problem]:
        return Problem(
            category=category,
            specific_type=self._determine_problem_type(issue_type, category),
            severity=self._determine_severity_from_data(issue_type, issue_details),
            description=self._create_description_from_data(issue_type, issue_details),
            count=self._count_issues_in_data(issue_details),
            raw_data=issue_details if isinstance(issue_details, dict) else {"data": issue_details},
        )

    def _parse_category(self, category_key: str) -> ProblemCategory:
        category_key_lower = category_key.lower()
        for key, category in self.category_mappings.items():
            if key in category_key_lower:
                return category
        return ProblemCategory.UNKNOWN_CATEGORY

    def _categorize_issue_text(self, issue_text: str) -> ProblemCategory:
        issue_lower = issue_text.lower()
        if any(word in issue_lower for word in ["function", "class", "module", "api", "interface", "signature", "missing"]):
            return ProblemCategory.INTERFACE_DIFFERENCE
        if any(word in issue_lower for word in ["algorithm", "logic", "flow", "implementation", "behavior"]):
            return ProblemCategory.LOGIC_DIFFERENCE
        if any(word in issue_lower for word in ["naming", "semantic", "intent", "meaning"]):
            return ProblemCategory.SEMANTIC_DIFFERENCE
        return ProblemCategory.OVERALL_DIFFERENCE

    def _determine_problem_type(self, issue_text: str, category: ProblemCategory) -> str:
        issue_lower = issue_text.lower()
        for keyword, problem_type in self.problem_type_mappings.items():
            if keyword in issue_lower:
                return problem_type

        if category == ProblemCategory.INTERFACE_DIFFERENCE:
            return "interface_general_difference"
        if category == ProblemCategory.LOGIC_DIFFERENCE:
            return "logic_general_difference"
        if category == ProblemCategory.SEMANTIC_DIFFERENCE:
            return "semantic_general_difference"
        return "unknown_difference"

    def _determine_severity_from_text(self, text: str) -> SeverityLevel:
        text_lower = text.lower()
        for severity, patterns in self.severity_patterns.items():
            if any(re.search(pattern, text_lower) for pattern in patterns):
                return severity
        return SeverityLevel.MEDIUM

    def _determine_severity_from_data(self, issue_type: str, issue_details: Any) -> SeverityLevel:
        issue_lower = issue_type.lower()
        if any(word in issue_lower for word in ["missing", "critical", "fatal", "severe"]):
            return SeverityLevel.CRITICAL
        if any(word in issue_lower for word in ["error", "failure", "major", "mismatch"]):
            return SeverityLevel.HIGH
        if self._count_issues_in_data(issue_details) >= 5:
            return SeverityLevel.HIGH
        return SeverityLevel.MEDIUM

    @staticmethod
    def _create_description_from_data(issue_type: str, issue_details: Any) -> str:
        if isinstance(issue_details, dict):
            return f"{issue_type}: {str(issue_details)[:160]}"
        if isinstance(issue_details, list):
            return f"{issue_type}: {len(issue_details)} items"
        return f"{issue_type}: {issue_details}"

    @staticmethod
    def _count_issues_in_data(issue_details: Any) -> int:
        if isinstance(issue_details, dict):
            return sum(len(value) if isinstance(value, list) else 1 for value in issue_details.values())
        if isinstance(issue_details, list):
            return len(issue_details)
        return 1

    def _extract_specific_issues_from_text(self, text: str) -> List[str]:
        patterns = [
            r"(missing\s+[^.\n;]+)",
            r"([^.\n;]*(?:mismatch|difference|error|failure|bug)[^.\n;]*)",
            r"([^.\n;]*(?:needs?|should|must)\s+(?:be\s+)?(?:fixed|improved|implemented)[^.\n;]*)",
        ]
        issues: List[str] = []
        for pattern in patterns:
            for match in re.findall(pattern, text, flags=re.IGNORECASE):
                issue = match.strip()
                if len(issue) > 8:
                    issues.append(issue)
        return sorted(set(issues))

    @staticmethod
    def _extract_keywords_from_text(text: str) -> List[str]:
        tech_keywords = [
            "algorithm",
            "api",
            "bug",
            "class",
            "control",
            "error",
            "function",
            "interface",
            "logic",
            "method",
            "missing",
            "module",
            "naming",
            "performance",
            "signature",
            "variable",
        ]
        text_lower = text.lower()
        return [keyword for keyword in tech_keywords if keyword in text_lower]

    def _merge_similar_problems(self, problems: List[Problem]) -> List[Problem]:
        merged: List[Problem] = []
        for problem in problems:
            for index, existing in enumerate(merged):
                if existing.is_similar_to(problem):
                    merged[index] = existing.merge_with(problem)
                    break
            else:
                merged.append(problem)
        return merged

    def _create_fallback_problem_list(self, score: float) -> ProblemList:
        severity = self._severity_from_score(score) or SeverityLevel.LOW
        return ProblemList(
            problems=[
                Problem(
                    category=ProblemCategory.OVERALL_DIFFERENCE,
                    specific_type="general_functionality_difference",
                    severity=severity,
                    description=f"Similarity score {score:.3f} requires review.",
                )
            ],
            source_evaluation_score=score,
        )


def parse_evaluation_output(similarity_score: float, analysis_text: str) -> ProblemList:
    """Parse the output from ``evaluate_similarity_with_analysis``."""

    return EvaluationTextParser().parse_evaluation_result(similarity_score, analysis_text)


def quick_parse_evaluation(evaluation_result: Tuple[float, str]) -> ProblemList:
    """Parse a ``(score, text)`` evaluation tuple."""

    score, text = evaluation_result
    return parse_evaluation_output(score, text)
