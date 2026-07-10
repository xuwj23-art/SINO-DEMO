# Query Redaction Prompt

Rewrite the user query for safe external web search.

Rules:

1. Remove customer names, account numbers, identification numbers, phone numbers, email addresses, addresses, transaction details, and internal document names.
2. Remove confidential company project names, CO investigation details, KYC details, MNPI, and non-public regulatory response drafts.
3. Preserve only the generic public-information need.
4. If the query cannot be made safe without losing its purpose, return `BLOCK_WEB_SEARCH`.

Output only the rewritten query or `BLOCK_WEB_SEARCH`.

Examples:

Input:
`For client Chan Tai Man account 123456, check current SFC requirement for suspicious transaction reporting.`

Output:
`Hong Kong SFC suspicious transaction reporting requirements`

Input:
`Search whether our internal CO memo about Project Alpha conflicts with the regulator response draft.`

Output:
`BLOCK_WEB_SEARCH`
