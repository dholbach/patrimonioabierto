"""Tests for names.py (accent restoration for monument names).

Run with `python3 -m unittest discover -s tests` from scripts/, or
`make test` from the repo root.
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from names import build_corpus, fold, restore_accents  # noqa: E402 - path setup above must run first


class FoldTests(unittest.TestCase):
    def test_drops_accents_tildes_and_case(self):
        self.assertEqual(fold("Peña Uñor Asunción"), "pena unor asuncion")


class LabelTests(unittest.TestCase):
    def test_copies_accents_from_a_matching_label(self):
        name, how = restore_accents("Iglesia de Nuestra Señora de la Asuncion", "iglesia de Nuestra Señora de la Asunción")
        self.assertEqual((name, how), ("Iglesia de Nuestra Señora de la Asunción", "label"))

    def test_keeps_the_names_own_capitalisation(self):
        # The label says "castillo ... La Adrada"; only accents may come over.
        name, _ = restore_accents("Castillo de la Adrada", "Castillo de La Adrada")
        self.assertEqual(name, "Castillo de la Adrada")
        name, _ = restore_accents("Castillo de Arevalo", "castillo de Arévalo")
        self.assertEqual(name, "Castillo de Arévalo")

    def test_all_caps_stays_all_caps(self):
        name, _ = restore_accents("PUENTE DE ALCANTARA", "puente de Alcántara")
        self.assertEqual(name, "PUENTE DE ALCÁNTARA")

    def test_different_name_in_the_label_is_ignored(self):
        # Wikidata names a different thing: nothing to copy, no corpus given.
        self.assertEqual(restore_accents("Castillo de la Triste Condesa", "Castillo de Arenas de San Pedro"), ("Castillo de la Triste Condesa", None))

    def test_unchanged_when_label_has_no_extra_accents(self):
        self.assertEqual(restore_accents("Puente de Medina", "puente de Medina"), ("Puente de Medina", None))

    def test_already_accented_words_are_kept(self):
        name, _ = restore_accents("Convento de San José", "convento de San José")
        self.assertEqual(name, "Convento de San José")

    def test_punctuation_and_numbers_survive(self):
        name, _ = restore_accents("Canal de Castilla: Esclusa 10 Ramal Norte", "Esclusa 10 del Canal de Castilla")
        self.assertEqual(name, "Canal de Castilla: Esclusa 10 Ramal Norte")


class DictionaryTests(unittest.TestCase):
    def setUp(self):
        self.corpus = build_corpus(
            [
                "iglesia de Santa María",
                "ermita de Santa María",
                "Castillo de Arévalo",
                "Fábrica de harinas",
                "si lo sabe",  # "si" is a plain word here ...
                "sí lo dice",  # ... and an accented one there: ambiguous
                "Peña Uñor",
            ]
        )

    def test_restores_a_dominant_accented_word(self):
        self.assertEqual(restore_accents("Iglesia de Santa Maria", None, self.corpus), ("Iglesia de Santa María", "dictionary"))

    def test_restores_several_words_and_keeps_case(self):
        name, how = restore_accents("FABRICA DE ARQUETAS Y CASTILLO DE AREVALO", None, self.corpus)
        self.assertEqual(name, "FÁBRICA DE ARQUETAS Y CASTILLO DE ARÉVALO")
        self.assertEqual(how, "dictionary")

    def test_leaves_ambiguous_words_alone(self):
        self.assertEqual(restore_accents("Si", None, self.corpus), ("Si", None))

    def test_leaves_unknown_words_alone(self):
        self.assertEqual(restore_accents("Torreon de Cardaba", None, self.corpus), ("Torreon de Cardaba", None))

    def test_tilde_words(self):
        self.assertEqual(restore_accents("Pena Unor", None, self.corpus), ("Peña Uñor", "dictionary"))

    def test_label_wins_over_dictionary_and_dictionary_fills_the_rest(self):
        # The label does not match, so the dictionary decides.
        self.assertEqual(restore_accents("Iglesia de Santa Maria", "Ermita de otro sitio", self.corpus)[1], "dictionary")

    def test_dictionary_finishes_what_a_partly_accented_label_leaves(self):
        # The label has María but still "Asuncion"; the dictionary knows it.
        corpus = build_corpus(["iglesia de la Asunción", "ermita de la Asunción"])
        name, how = restore_accents("Iglesia de Santa Maria de la Asuncion", "iglesia de Santa María de la Asuncion", corpus)
        self.assertEqual((name, how), ("Iglesia de Santa María de la Asunción", "label"))

    def test_no_corpus_and_no_label_changes_nothing(self):
        self.assertEqual(restore_accents("Iglesia de Santa Maria"), ("Iglesia de Santa Maria", None))


if __name__ == "__main__":
    unittest.main()
