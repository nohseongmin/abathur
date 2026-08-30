"""문서에 박힌 수치가 코드의 측정치와 어긋나지 않는지 확인한다.

같은 값이 두 곳(SKILL.md와 코드)에 미러링돼 있으면 한쪽만 바뀌어 조용히 썩는다.
"""

import re
from pathlib import Path

from abathur import bench
from abathur.rules import ANTI_RULES, CLAIMED_SAVING_PCT
from abathur.tokenizer import TiktokenCounter

ROOT = Path(__file__).resolve().parents[1]
SKILL_PATH = ROOT / "skills" / "abathur" / "SKILL.md"
README_PATH = ROOT / "README.md"


def read_skill() -> str:
    return SKILL_PATH.read_text(encoding="utf-8")


def test_skill_file_exists():
    assert SKILL_PATH.is_file(), f"스킬 파일 없음: {SKILL_PATH}"


def test_skill_frontmatter_has_name_and_description():
    text = read_skill()
    assert text.startswith("---\n")
    frontmatter = text.split("---", 2)[1]
    assert re.search(r"^name:\s*abathur\s*$", frontmatter, re.M)
    assert re.search(r"^description:", frontmatter, re.M)


def test_skill_claims_the_same_number_as_code():
    """스킬이 내건 절감률이 CLAIMED_SAVING_PCT와 일치해야 한다."""
    assert f"{CLAIMED_SAVING_PCT}%" in read_skill(), (
        f"SKILL.md의 절감률 주장이 코드의 {CLAIMED_SAVING_PCT}%와 다르다."
    )


def test_skill_lists_every_anti_rule():
    """안티규칙 표가 코드보다 뒤처지면 사용자가 기각된 규칙을 계속 쓰게 된다."""
    text = read_skill()
    section = text.split("## 하지 말 것")[1].split("## 강도")[0]
    rows = [
        line.strip() for line in section.splitlines()
        if line.startswith("|") and set(line.strip()) - set("|-: ")
    ]
    entries = len(rows) - 1  # 첫 행은 헤더 (구분선은 위 필터에서 이미 제외)
    assert entries == len(ANTI_RULES), (
        f"SKILL.md 안티규칙 {entries}개 != 코드 {len(ANTI_RULES)}개"
    )


def test_bench_md_is_current():
    """BENCH.md가 `abathur bench --format markdown` 출력과 일치해야 한다.

    손으로 갱신하는 표는 규칙이나 렌더러가 바뀌면 조용히 썩는다. README가
    "CI가 최신 여부 검사"라고 내건 것을 실제로 검사한다.
    """
    generated = bench.render_markdown(bench.run(TiktokenCounter()))
    on_disk = (ROOT / "BENCH.md").read_text(encoding="utf-8")
    assert on_disk.rstrip("\n") == generated.rstrip("\n"), (
        "BENCH.md가 실측과 어긋난다. "
        "`python -m abathur bench --format markdown > BENCH.md`로 다시 생성하라."
    )


def test_readme_total_row_matches_measurement():
    """README의 합계 행이 실측과 어긋나면 실패한다."""
    report = bench.run(TiktokenCounter())
    row = re.search(
        r"\|\s*\*\*합계\*\*\s*\|\s*\*\*(\d+)\*\*\s*\|\s*\*\*(\d+)\*\*\s*\|\s*\*\*(\d+)%\*\*",
        README_PATH.read_text(encoding="utf-8"),
    )
    assert row, "README에서 합계 행을 찾지 못했다"
    before, after, pct = (int(g) for g in row.groups())
    assert (before, after) == (report.sample_before, report.sample_after)
    assert pct == round(report.overall_ratio * 100)
