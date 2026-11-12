# Issue tracker: GitHub

Issues and specs live in GitHub Issues for
`tlsenjoyer/syntrillium-course`. Use the `gh` CLI from this repo.

## Conventions

- Before creating the first issue in a session, verify the target with
  `gh repo view --json nameWithOwner`.
- Create issues with `gh issue create --title "..." --body-file <path>`.
  Use a file for multiline bodies.
- Read issues with
  `gh issue view <number> --json number,title,body,labels,comments`.
- List issues with `gh issue list`, filtering by state and label.
- Comment with `gh issue comment <number> --body-file <path>`.
- Apply or remove labels with `gh issue edit <number> --add-label "..."`
  or `--remove-label "..."`.
- To close an issue, post the explanation first, then run
  `gh issue close <number>`.
- Use native GitHub sub-issues and issue dependencies when available.
  Otherwise, put `Part of #<parent>` and `Blocked by: #<number>` at the
  top of child issue bodies. Work is unblocked when every blocker is closed.

## Pull requests as a triage surface

**PRs as a request surface: no.**

## Skill operations

“Publish to the issue tracker” means create a GitHub issue.
“Fetch the relevant ticket” means read the GitHub issue.

For wayfinding, use one map issue labelled `wayfinder:map`, with child
issues labelled `wayfinder:<type>` (research, prototype, grilling, task).
Choose the first open child in map order with no open blockers or assignee.
Claim it by assigning yourself. Resolve it by commenting with the answer,
closing it, and adding a context pointer to the map's Decisions-so-far.
