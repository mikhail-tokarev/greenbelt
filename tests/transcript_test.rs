use std::path::Path;

#[test]
fn test_transcript_token_count() {
    let path = Path::new(env!("CARGO_MANIFEST_DIR")).join("test_transcript.jsonl");
    let total = greenbelt::transcript::calculate_used_tokens(&path)
        .expect("should parse test transcript");
    assert_eq!(total, 131_225, "token count must match Python reference");
}
