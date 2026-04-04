use anyhow::Result;
use std::io::{BufRead, BufReader};
use std::path::Path;

pub fn calculate_used_tokens(path: &Path) -> Result<u64> {
    let file = match std::fs::File::open(path) {
        Ok(f) => f,
        Err(e) if e.kind() == std::io::ErrorKind::NotFound => return Ok(0),
        Err(e) => return Err(e.into()),
    };
    let mut total: u64 = 0;
    for line in BufReader::new(file).lines() {
        let line = match line {
            Ok(l) => l,
            Err(_) => continue,
        };
        let trimmed = line.trim();
        if trimmed.is_empty() {
            continue;
        }
        total += parse_line_tokens(trimmed);
    }
    Ok(total)
}

fn parse_line_tokens(line: &str) -> u64 {
    let v: serde_json::Value = match serde_json::from_str(line) {
        Ok(v) => v,
        Err(_) => return 0,
    };

    // 1. toolUseResult.totalTokens
    if let Some(t) = v.get("toolUseResult").and_then(|r| r.get("totalTokens")).and_then(|t| t.as_u64()) {
        return t;
    }

    let kind = v.get("type").and_then(|t| t.as_str()).unwrap_or("");

    // 2. type == "assistant"
    if kind == "assistant" {
        let input = v
            .pointer("/message/usage/input_tokens")
            .and_then(|t| t.as_u64())
            .unwrap_or(0);
        let output = v
            .pointer("/message/usage/output_tokens")
            .and_then(|t| t.as_u64())
            .unwrap_or(0);
        return input + output;
    }

    // 3. type == "progress" with agent_progress
    if kind == "progress" {
        let data_type = v.pointer("/data/type").and_then(|t| t.as_str()).unwrap_or("");
        let msg_type = v.pointer("/data/message/type").and_then(|t| t.as_str()).unwrap_or("");
        if data_type == "agent_progress" && msg_type == "assistant" {
            let input = v
                .pointer("/data/message/message/usage/input_tokens")
                .and_then(|t| t.as_u64())
                .unwrap_or(0);
            let output = v
                .pointer("/data/message/message/usage/output_tokens")
                .and_then(|t| t.as_u64())
                .unwrap_or(0);
            return input + output;
        }
    }

    0
}
