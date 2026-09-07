from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path

import mwparserfromhell

from app.ml.dataset_builder import build_dataset, extract_infobox_fields


class DatasetBuilderTests(unittest.TestCase):
    def test_extract_infobox_fields_cleans_named_parameters(self) -> None:
        wikicode = mwparserfromhell.parse(
            "{{Infobox person\n"
            "| name = [[Ada Lovelace]]\n"
            "| birth_date = {{birth date|1815|12|10}}\n"
            "| occupation = mathematician<br />writer<ref>ignored</ref>\n"
            "| 1 = ignored positional value\n"
            "}}"
        )
        template = wikicode.filter_templates()[0]

        fields = extract_infobox_fields(template)

        self.assertEqual(fields["name"], "Ada Lovelace")
        self.assertIn("1815", fields["birth_date"])
        self.assertEqual(fields["occupation"], "mathematician writer")
        self.assertNotIn("1", fields)

    def test_build_dataset_writes_infobox_fields_column(self) -> None:
        xml = """<mediawiki>
  <page>
    <title>Ada Lovelace</title>
    <revision>
      <text>{{Infobox person
| name = [[Ada Lovelace]]
| birth_date = 10 December 1815
| occupation = mathematician and writer
}}
Ada Lovelace was an English mathematician and writer.</text>
    </revision>
  </page>
</mediawiki>"""

        with tempfile.TemporaryDirectory() as tmpdir:
            xml_path = Path(tmpdir) / "sample.xml"
            csv_path = Path(tmpdir) / "training.csv"
            xml_path.write_text(xml, encoding="utf-8")

            written = build_dataset(xml_path, csv_path)

            self.assertEqual(written, 1)
            with csv_path.open("r", encoding="utf-8", newline="") as handle:
                rows = list(csv.DictReader(handle))

        self.assertEqual(rows[0]["label"], "Infobox Person")
        fields = json.loads(rows[0]["infobox_fields"])
        self.assertEqual(fields["name"], "Ada Lovelace")
        self.assertEqual(fields["birth_date"], "10 December 1815")
        self.assertEqual(fields["occupation"], "mathematician and writer")


if __name__ == "__main__":
    unittest.main()
