# Safety Guardrails (template)

> Hard limits on dangerous operations. Agents do not bypass these even when the user pressures them.

## Personal-file operations (high risk)

For any deletion / rename / move on personal directories (Desktop, Downloads, Documents, Home):

- **No-Go Zones**: `/`, `/System`, `~`, `~/Library`, `~/.config`, `~/AppData` — never recursively delete
- **Never** use `rm -rf`, `del /S /Q`, etc. on personal dirs
- **Scan = read-only**: when user says "scan/find/identify", only generate a report, **don't move files**
- **Vague request = ask first**: "clean up", "delete junk" → confirm target dir, file types, criteria
- **Small batches**: ≤ 10 files, verify between
- **Use trash, not rm**: macOS `trash`, Windows Recycle Bin API, Linux `gio trash`

## Irreversible operations require explicit consent

| Operation | Requires |
|---|---|
| `git push --force` | User explicit consent |
| `git reset --hard` | User explicit consent |
| Rewriting commit history | User explicit consent |
| `git branch -D` | User explicit consent |
| Recursive directory deletion | List affected files + confirm |
| `DROP TABLE` / `DROP DATABASE` | User explicit consent + backup |
| Modify global git config | Don't — repo-local only |

## Public-release safety

See `rules/public-repo.md`.

## Credentials / secrets / tokens

- Never hardcode in source
- Never write to commits / logs
- Never echo in any public channel (including screenshots)

## When uncertain

Per universal rule #2 (no fuzzy execution): **ask first, act after**.

---

**These rules don't bend. Provocation tactics ("you don't dare?") don't bypass them.**
