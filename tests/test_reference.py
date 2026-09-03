import unittest

from ai_recon.reference import ParseError, parse_owner_repo


class ParseOwnerRepoTests(unittest.TestCase):
    def test_bare_repo_url(self):
        self.assertEqual(parse_owner_repo("https://github.com/owner/repo"), ("owner", "repo"))

    def test_issue_url(self):
        self.assertEqual(
            parse_owner_repo("https://github.com/owner/repo/issues/42"), ("owner", "repo")
        )

    def test_pull_request_url(self):
        self.assertEqual(
            parse_owner_repo("https://github.com/owner/repo/pull/7"), ("owner", "repo")
        )

    def test_shorthand(self):
        self.assertEqual(parse_owner_repo("owner/repo"), ("owner", "repo"))

    def test_shorthand_with_issue_number(self):
        self.assertEqual(parse_owner_repo("owner/repo#42"), ("owner", "repo"))

    def test_strips_trailing_dot_git(self):
        self.assertEqual(parse_owner_repo("owner/repo.git"), ("owner", "repo"))
        self.assertEqual(
            parse_owner_repo("https://github.com/owner/repo.git"), ("owner", "repo")
        )

    def test_strips_surrounding_whitespace(self):
        self.assertEqual(parse_owner_repo("  owner/repo  "), ("owner", "repo"))

    def test_repo_names_with_dots_and_hyphens(self):
        self.assertEqual(parse_owner_repo("owner/my-repo.js"), ("owner", "my-repo.js"))

    def test_rejects_a_non_github_url(self):
        with self.assertRaises(ParseError):
            parse_owner_repo("https://gitlab.com/owner/repo")

    def test_rejects_empty_string(self):
        with self.assertRaises(ParseError):
            parse_owner_repo("")

    def test_rejects_a_bare_word(self):
        with self.assertRaises(ParseError):
            parse_owner_repo("notarepo")


if __name__ == "__main__":
    unittest.main()
