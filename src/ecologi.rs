use anyhow::{bail, Result};

pub fn plant_trees(api_key: &str, number: u64, idempotency_key: &str) -> Result<()> {
    let body = serde_json::json!({
        "name": "Claude",
        "number": number
    });

    let response = ureq::post("https://public.ecologi.com/impact/trees")
        .set("Authorization", &format!("Bearer {api_key}"))
        .set("Idempotency-Key", idempotency_key)
        .set("Accept", "application/json")
        .send_json(&body);

    match response {
        Ok(r) if r.status() == 201 => {}
        Ok(r) => {
            let status = r.status();
            let text = r.into_string().unwrap_or_default();
            bail!("Ecologi API returned {status}: {text}");
        }
        Err(ureq::Error::Status(status, r)) => {
            let text = r.into_string().unwrap_or_default();
            bail!("Ecologi API returned {status}: {text}");
        }
        Err(e) => return Err(e.into()),
    }

    Ok(())
}
