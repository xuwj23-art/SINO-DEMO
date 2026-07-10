# RAG Evaluation

## Purpose

The eval suite proves whether the system is more accurate, more controllable,
and more auditable than manual use of a generic chatbot or Gem-style prompt.

## Metrics

Evaluate retrieval and generation separately. Retrieval failures should be fixed
before prompt or model tuning.

| Metric | Meaning |
|---|---|
| Recall@k | whether the relevant source chunks appear in the top k retrieved chunks |
| MRR | how early the first relevant chunk appears in retrieval results |
| Unauthorized retrieval blocking | unauthorized documents never appear in retrieved context |
| Chunking strategy comparison | compares chunk sizes, overlap, and section-aware chunking by retrieval quality |
| Answer accuracy | answer matches the expected conclusion |
| Citation precision | cited source actually supports the answer |
| Citation coverage | material claims have citations |
| Hallucination rate | answer includes unsupported claims |
| Correct refusal rate | assistant refuses when evidence is insufficient |
| Permission safety | assistant does not use unauthorized documents |
| Latency | time to final answer |
| Cost | token and infrastructure cost per query |

## Dataset Shape

Each eval case should contain:

```json
{
  "id": "case-001",
  "question": "What approval is required for X?",
  "allowed_document_ids": ["policy-001"],
  "blocked_document_ids": [],
  "expected_relevant_chunks": [
    {
      "document_id": "policy-001",
      "section": "3.2",
      "page": 4
    }
  ],
  "expected_answer": "Approval from ... is required.",
  "expected_citations": [
    {
      "document_id": "policy-001",
      "section": "3.2"
    }
  ],
  "should_refuse": false,
  "requires_human_review": false,
  "source_extraction_method": "native_text",
  "risk_level": "internal"
}
```

For OCR or mixed-source cases, set `source_extraction_method` to `ocr` or
`mixed` and assert that the answer visibly marks the citation as OCR/mixed and
requiring human caution unless the source is certified.

## First Eval Categories

- direct answer exists in one source
- answer requires two source sections
- insufficient evidence
- conflicting document versions
- unauthorized document access
- prompt injection in source document
- question asks for external legal interpretation
- question contains sensitive information and requests web search
- OCR/mixed source must be marked as lower-confidence unless certified
- SearchGateway is disabled by default and does not send internal context externally

## Retrieval Evaluation

Build an initial dataset from 10-20 public or explicitly redacted PDF documents.
Each question must map to the exact document, section, page, or chunk that
supports the expected answer.

Minimum retrieval checks:

- `Recall@5` for first-pass retrieval on simple and multi-section policy questions.
- `MRR` for single-fact lookup questions.
- unauthorized documents never appear in retrieved chunks or generated context.
- topically similar but irrelevant chunks do not lead to unsupported answers.
- chunking strategy is compared before changing embedding models or prompts.

Recommended chunking comparison:

| Strategy | What To Compare |
|---|---|
| fixed-size chunks | 256, 512, and 800 token chunks with overlap |
| section-aware chunks | preserve policy section headings and page references |
| contextual chunks | prepend document title and section path before embedding |

Prefer the strategy that improves retrieval recall while preserving precise page
and section citations.

## Generation Evaluation

After retrieval passes basic quality checks, evaluate the final answer:

- faithfulness to retrieved context
- answer relevance to the user question
- citation precision and coverage
- correct refusal when evidence is insufficient
- human-review marking for high-risk compliance, customer-data, MNPI, KYC, CO
  investigation, OCR/mixed, or external legal interpretation cases

## Post-MVP PDF Assistant Evaluation

PDF editing, redaction, and external-share export are not part of the two-week
MVP, but future PDF Assistant work must be evaluated before pilot or production
use.

Minimum checks:

- original PDF cannot be overwritten by edit operations
- edits create draft or new document versions
- redaction removes underlying text/images and is not only visual masking
- redacted content cannot be retrieved, copied, searched, or indexed from the
  exported version
- high-risk documents require human approval before redaction/export/publish
- annotations, highlights, watermarks, and page operations preserve audit events
- new searchable versions trigger extraction/chunking/embedding refresh where
  source text or page structure changes
- external-share exports preserve source version, approver, timestamp, and hash

## Directory Layout

```text
evals/
  datasets/
    sample-cases.jsonl
  reports/
    README.md
```

## POC Acceptance Criteria

- initial eval dataset uses only public, synthetic, or explicitly redacted PDFs
- Recall@5 is tracked for retrieval and reviewed before prompt tuning
- 90%+ citation precision on simple policy questions
- no answer from unauthorized documents
- no unsupported answer when evidence is missing
- OCR/mixed citations are visibly marked unless certified by human review
- SearchGateway remains disabled by default and never sends internal context
- prompt injection test does not override system rules
- all high-risk outputs are marked for human review
