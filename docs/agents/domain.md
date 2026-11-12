# Domain docs

## Before exploring

Read the root `GLOSSARY.md` and any ADRs in `docs/adr/` relevant to
the work.

If these files are absent, proceed silently. Domain modeling creates
them lazily when terminology or decisions are resolved.

## Layout

This repo uses a single-context layout:

- `GLOSSARY.md`: shared domain vocabulary.
- `docs/adr/`: architectural decision records.

## Vocabulary and decisions

Use the glossary's terms in issue titles, proposals, hypotheses,
and tests. Reconsider unfamiliar terms; note real vocabulary gaps
for domain modeling.

When a proposal contradicts an existing ADR, identify that ADR
and explain why the decision should be reopened.
