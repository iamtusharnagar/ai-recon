import base64
import unittest
from unittest.mock import patch

from ai_recon import github


def _b64(text: str) -> str:
    return base64.b64encode(text.encode("utf-8")).decode("ascii")


class RepoExistsTests(unittest.TestCase):
    @patch("ai_recon.github._request")
    def test_200_means_exists(self, mock_request):
        mock_request.return_value = (200, {"full_name": "owner/repo"})
        self.assertTrue(github.repo_exists("owner", "repo", "tok"))

    @patch("ai_recon.github._request")
    def test_404_means_does_not_exist(self, mock_request):
        mock_request.return_value = (404, {"message": "Not Found"})
        self.assertFalse(github.repo_exists("owner", "repo", "tok"))

    @patch("ai_recon.github._request")
    def test_other_status_raises(self, mock_request):
        mock_request.return_value = (403, {"message": "rate limited"})
        with self.assertRaises(github.GitHubError):
            github.repo_exists("owner", "repo", "tok")

    @patch("ai_recon.github._request")
    def test_only_calls_the_api_once(self, mock_request):
        mock_request.return_value = (403, {"message": "rate limited"})
        with self.assertRaises(github.GitHubError):
            github.repo_exists("owner", "repo", "tok")
        self.assertEqual(mock_request.call_count, 1)


class FetchPolicyFilesTests(unittest.TestCase):
    @patch("ai_recon.github._request")
    def test_raises_repo_not_found_before_fetching_anything(self, mock_request):
        mock_request.return_value = (404, {"message": "Not Found"})
        with self.assertRaises(github.RepoNotFoundError):
            github.fetch_policy_files("owner", "repo", "tok")
        # Just the one repo-existence check, no attempt to fetch any file.
        self.assertEqual(mock_request.call_count, 1)

    @patch("ai_recon.github._request")
    def test_fetches_every_existing_candidate_not_just_the_first(self, mock_request):
        def side_effect(path, token):
            if path == "/repos/owner/repo":
                return 200, {"full_name": "owner/repo"}
            if path == "/repos/owner/repo/contents/AI_POLICY.md":
                return 200, {"encoding": "base64", "content": _b64("no AI allowed")}
            if path == "/repos/owner/repo/contents/README.md":
                return 200, {"encoding": "base64", "content": _b64("hello")}
            return 404, {"message": "Not Found"}

        mock_request.side_effect = side_effect

        results = github.fetch_policy_files(
            "owner", "repo", "tok", paths=["AI_POLICY.md", "CONTRIBUTING.md", "README.md"]
        )

        self.assertEqual([r.path for r in results], ["AI_POLICY.md", "README.md"])
        self.assertEqual(results[0].text, "no AI allowed")

    @patch("ai_recon.github._request")
    def test_skips_a_path_that_is_a_directory_not_a_file(self, mock_request):
        def side_effect(path, token):
            if path == "/repos/owner/repo":
                return 200, {"full_name": "owner/repo"}
            if path == "/repos/owner/repo/contents/AI_POLICY.md":
                # A directory listing has no "encoding" key.
                return 200, [{"name": "a"}, {"name": "b"}]
            return 404, {"message": "Not Found"}

        mock_request.side_effect = side_effect

        results = github.fetch_policy_files("owner", "repo", "tok", paths=["AI_POLICY.md"])

        self.assertEqual(results, [])

    @patch("ai_recon.github._request")
    def test_a_non_404_file_error_propagates(self, mock_request):
        def side_effect(path, token):
            if path == "/repos/owner/repo":
                return 200, {"full_name": "owner/repo"}
            return 403, {"message": "rate limited"}

        mock_request.side_effect = side_effect

        with self.assertRaises(github.GitHubError):
            github.fetch_policy_files("owner", "repo", "tok", paths=["AI_POLICY.md"])

    @patch("ai_recon.github._request")
    def test_works_without_a_token_for_public_repos(self, mock_request):
        def side_effect(path, token):
            self.assertIsNone(token)
            if path == "/repos/owner/repo":
                return 200, {"full_name": "owner/repo"}
            return 404, {"message": "Not Found"}

        mock_request.side_effect = side_effect

        results = github.fetch_policy_files("owner", "repo", token=None, paths=["AI_POLICY.md"])
        self.assertEqual(results, [])

    def test_default_candidate_paths_cover_known_conventions(self):
        # Regression guard: these are the specific real-world conventions
        # the README documents checking. If one gets refactored out by
        # accident, this test -- not just manual inspection -- catches it.
        for expected in ("AI_POLICY.md", "AGENTS.md", "CLAUDE.md", "CONTRIBUTING.md", "README.md"):
            self.assertIn(expected, github.CANDIDATE_PATHS)


if __name__ == "__main__":
    unittest.main()
