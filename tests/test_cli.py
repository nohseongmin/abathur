"""CLI 동작 및 실패 처리."""

import json

import pytest

from gaejosik import cli
from gaejosik.tokenizer import AnthropicCounter


def test_bench_json_shape(capsys):
    assert cli.main(["bench", "--format", "json"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["tokenizer"] == "o200k_base"
    assert data["rules"] and data["anti_rules"] and data["samples"]
    assert 0 < data["overall_ratio"] < 1
    assert data["korean_token_multiple"] > 1


def test_bench_markdown_has_tables(capsys):
    assert cli.main(["bench", "--format", "markdown"]) == 0
    out = capsys.readouterr().out
    assert out.count("|---") >= 4


def test_count_file(tmp_path, capsys):
    target = tmp_path / "sample.md"
    target.write_text("테스트 42개 전부 통과", encoding="utf-8")
    assert cli.main(["count", str(target)]) == 0
    assert "토큰" in capsys.readouterr().out


def test_count_with_price(tmp_path, capsys):
    target = tmp_path / "sample.md"
    target.write_text("테스트 42개 전부 통과", encoding="utf-8")
    assert cli.main(["count", str(target), "--price-per-mtok", "15"]) == 0
    assert "비용 환산" in capsys.readouterr().out


def test_count_missing_file_fails_cleanly(capsys):
    assert cli.main(["count", "존재하지_않는_파일.md"]) == 1
    err = capsys.readouterr().err
    assert "파일이 없습니다" in err
    assert "Traceback" not in err


def test_count_rejects_oversized_file(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(cli, "MAX_FILE_BYTES", 10)
    target = tmp_path / "big.md"
    target.write_text("가" * 100, encoding="utf-8")
    assert cli.main(["count", str(target)]) == 1
    assert "너무 큽니다" in capsys.readouterr().err


def test_unknown_encoding_fails_cleanly(capsys):
    assert cli.main(["bench", "--encoding", "존재하지않는인코딩"]) == 1
    assert "알 수 없는 tiktoken 인코딩" in capsys.readouterr().err


class _FakeCount:
    input_tokens = 7


class _FakeMessages:
    def __init__(self):
        self.calls = []

    def count_tokens(self, **kwargs):
        self.calls.append(kwargs)
        return _FakeCount()


class _FakeClient:
    def __init__(self):
        self.messages = _FakeMessages()


def test_anthropic_counter_uses_injected_client():
    """네트워크 없이 Anthropic 경로의 계약을 검증한다."""
    fake = _FakeClient()
    counter = AnthropicCounter(model="claude-sonnet-4-5", client=fake)
    assert counter.count("테스트") == 7
    assert counter.count("") == 0, "빈 문자열은 API를 부르지 않아야 한다"
    assert len(fake.messages.calls) == 1
    assert fake.messages.calls[0]["model"] == "claude-sonnet-4-5"


def test_anthropic_counter_requires_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY"):
        AnthropicCounter()
