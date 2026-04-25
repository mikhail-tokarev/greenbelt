<p align="center">
<a href="https://github.com/mikhail-tokarev/greenbelt/stargazers"><img src="https://img.shields.io/github/stars/mikhail-tokarev/greenbelt?style=flat" alt="GitHub Repo stars"></a>
<a href="LICENSE"><img src="https://img.shields.io/github/license/mikhail-tokarev/greenbelt" alt="MIT License"></a>
</p>

# Greenbelt 🌱

Greenbelt tracks token usage across Claude Code sessions and plants trees whenever your token usage crosses a configurable threshold (1M tokens by default). It uses [Ecologi API](https://ecologi.com/) and runs as a Claude Code hook — no manual steps required after setup.

[Ecologi](https://ecologi.com) is a climate action platform that helps individuals and businesses take measurable, credible action for climate and nature. Fund tree planting from €0.80 (£0.60) per tree. File a feature request if you want to use a different provider.

## In Action
<img width="972" height="497" alt="Screenshot 2026-03-18 at 11 43 08" src="https://github.com/user-attachments/assets/5eb23510-253b-44a7-845e-27764aefa004" />

## Get started

Copy and paste the AI prompt:
```
Clone https://github.com/mikhail-tokarev/greenbelt into the ~/.claude folder and add the hooks as described in README.md
```

**1. Register the hooks**

Add the following to your Claude Code settings (`~/.claude/settings.json`):

> [!IMPORTANT]
> Replace `/path/to/greenbelt` with the absolute path where you cloned the repo.

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

**2. Configure Ecologi**

On the first run, Greenbelt creates `~/.claude/greenbelt.toml` automatically:

```toml
provider = "ecologi"
threshold = 1_000_000   # plant trees every 1M tokens

[ecologi]
api_key = ""            # get it from https://app.ecologi.com/impact-api
```

Fill in your [Ecologi API](https://app.ecologi.com/impact-api) key. Adjust `threshold` to control how often trees are planted.

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

## Gallery

Showcase your impact with Ecologi. Find your badge in `Business toolkit` > `Dynamic logos`.

![Mike](https://api.ecologi.com/badges/trees/69b932ffb5241f46d9b8e6c8?black=true&treeOnly=true)
