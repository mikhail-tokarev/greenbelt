use anyhow::Result;
use greenbelt::{config, db, ecologi, transcript};
use serde::Deserialize;
use std::path::Path;

#[derive(Deserialize)]
struct HookInput {
    hook_event_name: String,
    session_id: String,
    #[serde(default)]
    transcript_path: Option<String>,
}

fn main() {
    if let Err(e) = run() {
        eprintln!("[greenbelt] {e}");
        std::process::exit(1);
    }
}

fn run() -> Result<()> {
    let cfg = config::load_config()
        .map_err(|e| anyhow::anyhow!("Failed to parse config: {e}"))?;

    let input: HookInput = serde_json::from_reader(std::io::stdin())
        .map_err(|e| anyhow::anyhow!("Failed to parse hook payload: {e}"))?;

    let conn = db::open_db()?;
    db::init_db(&conn)?;

    match input.hook_event_name.as_str() {
        "SessionStart" => session_start(&conn),
        "SessionEnd" => session_end(&cfg, &conn, &input),
        other => {
            eprintln!("[greenbelt] Unknown hook event: {other}");
            Ok(())
        }
    }
}

fn session_start(conn: &rusqlite::Connection) -> Result<()> {
    let total = db::get_total_trees(conn)?;
    println!(
        r#"{{"continue": true, "systemMessage": "🌱 You've planted {total} trees simply by using Claude Code, helping reduce your CO2 impact!"}}"#
    );
    Ok(())
}

fn session_end(cfg: &config::Config, conn: &rusqlite::Connection, input: &HookInput) -> Result<()> {
    let transcript_path = match &input.transcript_path {
        Some(p) if !p.is_empty() => Path::new(p).to_path_buf(),
        _ => return Ok(()),
    };

    let used_tokens = transcript::calculate_used_tokens(&transcript_path)?;
    if used_tokens == 0 {
        return Ok(());
    }

    let now = chrono::Utc::now().to_rfc3339();
    db::add_usage(conn, &input.session_id, used_tokens, &now)?;

    let unaccounted = db::get_unaccounted_usage(conn)?;
    let trees_to_plant = unaccounted / cfg.threshold;
    if trees_to_plant == 0 {
        return Ok(());
    }

    if cfg.provider != "ecologi" {
        eprintln!("[greenbelt] Unsupported provider: {}", cfg.provider);
        return Ok(());
    }

    let api_key = cfg.ecologi.as_ref().map(|e| e.api_key.as_str()).unwrap_or("");
    if api_key.is_empty() {
        eprintln!("[greenbelt] Warning: ecologi.api_key is blank; skipping tree planting");
        return Ok(());
    }

    if let Err(e) = ecologi::plant_trees(api_key, trees_to_plant, &input.session_id) {
        eprintln!("[greenbelt] Failed to plant trees: {e}");
        return Ok(());
    }

    let now = chrono::Utc::now().to_rfc3339();
    db::add_trees(conn, trees_to_plant * cfg.threshold, trees_to_plant, &cfg.provider, &now)?;

    Ok(())
}
