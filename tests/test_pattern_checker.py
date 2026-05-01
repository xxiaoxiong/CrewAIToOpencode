from src.quality.pattern_checker import scan_bad_patterns


def test_scan_bad_patterns_finds_hits():
    result = scan_bad_patterns("+ it.skip('works')\n+ console.log('debug')")

    assert result["passed"] is False
    assert "it.skip" in result["hits"]
    assert "console.log(" in result["hits"]


def test_scan_bad_patterns_passes_clean_diff():
    result = scan_bad_patterns("+ print('hello')")

    assert result["passed"] is True
    assert result["hits"] == []
