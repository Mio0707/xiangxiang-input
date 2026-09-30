# Analysis result schema

The result file is a UTF-8 JSON array. Each object corresponds to one pending sentence:

```json
[
  {
    "id": 1,
    "zh": "我们需要确认项目近度",
    "corrected_zh": "我们需要确认项目进度",
    "en": "We need to check the project progress.",
    "items": [
      {
        "zh": "项目进度",
        "en": ["project progress"],
        "type": "phrase",
        "level": "B1",
        "keep": true
      }
    ]
  }
]
```

Constraints:

- `id` must match a pending record.
- `zh` is the unchanged recorded sentence and must match the pending record.
- `corrected_zh` is the Chinese sentence used for translation. Correct only unambiguous typos; otherwise copy `zh` unchanged.
- `en` is a natural, conversational translation of `corrected_zh`, not a stiff word-for-word rendering.
- Every item `zh` must be an exact substring of `corrected_zh`.
- `en` contains one or two concise equivalents.
- `type` is `word` or `phrase`.
- `level` is `A1`, `A2`, `B1`, `B2`, `C1`, `C2`, or `specialized`.
- `keep` is `false` for elementary vocabulary and uncertain alignments.
