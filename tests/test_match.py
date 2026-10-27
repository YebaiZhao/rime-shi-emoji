import unittest
from shi_emoji.match import Matcher


class PhraseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.matcher = Matcher.load("data/phrases.json")

    def emojis(self, text):
        return [row["emoji"] for row in self.matcher.search(text)["candidates"]]

    def test_unseen_long_sentence(self):
        self.assertEqual(self.emojis("今天下班以后我想出去玩耍一下")[:3], ["🏖️", "🎮", "🥳"])

    def test_longest_phrase_wins(self):
        result = self.matcher.search("我想玩游戏放松一下")
        self.assertIn("玩游戏", [hit["phrase"] for hit in result["matches"]])
        self.assertIn("放松", [hit["phrase"] for hit in result["matches"]])
        self.assertEqual(result["candidates"][0]["emoji"], "🎮")

    def test_deduplicate_repeated_intents(self):
        emojis = self.emojis("出去玩玩耍玩一下")
        self.assertEqual(emojis[:3], ["🏖️", "🎮", "🥳"])
        self.assertEqual(len(emojis), len(set(emojis)))

    def test_unknown_returns_empty(self):
        self.assertEqual(self.emojis("嗯"), [])

    def test_short_terms_depend_on_complete_candidate_length(self):
        for text in ("病", "好", "好人", "你"):
            with self.subTest(isolated=text):
                self.assertEqual(self.emojis(text), [])
        self.assertEqual(self.emojis("冰"), ["🧊"])
        self.assertIn("🏖️", self.emojis("海边"))
        longer = self.emojis("你真是一个好人")
        self.assertIn("🫵", longer)
        self.assertIn("🦸", longer)
        self.assertNotIn("🦟", self.emojis("我今天生病了"))

    def test_reviewed_literal_mappings(self):
        for term, expected in [
            ("牛", ["🐄", "🐂", "🐮"]),
            ("虾", ["🦐"]),
            ("苹果", ["🍎", "🍏"]),
            ("蛋糕", ["🍰", "🎂"]),
            ("乌龟", ["🐢"]),
            ("橙子", ["🍊"]),
            ("月亮", ["🌙", "🌕"]),
        ]:
            with self.subTest(term=term):
                self.assertEqual(self.emojis(term), expected)
        self.assertNotIn("🔥", self.emojis("我去坐火车"))
        self.assertNotIn("🧠", self.emojis("我买了电脑"))

    def test_local_negation(self):
        result = self.matcher.search("我不想去海边")
        self.assertEqual(result["candidates"][0]["emoji"], "🏖️")
        self.assertTrue(result["candidates"][0]["negated"])

    def test_contrast_resets_negation(self):
        result = self.matcher.search("我不想去海边但是想玩游戏")
        self.assertEqual([row["emoji"] for row in result["candidates"][:2]], ["🎮", "🥳"])
        self.assertFalse(result["candidates"][0]["negated"])
        self.assertIn("🏖️", [row["emoji"] for row in result["candidates"]])

    def test_overlapping_phrases_are_not_lost(self):
        matcher = Matcher({"negators": [], "boundaries": [], "rules": [
            {"id": "out", "phrases": ["出去玩"], "emoji": ["🏖️"]},
            {"id": "play", "phrases": ["玩耍"], "emoji": ["🎮"]}]})
        self.assertEqual([row["emoji"] for row in matcher.search("出去玩耍")["candidates"]], ["🏖️", "🎮"])

    def test_intrinsic_negative_intent(self):
        self.assertEqual(self.emojis("我今天不想上班")[:1], ["🐟"])

    def test_traditional_variant(self):
        self.assertEqual(self.emojis("下班後想玩遊戲")[:1], ["🎮"])

    def test_unknown_paraphrase_remains_unknown(self):
        self.assertEqual(self.emojis("甲乙丙丁戊己庚辛"), [])

    def test_generated_aliases_expand_sentence_coverage(self):
        self.assertIn("🌊", self.emojis("我想去听海浪的声音"))
        self.assertIn("🎣", self.emojis("周末想去钓鱼"))

    def test_candidate_count(self):
        self.assertLessEqual(len(self.emojis("放假休息玩游戏谢谢恭喜加油")), 6)

    def test_combo_is_one_candidate(self):
        self.assertEqual(self.emojis("牛逼")[:3], ["🐂🍺", "🤯", "👏"])

    def test_common_short_phrases(self):
        for phrase, first in [("下班", "🏃💨"), ("累死了", "😵‍💫🪫"),
                              ("吃瓜", "🍉👀"), ("干饭", "🍚🥢"), ("无语", "😑")]:
            with self.subTest(phrase=phrase):
                self.assertEqual(self.emojis(phrase)[0], first)

    def test_expanded_daily_intents(self):
        for phrase, first in [("今天又要加班", "💻☕"), ("终于有灵感了", "💡"),
                              ("中午去吃火锅", "🍲"), ("准备出发旅行", "🧳"),
                              ("这个礼物好可爱", "🎁"), ("生日快乐", "🎂")]:
            with self.subTest(phrase=phrase):
                self.assertEqual(self.emojis(phrase)[0], first)

    def test_reviewed_meaning_and_ambiguous_prefixes(self):
        for phrase,first in [('牛逼','🐂🍺'),('厉害','👏'),('牛马','🐂🐎'),
                             ('开发','🧑‍💻'),('今天开发软件','🧑‍💻'),
                             ('中国','🇨🇳'),('澳大利亚','🇦🇺'),
                             ('见一面','🤝'),('约会','🥂'),
                             ('堵车','🚗🚦'),('写代码','🧑‍💻')]:
            with self.subTest(phrase=phrase):
                self.assertEqual(self.emojis(phrase)[0],first)
        for phrase in ('房地产开发','开发房地产','发展中国家'):
            with self.subTest(ordinary=phrase):
                self.assertEqual(self.emojis(phrase),[])
        for phrase,wrong in [('输送机','🚗✈️'),('雾里看花','🌸'),
                             ('投石问路','🧭'),('擅离职守','👋💼'),
                             ('满足要求','😊')]:
            with self.subTest(ordinary=phrase):
                self.assertNotIn(wrong,self.emojis(phrase))


if __name__ == "__main__":
    unittest.main()
