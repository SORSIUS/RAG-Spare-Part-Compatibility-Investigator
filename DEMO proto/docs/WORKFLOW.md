# Spare-Part Investigator v2 workflow

GET /api/project provides the initial comparison. POST /api/run accepts the original sample part and an optional bulletin flag. comparison.py compares required and actual values, applies minimum versus equality rules, and carries a source ID for each check. The browser renders candidate verdicts, clickable colored cells, and the original/candidate passages. Enabling the bulletin changes only its documented connector field; switching it off restores the unknown. No proposal or installation-approval endpoint is supported.

This is a local single-user concept demonstration with deterministic rules and fictional records. No live AI or external business action is connected.
