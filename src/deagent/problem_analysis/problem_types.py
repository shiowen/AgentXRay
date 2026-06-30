"""Structured problem types produced from evaluation feedback."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List


class ProblemCategory(Enum):
    INTERFACE_DIFFERENCE = "interface_difference"
    LOGIC_DIFFERENCE = "logic_difference"
    SEMANTIC_DIFFERENCE = "semantic_difference"
    OVERALL_DIFFERENCE = "overall_difference"
    UNKNOWN_CATEGORY = "unknown_category"


class InterfaceType(Enum):
    FUNCTION_SIGNATURE_DIFF = "function_signature_diff"
    CLASS_STRUCTURE_DIFF = "class_structure_diff"
    MODULE_ORGANIZATION_DIFF = "module_organization_diff"
    MISSING_FUNCTIONS = "missing_functions"
    MISSING_CLASSES = "missing_classes"
    MISSING_MODULES = "missing_modules"


class LogicType(Enum):
    ALGORITHM_PATTERN_DIFF = "algorithm_pattern_diff"
    CONTROL_FLOW_DIFF = "control_flow_diff"
    COMPUTATIONAL_LOGIC_DIFF = "computational_logic_diff"
    IMPLEMENTATION_METHOD_DIFF = "implementation_method_diff"


class SemanticType(Enum):
    NAMING_SEMANTICS_DIFF = "naming_semantics_diff"
    CODE_INTENT_DIFF = "code_intent_diff"
    VARIABLE_NAMING_DIFF = "variable_naming_diff"
    FUNCTION_NAMING_DIFF = "function_naming_diff"


class SeverityLevel(Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


SEVERITY_WEIGHTS = {
    SeverityLevel.CRITICAL: 1.0,
    SeverityLevel.HIGH: 0.8,
    SeverityLevel.MEDIUM: 0.6,
    SeverityLevel.LOW: 0.4,
}


@dataclass
class Problem:
    category: ProblemCategory
    specific_type: str
    severity: SeverityLevel
    description: str = ""
    count: int = 1
    location: str = ""
    keywords: List[str] = field(default_factory=list)
    raw_data: Dict = field(default_factory=dict)

    @property
    def severity_weight(self) -> float:
        return SEVERITY_WEIGHTS.get(self.severity, SEVERITY_WEIGHTS[SeverityLevel.MEDIUM])

    @property
    def priority_score(self) -> float:
        return self.severity_weight * min(self.count / 5.0 + 0.5, 1.0)

    def to_dict(self) -> Dict:
        return {
            "category": self.category.value,
            "specific_type": self.specific_type,
            "severity": self.severity.value,
            "description": self.description,
            "count": self.count,
            "location": self.location,
            "keywords": self.keywords,
            "severity_weight": self.severity_weight,
            "priority_score": self.priority_score,
            "raw_data": self.raw_data,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "Problem":
        return cls(
            category=ProblemCategory(data["category"]),
            specific_type=data["specific_type"],
            severity=SeverityLevel(data["severity"]),
            description=data.get("description", ""),
            count=data.get("count", 1),
            location=data.get("location", ""),
            keywords=data.get("keywords", []),
            raw_data=data.get("raw_data", {}),
        )

    def is_similar_to(self, other: "Problem") -> bool:
        return self.category == other.category and self.specific_type == other.specific_type

    def merge_with(self, other: "Problem") -> "Problem":
        if not self.is_similar_to(other):
            raise ValueError("Cannot merge dissimilar problems")

        severity = (
            self.severity
            if self.severity_weight >= other.severity_weight
            else other.severity
        )
        return Problem(
            category=self.category,
            specific_type=self.specific_type,
            severity=severity,
            description=f"{self.description}; {other.description}".strip("; "),
            count=self.count + other.count,
            location=f"{self.location}, {other.location}".strip(", "),
            keywords=sorted(set(self.keywords + other.keywords)),
            raw_data={**self.raw_data, **other.raw_data},
        )


@dataclass
class ProblemList:
    problems: List[Problem]
    source_evaluation_score: float = 0.0
    extraction_timestamp: str = ""

    def __post_init__(self):
        if not self.extraction_timestamp:
            self.extraction_timestamp = datetime.now().isoformat()

    @property
    def total_count(self) -> int:
        return len(self.problems)

    @property
    def total_frequency(self) -> int:
        return sum(problem.count for problem in self.problems)

    def get_by_category(self, category: ProblemCategory) -> List[Problem]:
        return [problem for problem in self.problems if problem.category == category]

    def get_by_severity(self, severity: SeverityLevel) -> List[Problem]:
        return [problem for problem in self.problems if problem.severity == severity]

    def get_critical_problems(self) -> List[Problem]:
        return self.get_by_severity(SeverityLevel.CRITICAL)

    def get_high_priority_problems(self) -> List[Problem]:
        return [
            problem
            for problem in self.problems
            if problem.severity in {SeverityLevel.CRITICAL, SeverityLevel.HIGH}
        ]

    def get_top_priority_problems(self, limit: int = 5) -> List[Problem]:
        return sorted(self.problems, key=lambda item: item.priority_score, reverse=True)[:limit]

    def get_interface_problems(self) -> List[Problem]:
        return self.get_by_category(ProblemCategory.INTERFACE_DIFFERENCE)

    def get_logic_problems(self) -> List[Problem]:
        return self.get_by_category(ProblemCategory.LOGIC_DIFFERENCE)

    def get_semantic_problems(self) -> List[Problem]:
        return self.get_by_category(ProblemCategory.SEMANTIC_DIFFERENCE)

    def merge_similar_problems(self) -> "ProblemList":
        merged: List[Problem] = []
        for problem in self.problems:
            for index, existing in enumerate(merged):
                if existing.is_similar_to(problem):
                    merged[index] = existing.merge_with(problem)
                    break
            else:
                merged.append(problem)

        return ProblemList(
            problems=merged,
            source_evaluation_score=self.source_evaluation_score,
            extraction_timestamp=self.extraction_timestamp,
        )

    def to_dict(self) -> Dict:
        return {
            "problems": [problem.to_dict() for problem in self.problems],
            "total_count": self.total_count,
            "total_frequency": self.total_frequency,
            "source_evaluation_score": self.source_evaluation_score,
            "extraction_timestamp": self.extraction_timestamp,
            "summary": self.get_summary(),
            "category_breakdown": self.get_category_breakdown(),
            "severity_breakdown": self.get_severity_breakdown(),
        }

    def get_summary(self) -> Dict:
        top_problems = self.get_top_priority_problems(3)
        return {
            "total_problems": self.total_count,
            "total_frequency": self.total_frequency,
            "categories": self.get_category_breakdown(),
            "severities": self.get_severity_breakdown(),
            "top_issues": [
                {
                    "category": problem.category.value,
                    "type": problem.specific_type,
                    "severity": problem.severity.value,
                    "priority_score": problem.priority_score,
                }
                for problem in top_problems
            ],
        }

    def get_category_breakdown(self) -> Dict[str, int]:
        return {
            category.value: len(self.get_by_category(category))
            for category in ProblemCategory
            if self.get_by_category(category)
        }

    def get_severity_breakdown(self) -> Dict[str, int]:
        return {
            severity.value: len(self.get_by_severity(severity))
            for severity in SeverityLevel
            if self.get_by_severity(severity)
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "ProblemList":
        return cls(
            problems=[Problem.from_dict(problem) for problem in data["problems"]],
            source_evaluation_score=data.get("source_evaluation_score", 0.0),
            extraction_timestamp=data.get("extraction_timestamp", ""),
        )


TYPE_MAPPINGS = {
    ProblemCategory.INTERFACE_DIFFERENCE: {
        "function_signature_diff": InterfaceType.FUNCTION_SIGNATURE_DIFF,
        "class_structure_diff": InterfaceType.CLASS_STRUCTURE_DIFF,
        "module_organization_diff": InterfaceType.MODULE_ORGANIZATION_DIFF,
        "missing_functions": InterfaceType.MISSING_FUNCTIONS,
        "missing_classes": InterfaceType.MISSING_CLASSES,
        "missing_modules": InterfaceType.MISSING_MODULES,
    },
    ProblemCategory.LOGIC_DIFFERENCE: {
        "algorithm_pattern_diff": LogicType.ALGORITHM_PATTERN_DIFF,
        "control_flow_diff": LogicType.CONTROL_FLOW_DIFF,
        "computational_logic_diff": LogicType.COMPUTATIONAL_LOGIC_DIFF,
        "implementation_method_diff": LogicType.IMPLEMENTATION_METHOD_DIFF,
    },
    ProblemCategory.SEMANTIC_DIFFERENCE: {
        "naming_semantics_diff": SemanticType.NAMING_SEMANTICS_DIFF,
        "code_intent_diff": SemanticType.CODE_INTENT_DIFF,
        "variable_naming_diff": SemanticType.VARIABLE_NAMING_DIFF,
        "function_naming_diff": SemanticType.FUNCTION_NAMING_DIFF,
    },
}


COMMON_PROBLEM_PATTERNS = {
    "missing_main_function": Problem(
        category=ProblemCategory.INTERFACE_DIFFERENCE,
        specific_type=InterfaceType.MISSING_FUNCTIONS.value,
        severity=SeverityLevel.HIGH,
        description="Missing required main function.",
    ),
    "class_structure_mismatch": Problem(
        category=ProblemCategory.INTERFACE_DIFFERENCE,
        specific_type=InterfaceType.CLASS_STRUCTURE_DIFF.value,
        severity=SeverityLevel.MEDIUM,
        description="Class structure differs from the reference.",
    ),
    "algorithm_implementation_diff": Problem(
        category=ProblemCategory.LOGIC_DIFFERENCE,
        specific_type=LogicType.ALGORITHM_PATTERN_DIFF.value,
        severity=SeverityLevel.HIGH,
        description="Algorithm implementation differs from the reference.",
    ),
    "control_flow_mismatch": Problem(
        category=ProblemCategory.LOGIC_DIFFERENCE,
        specific_type=LogicType.CONTROL_FLOW_DIFF.value,
        severity=SeverityLevel.MEDIUM,
        description="Control flow differs from the reference.",
    ),
    "naming_style_diff": Problem(
        category=ProblemCategory.SEMANTIC_DIFFERENCE,
        specific_type=SemanticType.NAMING_SEMANTICS_DIFF.value,
        severity=SeverityLevel.LOW,
        description="Naming style differs from the reference.",
    ),
    "code_intent_mismatch": Problem(
        category=ProblemCategory.SEMANTIC_DIFFERENCE,
        specific_type=SemanticType.CODE_INTENT_DIFF.value,
        severity=SeverityLevel.MEDIUM,
        description="Code intent differs from the reference.",
    ),
}


def create_problem_from_evaluation_data(
    category: str,
    specific_type: str,
    evaluation_data: Dict,
    severity: str = "medium",
) -> Problem:
    """Create a ``Problem`` from evaluator output fields."""

    category_map = {
        "interface": ProblemCategory.INTERFACE_DIFFERENCE,
        "logic": ProblemCategory.LOGIC_DIFFERENCE,
        "semantic": ProblemCategory.SEMANTIC_DIFFERENCE,
        "overall": ProblemCategory.OVERALL_DIFFERENCE,
    }
    severity_map = {
        "critical": SeverityLevel.CRITICAL,
        "high": SeverityLevel.HIGH,
        "medium": SeverityLevel.MEDIUM,
        "low": SeverityLevel.LOW,
    }
    return Problem(
        category=category_map.get(category.lower(), ProblemCategory.UNKNOWN_CATEGORY),
        specific_type=specific_type,
        severity=severity_map.get(severity.lower(), SeverityLevel.MEDIUM),
        description=str(evaluation_data),
        raw_data=evaluation_data,
    )
