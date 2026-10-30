This repository is a lightweight orchestration Skill, not an application or model runtime.

- Preserve the seven-source sequence and the default six-round cap unless the user asks to change them.
- Keep upstream attribution. Do not describe third-party skills or engines as original work here.
- Keep SKILL.md self-contained with its local references and dependency manifest.
- Never commit .upstream/, sources.local.json, user projects, private materials, credentials or run screenshots.
- Validate script changes with `python -m unittest discover -s tests -v`.
- Tests of dependency preparation do not prove UI quality or that an Agent executed the loop.
