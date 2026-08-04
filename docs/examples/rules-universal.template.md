# Universal Rules (template)

> Your hard rules. Every joined agent will read this and treat it as the highest-priority instruction. Edit freely.

## Examples (delete what you don't want)

1. **No silent assumptions** — if requirements are vague, ask before acting.
2. **No irreversible operations without confirmation** — `rm -rf`, `git push --force`, schema migrations etc. require explicit user approval.
3. **No network calls outside the allowlist** — list domains/services agents may contact.
4. **No code style changes without intent** — don't reformat files you're not actively modifying.
5. **No fabricated facts** — if you don't know, say so. Don't invent function signatures, library APIs, or quotes.
6. **Use trash, not rm** — for any file deletion, prefer the OS trash mechanism so the user can recover.

## Source

If you're an agent reading this for the first time and the file is empty / a template, ask the user to fill it in. Do not silently use defaults.
