# Changelog

All notable changes to this project are documented in this file.

## [1.1.0] - 2026-08-17

### Added

- Cursor Team Marketplace manifest at `.cursor-plugin/marketplace.json` so the repo can be imported via Dashboard → Plugins → Import from Repo.
- Plugin `displayName` and explicit agents/skills/rules/commands paths in `plugins/kb-genie/.cursor-plugin/plugin.json`.
- Plugin-scoped `plugins/kb-genie/README.md`.

### Changed

- Nested the Cursor plugin under `plugins/kb-genie/` to match the official plugin-template layout.
- Agent `tools` frontmatter is now a YAML list.
- Validator now requires and checks the marketplace manifest.
- README documents marketplace import and local copy testing; `npx kb-genie` is only the knowledge-base folder helper.
- CLI `init` copies the template; `install` remains as a deprecated alias.

## [1.0.2] - 2026-08-17

### Fixed

- CI `npm test` validation.

## [1.0.1] - 2026-08-17

### Fixed

- Added `package-lock.json` and CI publish workflow.

## [1.0.0] - 2026-08-17

### Added

- Initial KB Genie agents, skills, commands, rules, and knowledge-base template CLI.
