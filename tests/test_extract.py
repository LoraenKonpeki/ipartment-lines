from ipartment_lines.extract import iter_sample_times, pick_recognition_region


def test_iter_sample_times_includes_start_and_stops_before_end():
    assert list(iter_sample_times(1000, 5000, 2000)) == [1000, 3000]


def test_pick_recognition_region_uses_center_band():
    assert pick_recognition_region({"x": 360, "y": 790, "w": 1200, "h": 230}) == {
        "x": 80,
        "y": 35,
        "w": 1040,
        "h": 170,
    }

