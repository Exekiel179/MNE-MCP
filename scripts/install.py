"""Install the lightweight interface into the current scientific environment."""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def detect_clients() -> list[str]:
    """Config presence is evidence of a client, not permission to configure it."""
    home = Path.home()
    paths = {
        "codex": Path(os.environ.get("CODEX_HOME", str(home / ".codex")))
        / "config.toml",
        "claude": home / ".claude.json",
        "psyclaw": home / ".psyclaw",
        "opencode": Path(os.environ.get("XDG_CONFIG_HOME", str(home / ".config")))
        / "opencode"
        / "opencode.json",
    }
    return [name for name, path in paths.items() if path.exists()]


def preflight(python: str) -> dict:
    """Read-only probe in the target interpreter; preserve actual import errors."""
    code = """
import importlib, json, sys
checks = {}
for name in ("mne", "numpy", "scipy", "matplotlib", "pandas", "pip"):
    try:
        module = importlib.import_module(name)
        checks[name] = {"ok": True, "version": str(getattr(module, "__version__", "unknown"))}
    except Exception as error:
        missing = isinstance(error, ModuleNotFoundError) and error.name == name
        checks[name] = {"ok": False, "missing": missing, "error": f"{type(error).__name__}: {error}"}
print("__MNE_PROBE__" + json.dumps({"python": sys.executable, "version": list(sys.version_info[:3]), "dependencies": checks}))
"""
    result = subprocess.run(
        [python, "-c", code], check=True, capture_output=True, text=True
    )
    line = next(
        (
            line
            for line in reversed(result.stdout.splitlines())
            if line.startswith("__MNE_PROBE__")
        ),
        None,
    )
    if line is None:
        raise ValueError("Interpreter probe returned no diagnostic JSON")
    report = json.loads(line[len("__MNE_PROBE__") :])
    report["detected_clients"] = detect_clients()
    report["ready"] = report["version"][:2] >= [3, 12] and all(
        item["ok"] for item in report["dependencies"].values()
    )
    return report


def select_clients(value: str) -> list[str]:
    if value.strip().lower() == "all":
        return ["claude", "codex", "psyclaw", "opencode"]
    if value == "auto":
        detected = detect_clients()
        if len(detected) != 1:
            raise ValueError(
                "Client selection is ambiguous. Use --clients codex, claude, psyclaw, or opencode; --check --json lists detected clients."
            )
        return detected
    selected = list(
        dict.fromkeys(c.strip().lower() for c in value.split(",") if c.strip())
    )
    if not selected or set(selected) - {"claude", "codex", "psyclaw", "opencode"}:
        raise ValueError("Select clients from: claude, codex, psyclaw, opencode")
    return selected


def prepare_environment(python: str, report: dict) -> None:
    """Install absent core libraries only; broken imports need diagnosis."""
    if report["ready"]:
        return
    dependencies = report.get("dependencies", {})
    core = {
        "mne": "mne>=1.6",
        "numpy": "numpy",
        "scipy": "scipy",
        "matplotlib": "matplotlib",
        "pandas": "pandas",
    }
    failed = {name: item for name, item in dependencies.items() if not item["ok"]}
    if (
        report.get("version", [])[:2] < [3, 12]
        or not dependencies.get("pip", {}).get("ok")
        or any(
            name not in core or not item.get("missing") for name, item in failed.items()
        )
    ):
        raise ValueError(
            "Environment needs diagnosis: " + json.dumps(report, ensure_ascii=False)
        )
    packages = [core[name] for name in failed]
    if not packages:
        raise ValueError("Incomplete environment diagnostic: " + json.dumps(report))
    print("Installing missing core libraries: " + ", ".join(packages), flush=True)
    subprocess.run([python, "-m", "pip", "install", *packages], check=True)
    verified = preflight(python)
    if not verified["ready"]:
        raise ValueError(
            "Core installation did not pass verification: " + json.dumps(verified)
        )


def install(*, clients: str, skip_configure: bool, python: str | None = None) -> None:
    selected = [] if skip_configure else select_clients(clients)
    python = python or sys.executable
    print(f"Using existing environment: {python}", flush=True)
    report = preflight(python)
    prepare_environment(python, report)
    subprocess.run([python, "-m", "pip", "install", str(ROOT)], check=True)
    subprocess.run([python, "-m", "mne_mcp.cli", "status"], check=True)
    if not skip_configure:
        subprocess.run(
            [python, "-m", "mne_mcp.cli", "setup", "--clients", ",".join(selected)],
            check=True,
        )
    print(
        "Installation verified. Restart the selected client to load MCP and skills.",
        flush=True,
    )


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--clients",
        default="all",
        help="Default: all; or select claude,codex,psyclaw,opencode",
    )
    parser.add_argument(
        "--python",
        default=sys.executable,
        help="Existing MNE environment's Python executable",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Read-only environment preflight; does not install or configure",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Machine-readable preflight output (requires --check)",
    )
    parser.add_argument("--skip-configure", action="store_true")
    args = parser.parse_args(argv)
    if args.json and not args.check:
        parser.error("--json requires --check")
    try:
        if args.check:
            report = preflight(args.python)
            print(json.dumps(report, ensure_ascii=False, indent=2))
            return 0 if report["ready"] else 1
        install(
            clients=args.clients, skip_configure=args.skip_configure, python=args.python
        )
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        if args.json:
            print(
                json.dumps({"ready": False, "python": args.python, "error": str(error)})
            )
            return 1
        print(f"Installation failed in {args.python}: {error}", file=sys.stderr)
        print(
            "Check the selected Python environment and the reported error. Only absent core libraries are installed automatically; broken imports require diagnosis.",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
