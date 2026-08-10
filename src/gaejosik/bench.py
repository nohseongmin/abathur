"""규칙 코퍼스를 토크나이저로 실측한다."""

from __future__ import annotations

from dataclasses import dataclass, field

from .rules import ANTI_RULES, LANG_PAIRS, RULES, SAMPLES, Rule, Sample
from .tokenizer import TokenCounter


@dataclass(frozen=True)
class Measurement:
    id: str
    name: str
    category: str
    before: int
    after: int
    note: str = ""

    @property
    def saved(self) -> int:
        return self.before - self.after

    @property
    def ratio(self) -> float:
        """절감률(0~1). 이득이 없으면 0 이하."""
        return self.saved / self.before if self.before else 0.0


@dataclass(frozen=True)
class LangMeasurement:
    korean: str
    ko_tokens: int
    en_tokens: int

    @property
    def multiple(self) -> float:
        return self.ko_tokens / self.en_tokens if self.en_tokens else 0.0


@dataclass
class Report:
    counter_name: str
    rules: list[Measurement] = field(default_factory=list)
    anti_rules: list[Measurement] = field(default_factory=list)
    samples: list[Measurement] = field(default_factory=list)
    languages: list[LangMeasurement] = field(default_factory=list)

    @property
    def sample_before(self) -> int:
        return sum(m.before for m in self.samples)

    @property
    def sample_after(self) -> int:
        return sum(m.after for m in self.samples)

    @property
    def overall_ratio(self) -> float:
        """답변 표본 전체의 토큰 절감률. SKILL.md가 내거는 수치의 근거."""
        before = self.sample_before
        return (before - self.sample_after) / before if before else 0.0

    @property
    def mean_lang_multiple(self) -> float:
        if not self.languages:
            return 0.0
        return sum(m.multiple for m in self.languages) / len(self.languages)


def _measure(counter: TokenCounter, item: Rule | Sample) -> Measurement:
    return Measurement(
        id=item.id,
        name=item.name,
        category=getattr(item, "category", "sample"),
        before=counter.count(item.verbose),
        after=counter.count(item.terse),
        note=getattr(item, "note", ""),
    )


def run(counter: TokenCounter) -> Report:
    return Report(
        counter_name=counter.name,
        rules=[_measure(counter, r) for r in RULES],
        anti_rules=[_measure(counter, r) for r in ANTI_RULES],
        samples=[_measure(counter, s) for s in SAMPLES],
        languages=[
            LangMeasurement(ko, counter.count(ko), counter.count(en))
            for ko, en in LANG_PAIRS
        ],
    )


# --- 렌더링 ------------------------------------------------------------------


def _row(m: Measurement) -> str:
    return f"| {m.name} | {m.before} | {m.after} | {m.ratio * 100:.0f}% |"


def render_markdown(report: Report) -> str:
    lines = [
        f"토크나이저: `{report.counter_name}`",
        "",
        "### 이득이 확인된 규칙",
        "",
        "| 규칙 | 원문 토큰 | 개조식 토큰 | 절감 |",
        "|---|---:|---:|---:|",
    ]
    lines += [_row(m) for m in report.rules]
    lines += [
        "",
        "### 측정 결과 기각된 규칙 (안티규칙)",
        "",
        "그럴듯하지만 토큰이 줄지 않는다. 가독성만 잃으므로 쓰지 않는다.",
        "",
        "| 안티규칙 | 원문 토큰 | 축약 토큰 | 절감 |",
        "|---|---:|---:|---:|",
    ]
    lines += [_row(m) for m in report.anti_rules]
    lines += [
        "",
        "### 답변 한 통 기준 절감",
        "",
        "| 표본 | 원문 토큰 | 개조식 토큰 | 절감 |",
        "|---|---:|---:|---:|",
    ]
    lines += [_row(m) for m in report.samples]
    lines += [
        f"| **합계** | **{report.sample_before}** | **{report.sample_after}** "
        f"| **{report.overall_ratio * 100:.0f}%** |",
        "",
        "### 한국어 vs 영어 (같은 의미)",
        "",
        "| 한국어 문장 | 한국어 | 영어 | 배수 |",
        "|---|---:|---:|---:|",
    ]
    lines += [
        f"| {m.korean} | {m.ko_tokens} | {m.en_tokens} | {m.multiple:.2f}x |"
        for m in report.languages
    ]
    lines.append(f"| **평균** | | | **{report.mean_lang_multiple:.2f}x** |")
    return "\n".join(lines)


def render_text(report: Report) -> str:
    lines = [f"토크나이저: {report.counter_name}", "", "[이득 확인된 규칙]"]
    lines += [
        f"  {m.name:24s} {m.before:4d} -> {m.after:4d}  {m.ratio * 100:5.1f}%"
        for m in report.rules
    ]
    lines += ["", "[기각된 안티규칙 — 쓰지 말 것]"]
    lines += [
        f"  {m.name:24s} {m.before:4d} -> {m.after:4d}  {m.ratio * 100:5.1f}%"
        for m in report.anti_rules
    ]
    lines += ["", "[답변 한 통 기준]"]
    lines += [
        f"  {m.name:24s} {m.before:4d} -> {m.after:4d}  {m.ratio * 100:5.1f}%"
        for m in report.samples
    ]
    lines += [
        f"  {'합계':24s} {report.sample_before:4d} -> {report.sample_after:4d}  "
        f"{report.overall_ratio * 100:5.1f}%",
        "",
        f"[한국어/영어 토큰 배수] 평균 {report.mean_lang_multiple:.2f}x",
    ]
    return "\n".join(lines)


def to_dict(report: Report) -> dict:
    def pack(m: Measurement) -> dict:
        return {
            "id": m.id, "name": m.name, "category": m.category,
            "before": m.before, "after": m.after,
            "saved": m.saved, "ratio": round(m.ratio, 4),
        }

    return {
        "tokenizer": report.counter_name,
        "rules": [pack(m) for m in report.rules],
        "anti_rules": [pack(m) for m in report.anti_rules],
        "samples": [pack(m) for m in report.samples],
        "overall_ratio": round(report.overall_ratio, 4),
        "korean_token_multiple": round(report.mean_lang_multiple, 4),
    }
