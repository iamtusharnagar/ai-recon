import unittest

from ai_recon.patterns import Evidence, PolicyResult, Verdict, classify_file, combine


class ClassifyFileBannedTests(unittest.TestCase):
    def test_explicit_ban_phrase(self):
        result = classify_file("AI_POLICY.md", "AI-generated contributions are not allowed here.")
        self.assertEqual(result.verdict, Verdict.BANNED)
        self.assertEqual(result.evidence[0].path, "AI_POLICY.md")

    def test_shall_not_phrasing(self):
        text = "Contributions shall not include content derived from an AI or LLM."
        self.assertEqual(classify_file("x.md", text).verdict, Verdict.BANNED)

    def test_bullet_point_without_terminal_punctuation(self):
        text = "Rules:\n- No AI-generated code is permitted\n- Keep commits small"
        result = classify_file("x.md", text)
        self.assertEqual(result.verdict, Verdict.BANNED)

    def test_bare_prohibited_near_ai(self):
        text = "Use of ChatGPT or similar tools is prohibited for this project."
        self.assertEqual(classify_file("x.md", text).verdict, Verdict.BANNED)

    def test_ban_wins_even_if_a_disclosure_sentence_appears_first(self):
        text = (
            "If you use an AI tool, please disclose it in your PR. "
            "That said, AI-assisted contributions are not accepted at this time."
        )
        result = classify_file("x.md", text)
        self.assertEqual(result.verdict, Verdict.BANNED)


class ClassifyFileDisclosureTests(unittest.TestCase):
    def test_must_disclose_phrasing(self):
        text = "Contributors must disclose any use of AI tools in the PR description."
        self.assertEqual(classify_file("x.md", text).verdict, Verdict.DISCLOSURE_REQUIRED)

    def test_assisted_by_trailer_convention(self):
        text = "Use an Assisted-by trailer in your commit message if you used an LLM."
        self.assertEqual(classify_file("x.md", text).verdict, Verdict.DISCLOSURE_REQUIRED)

    def test_higher_review_standard_language(self):
        text = "LLM-assisted contributions must aim for a higher standard of review than humans alone."
        self.assertEqual(classify_file("x.md", text).verdict, Verdict.DISCLOSURE_REQUIRED)

    def test_disclosure_bullet_separated_from_its_intro_line_by_a_colon(self):
        # Regression test: real CONTRIBUTING.md files commonly write "...
        # must:" on one line and list the actual requirements as bullets
        # below it, which the line-based splitter turns into separate
        # fragments -- so "must disclose" as one contiguous phrase never
        # appears anywhere, even though the policy clearly requires it.
        text = (
            "AI-assisted contributions are allowed. The submitter must:\n"
            "- Disclose meaningful use of AI agents in the PR description\n"
            "- Review every generated change"
        )
        self.assertEqual(classify_file("x.md", text).verdict, Verdict.DISCLOSURE_REQUIRED)

    def test_your_code_is_your_responsibility_language(self):
        text = "AI tools are fine to use, but remember: your code is your responsibility."
        self.assertEqual(classify_file("x.md", text).verdict, Verdict.DISCLOSURE_REQUIRED)


class ClassifyFileAllowedTests(unittest.TestCase):
    def test_explicit_welcome_with_no_disclosure_language(self):
        text = "AI-assisted contributions are welcome on this project."
        self.assertEqual(classify_file("x.md", text).verdict, Verdict.ALLOWED)

    def test_are_permitted_phrasing(self):
        text = "The use of Copilot and similar tools is permitted for all contributors."
        self.assertEqual(classify_file("x.md", text).verdict, Verdict.ALLOWED)


class ClassifyFileUnclearAndNotFoundTests(unittest.TestCase):
    def test_ai_mentioned_with_no_recognized_verdict_language(self):
        text = "This project uses AI internally for issue triage."
        result = classify_file("x.md", text)
        self.assertEqual(result.verdict, Verdict.MENTIONED_UNCLEAR)
        self.assertIn("AI", result.evidence[0].sentence)

    def test_no_ai_mention_at_all(self):
        text = "This project welcomes all contributions. Please run the tests before submitting."
        result = classify_file("x.md", text)
        self.assertEqual(result.verdict, Verdict.NOT_FOUND)
        self.assertEqual(result.evidence, [])

    def test_empty_file(self):
        result = classify_file("x.md", "")
        self.assertEqual(result.verdict, Verdict.NOT_FOUND)

    def test_a_sentence_about_something_else_does_not_false_positive_on_ai_as_a_name(self):
        # "Claude" the contributor's name, not the tool -- known limitation
        # documented in the README, but the mundane "no verdict language
        # nearby" case should still land as MENTIONED_UNCLEAR rather than
        # BANNED just because "not" appears somewhere unrelated in the file.
        text = "Claude opened issue #12 last week. We are not able to reproduce it yet."
        result = classify_file("x.md", text)
        self.assertEqual(result.verdict, Verdict.MENTIONED_UNCLEAR)


class CombineTests(unittest.TestCase):
    def test_banned_beats_allowed_across_files(self):
        results = [
            PolicyResult(Verdict.ALLOWED, [Evidence("README.md", "AI use is welcome.")]),
            PolicyResult(Verdict.BANNED, [Evidence("AI_POLICY.md", "AI contributions are not allowed.")]),
        ]
        combined = combine(results)
        self.assertEqual(combined.verdict, Verdict.BANNED)
        self.assertEqual(combined.evidence[0].path, "AI_POLICY.md")

    def test_disclosure_beats_allowed(self):
        results = [
            PolicyResult(Verdict.ALLOWED, [Evidence("README.md", "AI use is welcome.")]),
            PolicyResult(
                Verdict.DISCLOSURE_REQUIRED,
                [Evidence("CONTRIBUTING.md", "You must disclose AI use.")],
            ),
        ]
        self.assertEqual(combine(results).verdict, Verdict.DISCLOSURE_REQUIRED)

    def test_unclear_only_wins_when_nothing_stronger_exists(self):
        results = [
            PolicyResult(Verdict.MENTIONED_UNCLEAR, [Evidence("README.md", "We use AI for triage.")]),
            PolicyResult(Verdict.NOT_FOUND, []),
        ]
        self.assertEqual(combine(results).verdict, Verdict.MENTIONED_UNCLEAR)

    def test_all_not_found_combines_to_not_found(self):
        results = [PolicyResult(Verdict.NOT_FOUND, []), PolicyResult(Verdict.NOT_FOUND, [])]
        combined = combine(results)
        self.assertEqual(combined.verdict, Verdict.NOT_FOUND)
        self.assertEqual(combined.evidence, [])

    def test_empty_results_list_combines_to_not_found(self):
        self.assertEqual(combine([]).verdict, Verdict.NOT_FOUND)

    def test_confident_property(self):
        self.assertTrue(PolicyResult(Verdict.BANNED, []).confident)
        self.assertTrue(PolicyResult(Verdict.DISCLOSURE_REQUIRED, []).confident)
        self.assertTrue(PolicyResult(Verdict.ALLOWED, []).confident)
        self.assertFalse(PolicyResult(Verdict.MENTIONED_UNCLEAR, []).confident)
        self.assertFalse(PolicyResult(Verdict.NOT_FOUND, []).confident)


if __name__ == "__main__":
    unittest.main()
