# eval/models.py
from dataclasses import dataclass, field


@dataclass
class MetricScore:
    name: str
    passed: int
    total: int

    def __post_init__(self):
        if self.total < 0 or self.passed < 0:
            raise ValueError(f"passed and total must be non-negative, got passed={self.passed}, total={self.total}")
        if self.passed > self.total:
            raise ValueError(f"passed ({self.passed}) cannot exceed total ({self.total})")

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
    metrics: list[MetricScore] = field(default_factory=list)
    failures: list[FailureDetail] = field(default_factory=list)

    @property
    def overall_score(self) -> float:
        if not self.metrics:
            return 0.0
        total_pct = sum(m.score_pct for m in self.metrics)
        return round(total_pct / len(self.metrics), 1)

    @property
    def passed(self) -> bool:
        return self.overall_score >= 85.0
