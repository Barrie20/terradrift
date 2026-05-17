from terradrift.taxonomy import CATEGORY_INFO, Category, classify


def test_known_rule_maps_to_category() -> None:
    assert classify("CKV_AWS_20") == Category.PUBLIC_EXPOSURE


def test_unknown_rule_falls_back_to_other() -> None:
    assert classify("CKV_AWS_999999") == Category.OTHER


def test_every_category_has_info() -> None:
    """Every category must carry a description and a real-world example
    — this is part of our publication contract."""
    for cat in Category:
        info = CATEGORY_INFO[cat]
        assert info.description
        assert info.real_world_example
