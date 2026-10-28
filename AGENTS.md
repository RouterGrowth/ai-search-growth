# Agent notes

This repository runs an AI search visibility program. Its agent skill is `skills/ai-search-growth/SKILL.md`: read it, and the reference file of the module it points to, before acting on a request about AI search, the prompt panel, the tracking reports, comparison pages, Reddit and X threads, press, listings or a Product Hunt launch.

- `config.json` and `prompts.json` at the root drive everything. While they still hold `<placeholders>`, run the skill's setup (module 0) first.
- The scheduled tracking is `runner/track.py` on GitHub Actions, with an API key. The skill works through the RouterGrowth MCP connector, signed in with OAuth: never ask the user for a key in chat.
- Nothing is posted, sent or submitted: the skill drafts, a person sends.
