import unittest
from unittest.mock import patch

from ai_recon import cli, github
from ai_recon.patterns import Verdict


class CheckTests(unittest.TestCase):
    @patch("ai_recon.github.fetch_policy_files")
    def test_banned_repo(self, mock_fetch):
        mock_fetch.return_value = [
            github.FetchedFile("AI_POLICY.md", "AI-generated contributions are not allowed.")
        ]

        result, files = cli.check("owner/repo", token="tok")

        self.assertEqual(result.verdict, Verdict.BANNED)
        self.assertEqual(len(files), 1)
        mock_fetch.assert_called_once_with("owner", "repo", "tok")

    @patch("ai_recon.github.fetch_policy_files")
    def test_no_files_found_at_all(self, mock_fetch):
        mock_fetch.return_value = []

        result, files = cli.check("owner/repo", token="tok")

        self.assertEqual(result.verdict, Verdict.NOT_FOUND)
        self.assertEqual(files, [])

    @patch("ai_recon.github.fetch_policy_files")
    def test_files_present_but_no_policy_language(self, mock_fetch):
        mock_fetch.return_value = [github.FetchedFile("README.md", "Just a normal readme.")]

        result, files = cli.check("owner/repo", token="tok")

        self.assertEqual(result.verdict, Verdict.NOT_FOUND)
        self.assertEqual(len(files), 1)  # the file existed, it just said nothing about AI

    @patch("ai_recon.github.fetch_policy_files")
    def test_invalid_reference_raises_before_any_network_call(self, mock_fetch):
        with self.assertRaises(cli.ReconError):
            cli.check("not a valid reference", token="tok")
        mock_fetch.assert_not_called()

    @patch("ai_recon.github.fetch_policy_files")
    def test_missing_repo_raises_a_recon_error(self, mock_fetch):
        mock_fetch.side_effect = github.RepoNotFoundError("owner/repo does not exist")

        with self.assertRaises(cli.ReconError):
            cli.check("owner/repo", token="tok")

    @patch("ai_recon.github.fetch_policy_files")
    def test_works_with_no_token(self, mock_fetch):
        mock_fetch.return_value = []

        cli.check("owner/repo", token=None)

        mock_fetch.assert_called_once_with("owner", "repo", None)


class FormatResultTests(unittest.TestCase):
    def test_confident_verdict_has_no_double_check_warning(self):
        from ai_recon.patterns import Evidence, PolicyResult

        result = PolicyResult(Verdict.BANNED, [Evidence("AI_POLICY.md", "not allowed")])
        text = cli._format_result(result, [github.FetchedFile("AI_POLICY.md", "...")])

        self.assertNotIn("not a confident verdict", text)
        self.assertIn("BANNED", text)

    def test_unclear_verdict_includes_the_double_check_warning(self):
        from ai_recon.patterns import Evidence, PolicyResult

        result = PolicyResult(Verdict.MENTIONED_UNCLEAR, [Evidence("README.md", "we use AI internally")])
        text = cli._format_result(result, [github.FetchedFile("README.md", "...")])

        self.assertIn("not a confident verdict", text)

    def test_not_found_includes_the_caveat_about_unwatched_locations(self):
        from ai_recon.patterns import PolicyResult

        result = PolicyResult(Verdict.NOT_FOUND, [])
        text = cli._format_result(result, [])

        self.assertIn("wiki", text)
        self.assertIn("none of the checked files exist", text)


class MainTests(unittest.TestCase):
    @patch("ai_recon.github.fetch_policy_files")
    def test_prints_result_and_exits_0(self, mock_fetch):
        mock_fetch.return_value = [
            github.FetchedFile("AI_POLICY.md", "AI-generated contributions are not allowed.")
        ]

        with patch("sys.stdout") as mock_stdout:
            exit_code = cli.main(["owner/repo"])

        self.assertEqual(exit_code, 0)
        self.assertTrue(mock_stdout.write.called)

    def test_bad_reference_exits_1(self):
        with patch("sys.stderr"):
            exit_code = cli.main(["not a valid reference at all"])
        self.assertEqual(exit_code, 1)

    @patch("ai_recon.github.fetch_policy_files")
    def test_repo_not_found_exits_1(self, mock_fetch):
        mock_fetch.side_effect = github.RepoNotFoundError("owner/repo does not exist")

        with patch("sys.stderr"):
            exit_code = cli.main(["owner/repo"])

        self.assertEqual(exit_code, 1)

    @patch.dict("os.environ", {}, clear=True)
    @patch("ai_recon.github.fetch_policy_files")
    def test_runs_without_github_token_set(self, mock_fetch):
        mock_fetch.return_value = []

        with patch("sys.stdout"):
            exit_code = cli.main(["owner/repo"])

        self.assertEqual(exit_code, 0)
        mock_fetch.assert_called_once_with("owner", "repo", None)


if __name__ == "__main__":
    unittest.main()
