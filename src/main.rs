use std::fs;
use std::io::{self, IsTerminal, Read};
use std::path::PathBuf;
use std::process::ExitCode;

use clap::Parser;
use libpgfmt::style::Style;

#[derive(Parser)]
#[command(name = "pgfmt", about = "Format PostgreSQL SQL statements")]
struct Cli {
    /// SQL files to format (reads stdin if none given)
    files: Vec<PathBuf>,

    /// Formatting style
    #[arg(long, default_value = "river")]
    style: Style,

    /// Check if files are already formatted (exit 1 if not)
    #[arg(long)]
    check: bool,
}

fn format_sql(sql: &str, style: Style) -> Result<String, String> {
    libpgfmt::format(sql, style).map_err(|e| e.to_string())
}

fn process(name: &str, sql: &str, cli: &Cli) -> Result<bool, String> {
    if sql.trim().is_empty() {
        return Ok(true);
    }
    let formatted = format_sql(sql, cli.style)?;
    if cli.check {
        if formatted.trim() != sql.trim() {
            eprintln!("Would reformat: {name}");
            return Ok(false);
        }
    } else {
        print!("{formatted}");
    }
    Ok(true)
}

fn run() -> Result<ExitCode, String> {
    let cli = Cli::parse();
    let mut all_ok = true;

    if cli.files.is_empty() {
        if io::stdin().is_terminal() && !cli.check {
            return Err("no input files and stdin is a terminal".to_string());
        }
        let mut sql = String::new();
        io::stdin()
            .read_to_string(&mut sql)
            .map_err(|e| e.to_string())?;
        if !process("<stdin>", &sql, &cli)? {
            all_ok = false;
        }
    } else {
        for path in &cli.files {
            let sql = fs::read_to_string(path).map_err(|e| format!("{}: {e}", path.display()))?;
            let name = path.display().to_string();
            if !process(&name, &sql, &cli)? {
                all_ok = false;
            }
        }
    }

    if all_ok {
        Ok(ExitCode::SUCCESS)
    } else {
        Ok(ExitCode::FAILURE)
    }
}

fn main() -> ExitCode {
    match run() {
        Ok(code) => code,
        Err(msg) => {
            eprintln!("pgfmt: {msg}");
            ExitCode::FAILURE
        }
    }
}
