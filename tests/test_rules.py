"""규칙 회귀 테스트 — 이 프로젝트의 핵심 산출물.

스타일 가이드를 토크나이저로 검증한다. 규칙이 실제로 토큰을 줄이지 못하게 되면
(토크나이저 교체, 규칙 수정, 예문 변경 등) 여기서 깨진다.
"""

import pytest

from abathur import bench
from abathur.rules import (
    ANTI_RULES,
    CLAIMED_SAVING_PCT,
    MARGINAL_RULES,
    MIN_RULE_SAVING_RATIO,
    RULES,
    SAMPLES,
)
from abathur.tokenizer import TiktokenCounter


@pytest.fixture(scope="module")
def report():
    return bench.run(TiktokenCounter())


def test_rule_corpus_is_not_empty():
    assert RULES and ANTI_RULES and SAMPLES


def test_rule_ids_unique():
    ids = [r.id for r in RULES + MARGINAL_RULES + ANTI_RULES]
    assert len(ids) == len(set(ids))


def test_marginal_rules_are_real_but_small(report):
    """이득이 실재하되 기준 미만이어야 한다. 양쪽 어디로도 뭉개지 않는다."""
    for m in report.marginal_rules:
        assert 0 < m.ratio < MIN_RULE_SAVING_RATIO, (
            f"{m.name}: {m.ratio * 100:.1f}% — 기준을 넘으면 RULES로, "
            "이득이 없으면 ANTI_RULES로 옮겨라."
        )


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


def test_spacing_removal_is_a_net_loss(report):
    """띄어쓰기를 지우면 글자는 줄고 토큰은 늘어난다."""
    by_id = {m.id: m for m in report.anti_rules}
    assert by_id["spacing"].saved < 0


def test_arrow_sign_depends_on_what_it_replaces(report):
    """화살표는 접속사를 대체하면 이득, 구두점을 대체하면 무이득.

    '화살표는 항상 이득/항상 손해' 양쪽 주장이 다 틀렸다는 것이 핵심 발견이라
    두 경우를 함께 고정한다.
    """
    conj = {m.id: m for m in report.marginal_rules}["conj_arrow"]
    punct = {m.id: m for m in report.anti_rules}["arrow_for_punct"]
    assert conj.saved > 0, "접속사 치환은 이득이어야 한다"
    assert punct.saved == 0, "구두점 치환은 동률이어야 한다"


def test_studies_have_rows(report):
    assert report.studies
    for study in report.studies:
        assert study.rows, f"{study.id}: 원자료가 비었다"
    ids = [row.id for study in report.studies for row in study.rows]
    assert len(ids) == len(set(ids))


def test_arrow_gain_is_korean_only(report):
    """화살표 이득은 한국어 접속사에서만 난다 — 영어 대조군은 0이어야 한다."""
    rows = {m.name: m for s in report.studies if s.id == "arrow_alternatives" for m in s.rows}
    assert rows["영어 대조"].saved == 0
    assert all(rows[k].saved > 0 for k in rows if k.startswith("접속사"))
    assert all(rows[k].saved == 0 for k in rows if k.startswith("구두점"))


@pytest.mark.parametrize("encoding", ["o200k_base", "cl100k_base"])
def test_savings_hold_across_tokenizers(encoding):
    """o200k에서만 통하는 우연이 아님을 확인한다."""
    result = bench.run(TiktokenCounter(encoding))
    assert result.overall_ratio * 100 >= CLAIMED_SAVING_PCT
