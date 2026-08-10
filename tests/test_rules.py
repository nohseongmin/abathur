"""규칙 회귀 테스트 — 이 프로젝트의 핵심 산출물.

스타일 가이드를 토크나이저로 검증한다. 규칙이 실제로 토큰을 줄이지 못하게 되면
(토크나이저 교체, 규칙 수정, 예문 변경 등) 여기서 깨진다.
"""

import pytest

from gaejosik import bench
from gaejosik.rules import (
    ANTI_RULES,
    CLAIMED_SAVING_PCT,
    MIN_RULE_SAVING_RATIO,
    RULES,
    SAMPLES,
)
from gaejosik.tokenizer import TiktokenCounter


@pytest.fixture(scope="module")
def report():
    return bench.run(TiktokenCounter())


def test_rule_corpus_is_not_empty():
    assert RULES and ANTI_RULES and SAMPLES


def test_rule_ids_unique():
    ids = [r.id for r in RULES] + [r.id for r in ANTI_RULES]
    assert len(ids) == len(set(ids))


def test_every_rule_actually_saves_tokens(report):
    """규칙으로 실린 것은 전부 최소 절감률을 넘어야 한다."""
    weak = [
        f"{m.name}: {m.ratio * 100:.1f}%"
        for m in report.rules
        if m.ratio < MIN_RULE_SAVING_RATIO
    ]
    assert not weak, (
        f"토큰을 충분히 줄이지 못하는 규칙 (기준 {MIN_RULE_SAVING_RATIO * 100:.0f}%): {weak}. "
        "안티규칙으로 옮기거나 예문을 고쳐라."
    )


def test_anti_rules_really_have_no_gain(report):
    """안티규칙은 이득이 없다는 주장 자체가 측정으로 뒷받침돼야 한다.

    이득이 있는데 안티규칙에 넣어두면 사용자를 잘못 이끄는 것이므로 실패시킨다.
    """
    wrongly_rejected = [
        f"{m.name}: {m.ratio * 100:.1f}%"
        for m in report.anti_rules
        if m.ratio >= MIN_RULE_SAVING_RATIO
    ]
    assert not wrongly_rejected, (
        f"안티규칙인데 실제로는 토큰이 줄어든다: {wrongly_rejected}. "
        "규칙으로 승격하거나 근거를 다시 써라."
    )


def test_headline_claim_still_true(report):
    """대외 절감률 주장이 실측보다 크면 안 된다."""
    measured = report.overall_ratio * 100
    assert measured >= CLAIMED_SAVING_PCT, (
        f"주장 {CLAIMED_SAVING_PCT}% > 실측 {measured:.1f}%. 주장을 낮춰라."
    )


def test_korean_costs_more_tokens_than_english(report):
    """이 프로젝트의 전제. 깨지면 프로젝트의 존재 이유가 사라진다."""
    assert report.mean_lang_multiple > 1.0
    for m in report.languages:
        assert m.ko_tokens > m.en_tokens, f"한국어가 더 싼 반례: {m.korean}"


def test_arrow_and_spacing_are_net_losses(report):
    """가장 흔한 오해 두 가지는 이득이 아니라 손해라는 것까지 확인한다."""
    by_id = {m.id: m for m in report.anti_rules}
    assert by_id["arrow"].saved < 0
    assert by_id["spacing"].saved < 0


def test_ending_swap_saves_nothing(report):
    """어미 교체 0% — 스킬이 내세우는 대표 반례."""
    by_id = {m.id: m for m in report.anti_rules}
    assert by_id["ending_swap"].saved == 0


@pytest.mark.parametrize("encoding", ["o200k_base", "cl100k_base"])
def test_savings_hold_across_tokenizers(encoding):
    """o200k에서만 통하는 우연이 아님을 확인한다."""
    result = bench.run(TiktokenCounter(encoding))
    assert result.overall_ratio * 100 >= CLAIMED_SAVING_PCT
