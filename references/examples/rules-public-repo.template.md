# Public Repository Hard Rules (template)

> Rules that agents MUST follow before pushing to any public repository.
> Customize the wildcards below for your situation.

## 1. Git author check

Before any `git push` to a public remote, verify:

```bash
git config user.email   # Must be your PUBLIC email, not your work/internal one
git config user.name    # Must be your PUBLIC handle
```

If the repo inherits an internal email from global config, set repo-local override:

```bash
git config user.email "<your-public-email>"
git config user.name  "<your-public-handle>"
# Do NOT change global config
```

## 2. Internal-info scan (must return 0 hits)

```bash
grep -rn -E "<internal-username>|<internal-domain>|<internal-tools>|<private-project-codenames>" . \
  --exclude-dir=.git --exclude-dir=node_modules
```

Replace these patterns with your actual blocklist (kept in your private memory, not in any public file):

- Internal usernames / employee IDs
- Internal email domain
- Internal tool/system names (replace with generic equivalents in code/docs)
- Private project codenames

## 3. Private project codenames must never appear

In **any** public file: README, code comments, commit messages, variable names, test cases, screenshots.

## 4. Public-facing identity

| Platform | ID |
|---|---|
| GitHub | `<your-handle>` |
| Public email | `<your-public-email>` |

## 5. Pre-publish checklist

- [ ] Git author check passed
- [ ] Internal-info scan: 0 hits
- [ ] Private codenames: 0 occurrences
- [ ] LICENSE file exists
- [ ] README does not contain "self-incriminating" phrases (no "Removed encryption", "Migrated from", etc. that audit tools may flag)
