# eval/models.py
from dataclasses import dataclass, field


@dataclass
class MetricScore:
    name: str
    passed: int
    total: int

    @property
    def score_pct(self) -> float:
        if self.total == 0:
            return 0.0
        return round(self.passed / self.total * 100, 1)

    @property
    def symbol(self) -> str:
        if self.score_pct >= 85:
            return "✓"
        if self.score_pct >= 70:
            return "⚠"
        return "✗"


@dataclass
class FailureDetail:
    case_id: str
    metric: str
    input_summary: str
    expected: str
    actual: str


@dataclass
class EvalResult:
    area: str
    metrics: list = field(default_factory=list)       # list[MetricScore]
    failures: list = field(default_factory=list)      # list[FailureDetail]

    @property
    def overall_score(self) -> float:
        if not self.metrics:
            return 0.0
        total_pct = sum(m.score_pct for m in self.metrics)
        return round(total_pct / len(self.metrics), 1)

    @property
    def passed(self) -> bool:
        return self.overall_score >= 85.0
