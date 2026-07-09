from __future__ import annotations

from .lines import LineRecord


def render_mysql_sql(records: list[LineRecord], *, database: str = "ipartment_lines") -> str:
    lines = [
        "SET NAMES utf8mb4;",
        f"CREATE DATABASE IF NOT EXISTS `{database}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;",
        f"USE `{database}`;",
        "DROP TABLE IF EXISTS `lines`;",
        """
CREATE TABLE `lines` (
  `id` varchar(32) NOT NULL,
  `season` int NOT NULL,
  `episode` int NOT NULL,
  `source` varchar(255) NOT NULL,
  `start_ms` int NOT NULL,
  `end_ms` int NOT NULL,
  `text` text NOT NULL,
  `screenshot_key` varchar(255) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `idx_episode_time` (`season`, `episode`, `start_ms`),
  FULLTEXT KEY `ft_text` (`text`) WITH PARSER ngram
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
""".strip(),
    ]

    if records:
        values = [
            "("
            + ", ".join(
                [
                    _quote(record.id),
                    str(record.season),
                    str(record.episode),
                    _hex(record.source),
                    str(record.start_ms),
                    str(record.end_ms),
                    _hex(record.text),
                    _hex(record.screenshot_key),
                ]
            )
            + ")"
            for record in records
        ]
        lines.append(
            "INSERT INTO `lines` (`id`, `season`, `episode`, `source`, `start_ms`, `end_ms`, `text`, `screenshot_key`) VALUES\n"
            + ",\n".join(values)
            + ";"
        )

    return "\n\n".join(lines) + "\n"


def _quote(value: str) -> str:
    return "'" + value.replace("\\", "\\\\").replace("'", "\\'") + "'"


def _hex(value: str) -> str:
    return "0x" + value.encode("utf-8").hex().upper()

