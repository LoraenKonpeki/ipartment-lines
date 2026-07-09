from ipartment_lines.sources import parse_part_title


def test_parse_chinese_season_and_episode_range():
    part = parse_part_title("风景第三季21-24")

    assert part.season == 3
    assert part.first_episode == 21
    assert part.last_episode == 24


def test_parse_part_title_rejects_non_episode_part():
    assert parse_part_title("点点关注不迷路，补档一辈子") is None

