"""ASR measurement helpers (scripts/asr/common.py) on synthetic data only: no real names or speech."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts", "asr"))
from common import align, attribution, fmt, norm, parse, speaker_wer, to_global, trim, words  # noqa: E402


def w(text, speaker="Спикер 1", t=0):
    return [(t, speaker, x) for x in map(norm, text.split())]


class TestLines(unittest.TestCase):
    def test_parse_and_fmt_round_trip(self):
        self.assertEqual(parse("[1:02:03] Спикер 2: Добрый день."), (3723, "Спикер 2", "Добрый день."))
        self.assertIsNone(parse("# Кусок A"))
        self.assertEqual(fmt(3723.9), "1:02:03")

    def test_norm_drops_punctuation_case_and_yo(self):
        self.assertEqual(norm("Ещё,"), "еще")
        self.assertEqual(norm("«Да»"), "да")

    def test_words_keep_only_the_window(self):
        lines = ["[0:00:59] Спикер 1: раз", "[0:01:00] Спикер 1: два три", "[0:03:00] Спикер 2: четыре"]
        self.assertEqual([x[2] for x in words(lines, 60, 180)], ["два", "три"])


class TestTimeline(unittest.TestCase):
    def test_speech_only_time_maps_back_to_the_recording(self):
        entry = {"offset": 100.0, "map": [[0.0, 2.0, 10.0], [2.6, 5.6, 40.0]]}
        self.assertAlmostEqual(to_global(entry, 1.0), 111.0)
        self.assertAlmostEqual(to_global(entry, 3.6), 141.0)
        self.assertAlmostEqual(to_global(entry, 2.2), 112.2)  # inside the gap: still the first piece


class TestScoring(unittest.TestCase):
    def test_align_counts_substitution_deletion_insertion(self):
        ops = align(w("мама мыла раму"), w("мама мыла большую раму"))
        self.assertEqual([o[0] for o in ops], ["=", "=", "I", "="])
        ops = align(w("мама мыла раму"), w("папа раму"))
        self.assertEqual(sum(o[0] != "=" for o in ops), 2)

    def test_trim_drops_the_wider_window_edges(self):
        ops = align(w("два три"), w("раз два три четыре"))
        self.assertEqual([o[0] for o in trim(ops)], ["=", "="])

    def test_a_repeated_word_past_the_edge_is_not_an_error(self):
        ref = w("а с ним будут они")
        hyp = w("до этого") + w("а с ним будут они вот они")
        self.assertEqual(speaker_wer(ref, hyp), (5, 0))

    def test_identical_text_scores_zero(self):
        ref = w("добрый день коллеги") + w("спасибо", "Спикер 2")
        self.assertEqual(speaker_wer(ref, list(ref)), (4, 0))
        self.assertEqual(attribution(ref, list(ref)), (4, 4))

    def test_phrase_order_between_speakers_is_not_an_error(self):
        ref = w("добрый день", "Спикер 1") + w("здравствуйте", "Спикер 2")
        hyp = w("здравствуйте", "Спикер 2") + w("добрый день", "Спикер 1")
        self.assertEqual(speaker_wer(ref, hyp), (3, 0))

    def test_a_speaker_never_recognised_counts_as_deletions(self):
        ref = w("добрый день", "Спикер 1") + w("ну да", "Спикер 2")
        self.assertEqual(speaker_wer(ref, w("добрый день", "Спикер 1")), (4, 2))

    def test_wrong_speaker_lowers_attribution(self):
        ref = w("добрый день коллеги", "Спикер 1")
        hyp = w("добрый день", "Спикер 1") + w("коллеги", "Спикер 2")
        self.assertEqual(attribution(ref, hyp), (2, 3))


if __name__ == "__main__":
    unittest.main()
