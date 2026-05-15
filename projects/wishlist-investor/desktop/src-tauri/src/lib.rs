use serde::{Deserialize, Serialize};
use std::process::{Command, Stdio};
use std::path::PathBuf;

#[derive(Debug, Deserialize)]
struct GenerateRequest {
    portfolio_csv: String,
    wishlist: Vec<String>,
    settings: Option<serde_json::Value>,
}

#[derive(Debug, Serialize)]
struct GenerateResponse {
    ok: bool,
    report: Option<serde_json::Value>,
    error: Option<String>,
}

#[derive(Debug, Deserialize)]
struct PrefetchRequest {
    tickers: Vec<String>,
}

#[derive(Debug, Serialize)]
struct PrefetchResponse {
    ok: bool,
    warmed: Option<i64>,
    error: Option<String>,
}

#[tauri::command]
fn generate_report(req: GenerateRequest) -> GenerateResponse {
    let engine_py = if let Ok(p) = std::env::var("WISHLIST_INVESTOR_ENGINE") {
        PathBuf::from(p)
    } else {
        // dev default: desktop/engine.py (relative to desktop/src-tauri)
        PathBuf::from(env!("CARGO_MANIFEST_DIR"))
            .join("..")
            .join("engine.py")
    };
    let py = std::env::var("WISHLIST_INVESTOR_PYTHON").unwrap_or_else(|_| "python3".to_string());

    let input = serde_json::json!({
        "portfolio_csv": req.portfolio_csv,
        "wishlist": req.wishlist,
        "settings": req.settings,
    });

    match run_engine(py, engine_py, input) {
        Ok(v) => GenerateResponse {
            ok: true,
            report: Some(v),
            error: None,
        },
        Err(e) => GenerateResponse {
            ok: false,
            report: None,
            error: Some(e),
        },
    }
}

fn run_engine(py: String, engine_py: PathBuf, input: serde_json::Value) -> Result<serde_json::Value, String> {
    let mut child = Command::new(py)
        .arg(engine_py)
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .map_err(|e| format!("Failed to start engine: {e}"))?;

    if let Some(mut stdin) = child.stdin.take() {
        use std::io::Write;
        stdin
            .write_all(input.to_string().as_bytes())
            .map_err(|e| format!("Failed to write engine stdin: {e}"))?;
    }

    let out = child
        .wait_with_output()
        .map_err(|e| format!("Engine failed: {e}"))?;
    if !out.status.success() {
        let err = String::from_utf8_lossy(&out.stderr).trim().to_string();
        return Err(if err.is_empty() { "Engine exited with error".to_string() } else { err });
    }
    let s = String::from_utf8_lossy(&out.stdout);
    serde_json::from_str::<serde_json::Value>(&s).map_err(|e| format!("Engine returned invalid JSON: {e}"))
}

#[tauri::command]
fn prefetch_quotes(req: PrefetchRequest) -> PrefetchResponse {
    let engine_py = if let Ok(p) = std::env::var("WISHLIST_INVESTOR_ENGINE") {
        PathBuf::from(p)
    } else {
        PathBuf::from(env!("CARGO_MANIFEST_DIR"))
            .join("..")
            .join("engine.py")
    };
    let py = std::env::var("WISHLIST_INVESTOR_PYTHON").unwrap_or_else(|_| "python3".to_string());

    let input = serde_json::json!({
        "mode": "prefetch",
        "tickers": req.tickers,
    });

    match run_engine(py, engine_py, input) {
        Ok(v) => PrefetchResponse {
            ok: true,
            warmed: v.get("warmed").and_then(|x| x.as_i64()),
            error: None,
        },
        Err(e) => PrefetchResponse {
            ok: false,
            warmed: None,
            error: Some(e),
        },
    }
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_opener::init())
        .invoke_handler(tauri::generate_handler![generate_report, prefetch_quotes])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
