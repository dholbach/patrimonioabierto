"""Tests for the wording of the province/category pages' intro texts in
build_monument_pages.py: counts, gender and the sentences derived from data.

Run with `python3 -m unittest discover -s tests` from scripts/, or
`make test` from the repo root.
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from build_monument_pages import (  # noqa: E402 - path setup above must run first
    category_summary,
    counted,
    oldest_sentence,
    photo_and_wikidata_sentence,
    province_summary,
)


def record(name, municipality="Aldea", category="CASTILLOS", date="1949-04-22", photo=False, linked=True, jcyl_id=1):
    return {
        "jcyl_id": jcyl_id,
        "name": name,
        "municipality": municipality,
        "category": category,
        "protection_date": date,
        "has_wikidata_image": photo,
        "already_linked": linked,
    }


class CountedTests(unittest.TestCase):
    def test_singular_and_plural(self):
        self.assertEqual(counted(1, "CASTILLOS"), "1 castillo")
        self.assertEqual(counted(175, "CASTILLOS"), "175 castillos")

    def test_uncountable_heading_gets_a_countable_noun(self):
        self.assertEqual(counted(25, "ARTE RUPESTRE"), "25 yacimientos de arte rupestre")

    def test_unknown_category_falls_back_to_bienes(self):
        self.assertEqual(counted(3, "ALGO NUEVO"), "3 bienes")


class PhotoSentenceTests(unittest.TestCase):
    def recs(self, photos, total=10):
        return [record(f"M{i}", photo=i < photos, jcyl_id=i) for i in range(total)]

    def test_none_one_and_several(self):
        self.assertTrue(photo_and_wikidata_sentence(self.recs(0)).startswith("Ninguno tiene fotografía libre"))
        self.assertTrue(photo_and_wikidata_sentence(self.recs(1)).startswith("Solo uno tiene fotografía libre"))
        self.assertTrue(photo_and_wikidata_sentence(self.recs(4)).startswith("4 de ellos tienen fotografía libre"))

    def test_feminine(self):
        self.assertTrue(photo_and_wikidata_sentence(self.recs(0), "f").startswith("Ninguna tiene"))
        self.assertIn("enlazadas a Wikidata", photo_and_wikidata_sentence(self.recs(2), "f"))

    def test_mentions_missing_photos_only_when_most_lack_one(self):
        self.assertIn("Aún faltan fotografías libres de 9", photo_and_wikidata_sentence(self.recs(1)))
        self.assertNotIn("Aún faltan", photo_and_wikidata_sentence(self.recs(8)))
        self.assertNotIn("Aún faltan", photo_and_wikidata_sentence(self.recs(10)))

    def test_singular_link_count_agrees(self):
        recs = [record("A", linked=True), record("B", linked=False)]
        self.assertIn("1 está enlazado a Wikidata", photo_and_wikidata_sentence(recs))


class OldestTests(unittest.TestCase):
    def test_names_the_earliest_by_year(self):
        recs = [record("Nuevo", date="1990-01-01"), record("Viejo", "Villa", date="1931-05-03")]
        self.assertEqual(oldest_sentence(recs), "El más antiguo, Viejo (Villa), está protegido desde 1931.")

    def test_feminine_form(self):
        self.assertTrue(oldest_sentence([record("X", date="1931-05-03")], "f").startswith("La más antigua"))

    def test_a_tie_on_the_earliest_date_names_nobody(self):
        recs = [record("A", date="1984-01-01"), record("B", date="1984-01-01"), record("C", date="1990-01-01")]
        self.assertEqual(oldest_sentence(recs), "La protección más antigua data de 1984.")

    def test_nothing_without_dates(self):
        self.assertEqual(oldest_sentence([record("X", date=None)]), "")


class SummaryTests(unittest.TestCase):
    def test_category_summary_reads_correctly_for_arte_rupestre(self):
        recs = [record(f"R{i}", f"M{i % 3}", "ARTE RUPESTRE", jcyl_id=i) for i in range(5)]
        text = category_summary("Zamora", "ARTE RUPESTRE", recs)
        self.assertIn("5 yacimientos de arte rupestre protegidos como Bien de Interés Cultural en la provincia de Zamora", text)
        self.assertIn("en 3 municipios", text)
        self.assertIn("M0 reúne 2 de ellos.", text)

    def test_category_summary_skips_the_biggest_municipality_when_all_are_alone(self):
        recs = [record(f"C{i}", f"Aldea{i}", jcyl_id=i) for i in range(5)]
        self.assertNotIn("reúne", category_summary("Soria", "CASTILLOS", recs))

    def test_province_summary_names_top_category_and_municipality(self):
        recs = [record("A", "Villa", "CASTILLOS", jcyl_id=1), record("B", "Villa", "CASTILLOS", jcyl_id=2), record("C", "Otra", "MONUMENTO", jcyl_id=3)]
        text = province_summary("Burgos", recs)
        self.assertIn("3 bienes protegidos", text)
        self.assertIn("La categoría más numerosa es «Castillos» (2)", text)
        self.assertIn("el municipio con más bienes es Villa (2)", text)

    def test_one_of_everything_uses_singular(self):
        text = province_summary("Soria", [record("A")])
        self.assertIn("1 bien protegido", text)
        self.assertIn("1 municipio y 1 categoría", text)


if __name__ == "__main__":
    unittest.main()
