use anyhow::{Context, Result};
use serde::{Deserialize, Serialize};
use std::path::PathBuf;

const CONFIG_TEMPLATE: &str = r#"provider = "ecologi"
threshold = 1_000_000

[ecologi]
api_key = "" # get it from https://app.ecologi.com/impact-api
"#;

#[derive(Debug, Deserialize, Serialize)]
pub struct EcologiConfig {
    pub api_key: String,
}

#[derive(Debug, Deserialize, Serialize)]
pub struct Config {
    pub provider: String,
    pub threshold: u64,
    pub ecologi: Option<EcologiConfig>,
}

pub fn config_path() -> Result<PathBuf> {
    if let Ok(p) = std::env::var("GREENBELT_CONFIG") {
        return Ok(PathBuf::from(p));
    }
    let home = home::home_dir().context("could not determine home directory")?;
    Ok(home.join(".claude").join("greenbelt.toml"))
}

pub fn load_config() -> Result<Config> {
    let path = config_path()?;
    if !path.exists() {
        if let Some(parent) = path.parent() {
            std::fs::create_dir_all(parent)
                .with_context(|| format!("could not create config directory {}", parent.display()))?;
        }
        std::fs::write(&path, CONFIG_TEMPLATE)
            .with_context(|| format!("could not write default config to {}", path.display()))?;
    }
    let contents = std::fs::read_to_string(&path)
        .with_context(|| format!("could not read config file {}", path.display()))?;
    toml::from_str(&contents)
        .with_context(|| format!("could not parse config file {}", path.display()))
}
