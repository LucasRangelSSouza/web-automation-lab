import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
S = json.loads((ROOT / "results" / "summary.json").read_text())


def test_all_four_tools_eventually_ran():
    assert S["tools_with_success"] == S["tools"] == 4


def test_harness_caused_most_failures():
    assert S["harness_failures"] > S["other_failures"]


def test_three_different_numbers_not_a_ranking():
    # the three headline timings measure different things on a trivial page
    assert S["m_playwright_goto_ms_median"] < S["m_obscura_fetch_ms_median"] < 1000 * S["m_crawl4ai_example_com_s"]
