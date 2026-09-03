# ai-recon

Check a repo's AI-contribution policy before you invest time in it.

```
$ ai-recon aonyx-ai/whisker-aonyx-rules
AI-assisted contributions appear ALLOWED, WITH DISCLOSURE REQUIRED.
checked (found): CLAUDE.md, README.md
  CLAUDE.md: "In particular, LLM-assisted contributions must aim for a
  higher standard of excellence than with humans alone, and you should
  spend at least 3x the amount of time reviewing code as you did writing
  it."
```

## Why this exists

More and more repos are writing down a policy on AI-assisted contributions
— some ban them outright, some require disclosure, some welcome them freely
— but there's no standard place that policy lives. It might be a dedicated
`AI_POLICY.md`, the emerging `AGENTS.md` convention, a `CLAUDE.md` written
for coding agents specifically, a section buried in `CONTRIBUTING.md`, or
just a paragraph in the README. Finding out means reading through a repo by
hand before you know whether your time there is welcome at all.

`ai-recon` checks the places these policies actually tend to live and gives
you a straight answer, so you find out before you fork, not after you've
already opened a PR.

## Install

```bash
pip install ai-recon
```

Requires Python 3.10+.

## Use

```bash
ai-recon <reference>
```

`<reference>` can be a GitHub URL (repo, issue, or PR — only the repo part
matters) or `owner/repo` shorthand.

```bash
ai-recon https://github.com/owner/repo/issues/123
ai-recon owner/repo
```

Works without a token for public repos. Set `GITHUB_TOKEN` if you're
hitting rate limits or need to check a private repo you have access to.

## What it checks

In order, every one that exists (not just the first match — a repo can and
sometimes does say different things in different places):

- `AI_POLICY.md` / `.github/AI_POLICY.md`
- `AGENTS.md` / `.github/AGENTS.md`
- `CLAUDE.md`
- `CONTRIBUTING.md` / `.github/CONTRIBUTING.md` / `docs/CONTRIBUTING.md`
- `README.md`

## What the verdicts mean

- **BANNED** — found language like "not allowed," "prohibited," or a
  clearly negated permission ("no AI-generated code is permitted").
- **DISCLOSURE_REQUIRED** — found language asking for disclosure,
  attribution, or extra review scrutiny (`must disclose`, `Assisted-by`
  trailers, "higher standard of review," etc.).
- **ALLOWED** — found explicit welcoming language with no disclosure
  requirement attached.
- **MENTIONED_UNCLEAR** — AI is mentioned somewhere in a checked file, but
  not in language this tool recognizes as a clear verdict (e.g. a policy
  that's only linked to externally, not stated inline). Read the source
  yourself.
- **NOT_FOUND** — none of the checked files mention AI at all. This does
  *not* mean no policy exists — it might be in a wiki page, an external
  doc, or a location this tool doesn't check yet.

When multiple files disagree, BANNED always wins over anything else found
anywhere else, on purpose: the cost of missing a ban is a rejected PR and
wasted effort on both sides; the cost of over-cautiously flagging one is an
extra thirty seconds double-checking. See `patterns.py` for the reasoning
in full.

## What it deliberately is not

This is a heuristic over prose that humans wrote for other humans, not a
parser for a real specification — no machine-readable standard for AI
contribution policies exists yet. Every verdict except a very confident
BANNED/DISCLOSURE_REQUIRED/ALLOWED match is a starting point for your own
judgment, not a replacement for it. Treat `ai-recon` the way you'd treat a
linter: fast, useful, and not infallible.

## Why zero dependencies

Like [beachhead](https://github.com/tusharnagar2002/beachhead), this
imports only the Python standard library. No dependency tree means nothing
here has a supply-chain surface beyond Python itself.

## Contributing

The test suite mirrors beachhead's approach: pure classification logic
(`patterns.py`) is tested directly with representative policy phrasing
(paraphrased from real projects' actual language, not copied verbatim);
`github.py` is tested by mocking the one function that opens a socket. Two
real bugs were caught this way during development — a negated-permission
false positive ("no AI-generated code is permitted" reading as *allowed*)
and a directory-vs-file type error — both now have regression tests.

```bash
git clone https://github.com/tusharnagar2002/ai-recon.git
cd ai-recon
python -m venv .venv && source .venv/bin/activate
pip install -e .
python -m unittest discover -s tests -v
```

## License

MIT
