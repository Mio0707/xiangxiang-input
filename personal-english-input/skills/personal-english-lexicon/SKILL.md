---
name: personal-english-lexicon
description: Process Chinese sentences recorded by the local Rime sentence recorder into bilingual sentence and personal vocabulary reports. Use when the user asks to update, inspect, or publish their personal English lexicon; do not use for continuous input recording.
---

# Personal English Lexicon

Use the bundled `scripts/lexicon_store.py` for storage, deduplication, validation, reporting, and publishing. Keep raw sentences local.

## Update workflow

1. Run `ingest`, then `pending`. If there are no pending sentences, report that succinctly and stop. Use `ignore` for sensitive or meaningless records.
2. Before translating, correct only obvious input-method typos, homophone substitutions, and accidental missing or repeated characters when the intended sentence is unambiguous. Preserve the user's meaning, wording, tone, and punctuation; do not polish or rewrite. If a correction is uncertain, keep the original text.
3. Translate the corrected Chinese into natural, conversational English by default. Prefer everyday phrasing and contractions where appropriate; avoid stiff word-for-word translation, but do not add slang or change the meaning. Keep both the original and corrected Chinese in the result so the user can audit every correction.
4. Extract only useful contextual words or phrases from the corrected Chinese. Do not mechanically split phrases: create a component entry only when it appears independently in the source evidence.
5. Return one preferred English equivalent and at most one materially different alternative. Classify each item as `word` or `phrase`, and as `A1`, `A2`, `B1`, `B2`, `C1`, `C2`, or `specialized`.
6. Mark A1/A2 items `keep: false`. Keep B1+ and domain-specific expressions. Never force an alignment when Chinese and English do not correspond cleanly.
7. Write the strict JSON result described in [references/result-schema.md](references/result-schema.md), run `apply-results`, then `report`.
8. Show the two reports to the user. Do not run `publish` until the user explicitly approves updating the live Rime dictionary.

`publish` writes only the kept personal entries to
`~/Library/Rime/personal_translate.tsv`. The live `personal_translate` filter
has no ECDICT, helper, cloud, or other fallback; unmatched candidates remain
unannotated.

Default to all pending sentences. If the user requests a smaller range, limit the pending batch accordingly. Do not impose a calendar schedule.

## Privacy and quality

- Do not send raw sentences to an additional service or install an AI provider unless the user explicitly asks.
- Do not include passwords, tokens, URLs, email addresses, or obviously private identifiers in reports. Mark such records ignored instead.
- Prefer no vocabulary entry over a weak or invented alignment.
- The live candidate annotation must contain no more than two English equivalents.

## Commands

Resolve the skill folder, then run its bundled script:

```bash
python3 scripts/lexicon_store.py ingest
python3 scripts/lexicon_store.py pending --limit 100
python3 scripts/lexicon_store.py ignore 12 18
python3 scripts/lexicon_store.py apply-results /path/to/results.json
python3 scripts/lexicon_store.py report
```

After explicit approval only:

```bash
python3 scripts/lexicon_store.py publish
```
