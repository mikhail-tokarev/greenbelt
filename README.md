# Greenbelt 🌱

## Goal

Greenbelt tracks token usage across Claude Code sessions and plants trees whenever your token usage crosses a configurable threshold. It runs as a Claude Code hook — no manual steps required after setup.

## Get started

**1. Clone the repo**

```bash
git clone https://github.com/mikhail-tokarev/greenbelt.git ~/.claude/greenbelt
```

**2. Register the hooks**

Add the following to your Claude Code settings (`~/.claude/settings.json`):

> [!IMPORTANT]
> Replace `/path/to/greenbelt` with the actual path where you cloned the repo.

```json
{
  "hooks": {
    "SessionStart": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "python3 /path/to/greenbelt/session_hook.py"
          }
        ]
      }
    ],
    "SessionEnd": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "python3 /path/to/greenbelt/session_hook.py"
          }
        ]
      }
    ]
  }
}
```

**3. Configure Ecologi**

On the first run, Greenbelt creates `~/.claude/greenbelt.toml` automatically:

```toml
provider = "ecologi"
threshold = 1_000_000   # plant trees every 1M tokens

[ecologi]
api_key = ""            # get it from https://app.ecologi.com/impact-api
```

Fill in your Ecologi API key. Adjust `threshold` to control how often trees are planted.

**That's it.** From this point on, Greenbelt runs silently in the background. At the start of each session it shows how many trees you've planted so far.

## Uninstall

1. **Remove the hooks** — delete the `SessionStart` and `SessionEnd` entries added in step 2 from your Claude Code settings file.

2. **Delete the data files**:

```bash
rm ~/.claude/greenbelt.sqlite3
rm ~/.claude/greenbelt.toml
```

3. **Delete the repo** (optional):

```bash
rm -rf ~/.claude/greenbelt
```
