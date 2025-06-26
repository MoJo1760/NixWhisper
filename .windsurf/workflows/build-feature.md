---
description: Workflow for building a feature
---

- Reference PRD.md and TODO.md to check features
- evaluate existing code base to see where the new feature will properly fit, minimizing complexity and dead code
- create code for the feature given in the command, only one feature at a time
- create tests for the feature
- run unit tests for the feature
- fix any tests that are failing and then test again
- when unit tests are passing, run full test suite and fix broken
- when full test suite is passing, commit code to git
- after code is commited, check off the item in the TODO.md to mark it complete