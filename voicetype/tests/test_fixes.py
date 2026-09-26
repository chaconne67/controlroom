"""Which edits after a paste count as word fixes. Run: uv run python -m unittest tests.test_fixes"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from voicetype import fixes_in_field, word_fixes  # noqa: E402

P = "펀드키퍼 저장소에 커밋하고 푸시해 줘."


class WordFixes(unittest.TestCase):
    def test_misheard_name_keeps_particle_out(self):
        self.assertEqual(word_fixes("펀드키퍼에 올려 줘", "FundKeeper에 올려 줘"), [("펀드키퍼", "FundKeeper")])

    def test_multi_word_phrase_is_one_fix(self):
        self.assertEqual(word_fixes("클로드 코드로 열어 줘", "Claude Code로 열어 줘"), [("클로드 코드", "Claude Code")])

    def test_spacing_and_punctuation_are_not_fixes(self):
        self.assertEqual(word_fixes("돌려 보고 알려 줘.", "돌려보고 알려 줘!"), [])

    def test_typing_more_is_not_a_fix(self):
        self.assertEqual(word_fixes(P, P + " 그리고 배포도 해 줘."), [])

    def test_deleting_is_not_a_fix(self):
        self.assertEqual(word_fixes(P, "저장소에 커밋하고 푸시해 줘."), [])

    def test_rewrite_is_not_learned(self):
        self.assertEqual(word_fixes(P, "오늘은 쉬자."), [])

    def test_sound_alike_word_inside_a_sentence(self):
        self.assertEqual(word_fixes("알앤디로그 서버 확인해 줘", "RNDLOG 서버 확인해 줘"), [("알앤디로그", "RNDLOG")])


class FixesInField(unittest.TestCase):
    def test_fix_with_text_around_the_paste(self):
        before = "앞 문장입니다. " + P + "\n뒤 문장"
        after = "앞 문장입니다. " + P.replace("펀드키퍼", "FundKeeper") + "\n뒤 문장"
        self.assertEqual(fixes_in_field(P, before, after), [("펀드키퍼", "FundKeeper")])

    def test_field_sent_or_cleared_stops_watching(self):
        self.assertIsNone(fixes_in_field(P, P, ""))

    def test_text_before_the_paste_changed_stops_watching(self):
        self.assertIsNone(fixes_in_field(P, "가 " + P, "나 " + P))

    def test_paste_not_in_field(self):
        self.assertIsNone(fixes_in_field(P, "다른 글", "다른 글"))

    def test_unchanged_field_has_no_fixes(self):
        self.assertEqual(fixes_in_field(P, P, P), [])


if __name__ == "__main__":
    unittest.main()
