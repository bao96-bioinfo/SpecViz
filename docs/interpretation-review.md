# Reviewing interpretation quality

The helper validates references and content accounting. An agent must still
interpret meaning correctly. Use `tests/fixtures/interpretation/spec.md` as a
source-backed evaluation request: ask a fresh agent to produce concise and
detailed text views using the installed skill. Do not supply an expected diagram.

Check the resulting views against these obligations:

| Source meaning | Review question |
| --- | --- |
| Never export another person's data | Does the explanation retain the prohibition and supplied-identifier exception? |
| 30 seconds; encrypted exports up to 90 seconds | Are both quantities, their units, and the exception visible? |
| Reject over 10 megabytes before creation | Are threshold and ordering retained? |
| Protection optional; chosen passwords at least 12 characters | Are optional choice and conditional minimum distinct? |
| Invalid input creates no partial download | Are the failure outcome and negative condition retained? |
| Role-based access control | Is the unfamiliar abbreviation expanded in explanatory text? |
| Undecided one-day expiry | Is it a question rather than an implemented or mandatory rule? |

Detailed views must account for every source block or show it as unresolved.
Concise views can collapse rules into a named group, with detailed mode exposing
the individual obligations. Check that expanding does not change node order or
relationships. Test judgments of behavioral equivalence separately from syntax
and formatting tests. Record actual host, version, source versions, and observed
limitations in `docs/acceptance.md`; do not treat golden text as model evaluation.
