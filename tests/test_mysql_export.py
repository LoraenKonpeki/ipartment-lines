from ipartment_lines.lines import LineRecord
from ipartment_lines.mysql_export import render_mysql_sql


def test_render_mysql_sql_uses_hex_literals_for_text_fields():
    sql = render_mysql_sql(
        [
            LineRecord(
                id="S01E01-000001000",
                season=1,
                episode=1,
                source="01 - 风景第一季1-5.mp4",
                start_ms=1000,
                end_ms=3000,
                text="不行 我这是婚车",
                screenshot_key="S01E01/1000.webp",
            )
        ],
        database="ipartment_lines",
    )

    assert "CREATE DATABASE IF NOT EXISTS `ipartment_lines`" in sql
    assert "INSERT INTO `lines`" in sql
    assert "0xE4B88DE8A18C20E68891E8BF99E698AFE5A99AE8BDA6" in sql
    assert "'S01E01-000001000'" in sql
