use anyhow::{Context, Result};
use rusqlite::Connection;
use std::path::PathBuf;

pub fn db_path() -> Result<PathBuf> {
    if let Ok(p) = std::env::var("GREENBELT_DB") {
        return Ok(PathBuf::from(p));
    }
    let home = home::home_dir().context("could not determine home directory")?;
    Ok(home.join(".claude").join("greenbelt.sqlite3"))
}

pub fn open_db() -> Result<Connection> {
    let path = db_path()?;
    if let Some(parent) = path.parent() {
        std::fs::create_dir_all(parent)
            .with_context(|| format!("could not create db directory {}", parent.display()))?;
    }
    let conn = Connection::open(&path)
        .with_context(|| format!("could not open database {}", path.display()))?;
    conn.execute_batch("PRAGMA journal_mode=WAL; PRAGMA synchronous=NORMAL;")
        .context("could not set database pragmas")?;
    Ok(conn)
}

pub fn init_db(conn: &Connection) -> Result<()> {
    conn.execute_batch(
        "CREATE TABLE IF NOT EXISTS usage_events (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id  TEXT    NOT NULL,
            used_tokens INTEGER NOT NULL,
            created_at  TEXT    NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_usage_events_created_at
            ON usage_events(created_at);
        CREATE TABLE IF NOT EXISTS planted_trees (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            used_tokens INTEGER NOT NULL,
            num_trees   INTEGER NOT NULL,
            provider    TEXT    NOT NULL,
            created_at  TEXT    NOT NULL
        );",
    )
    .context("could not initialize database schema")
}

pub fn add_usage(conn: &Connection, session_id: &str, used_tokens: u64, created_at: &str) -> Result<()> {
    conn.execute(
        "INSERT INTO usage_events (session_id, used_tokens, created_at) VALUES (?1, ?2, ?3)",
        rusqlite::params![session_id, used_tokens as i64, created_at],
    )
    .context("could not insert usage event")?;
    Ok(())
}

pub fn add_trees(conn: &Connection, used_tokens: u64, num_trees: u64, provider: &str, created_at: &str) -> Result<()> {
    conn.execute(
        "INSERT INTO planted_trees (used_tokens, num_trees, provider, created_at) VALUES (?1, ?2, ?3, ?4)",
        rusqlite::params![used_tokens as i64, num_trees as i64, provider, created_at],
    )
    .context("could not insert planted trees")?;
    Ok(())
}

pub fn get_total_trees(conn: &Connection) -> Result<u64> {
    let n: i64 = conn
        .query_row(
            "SELECT COALESCE(SUM(num_trees), 0) FROM planted_trees",
            [],
            |row| row.get(0),
        )
        .context("could not query total trees")?;
    Ok(n.max(0) as u64)
}

pub fn get_unaccounted_usage(conn: &Connection) -> Result<u64> {
    let n: i64 = conn
        .query_row(
            "SELECT COALESCE((SELECT SUM(used_tokens) FROM usage_events), 0)
                  - COALESCE((SELECT SUM(used_tokens) FROM planted_trees), 0)",
            [],
            |row| row.get(0),
        )
        .context("could not query unaccounted usage")?;
    Ok(n.max(0) as u64)
}
