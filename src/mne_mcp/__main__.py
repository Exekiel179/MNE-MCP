"""
Command-line interface for the MNE MCP server.
"""

import argparse
import json
import sys

from mne_mcp.claude_config import (
    SERVER_KEY,
    build_mcp_server_config,
    configure_claude_settings,
    get_default_settings_path,
    get_entrypoint_config,
)


def main():
    parser = argparse.ArgumentParser(
        prog="python -m mne_mcp", description="MNE-Python Model Context Protocol server"
    )
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # serve
    serve_parser = subparsers.add_parser("serve", help="Run the MCP server")
    serve_parser.add_argument(
        "--transport",
        choices=["stdio", "streamable-http", "sse"],
        default="stdio",
        help="Transport to use (default: stdio)",
    )
    serve_parser.add_argument("--host", default="localhost")
    serve_parser.add_argument("--port", type=int, default=8000)

    # status
    subparsers.add_parser("status", help="Show MNE detection results and exit")

    # version
    subparsers.add_parser("version", help="Print version information")

    # setup-info
    subparsers.add_parser("setup-info", help="Show Claude Code MCP config snippet")

    # configure (defaults wizard)
    cfg_parser = subparsers.add_parser(
        "configure",
        help="Interactively set default analysis parameters (line freq, montage, filter band, …)",
    )
    cfg_parser.add_argument(
        "--show", action="store_true", help="Print current defaults and exit"
    )
    cfg_parser.add_argument(
        "--reset", action="store_true", help="Reset defaults to built-in values"
    )
    cfg_parser.add_argument(
        "--set",
        nargs="+",
        metavar="KEY=VALUE",
        help="Set values non-interactively, e.g. --set line_freq=60 default_montage=biosemi64",
    )

    # setup (one-click multi-client registration + skills)
    setup_parser = subparsers.add_parser(
        "setup",
        help="Verify MCP, register Claude Code / Codex / PsyClaw / opencode and install skills",
    )
    setup_parser.add_argument(
        "--clients",
        default="all",
        help="Comma list: claude,codex,psyclaw,opencode (default: all)",
    )
    setup_parser.add_argument(
        "--no-skills",
        action="store_true",
        help="Do not install the bundled MNE skills (analyst, guard, methodology critic + analysis suite)",
    )
    verify_parser = subparsers.add_parser(
        "verify", help="Test MCP handshake, tools and status without registering"
    )
    verify_parser.add_argument(
        "--client", choices=["psyclaw"], help="Test the saved PsyClaw server entry"
    )

    # configure-claude
    configure_parser = subparsers.add_parser(
        "configure-claude",
        help="Register the MCP server in Claude Code only (subset of `setup`)",
    )
    configure_parser.add_argument(
        "--settings-file",
        help="Explicit Claude Code settings file path to update",
    )
    configure_parser.add_argument(
        "--local",
        action="store_true",
        help="Write to settings.local.json instead of settings.json",
    )

    args = parser.parse_args()

    if not args.command:
        args.command = "serve"
        args.transport = "stdio"

    if args.command == "version":
        from mne_mcp._version import __version__

        print(f"MNE MCP v{__version__}")
        sys.exit(0)

    elif args.command == "status":
        from mne_mcp.config import detect_capabilities, get_runtime_config

        caps = detect_capabilities()
        cfg = get_runtime_config()
        print("=== MNE MCP Capability Status ===")
        print(
            f"MNE-Python   : {'OK v' + caps['mne_version'] if caps['mne'] else 'NOT FOUND'}"
        )
        print(
            f"scikit-learn : {'OK v' + caps['sklearn_version'] if caps['sklearn'] else 'unavailable (optional: ICA/decoding)'}"
        )
        print(f"numpy        : {caps['numpy_version'] or 'NOT FOUND'}")
        print(f"scipy        : {caps['scipy_version'] or 'NOT FOUND'}")
        print(f"matplotlib   : {caps['matplotlib_version'] or 'NOT FOUND'}")
        print(f"pandas       : {caps['pandas_version'] or 'NOT FOUND'}")
        print()
        print(f"Results dir  : {cfg['results_dir']}")
        print(f"Data dir     : {cfg['data_dir']}")
        print(f"Timeout      : {cfg['timeout']}s")
        if not caps["mne"]:
            print()
            print(
                f"MNE cannot be imported in {sys.executable}. Activate your MNE environment "
                "and register that interpreter. Inspect the import error before installing dependencies."
            )
        sys.exit(0)

    elif args.command == "setup-info":
        executable_command, executable_args = get_entrypoint_config()

        from mne_mcp._version import __version__

        snippet = {"mcpServers": {SERVER_KEY: build_mcp_server_config()}}

        print(f"=== MNE MCP v{__version__} Setup Info ===")
        print(f"Command: {executable_command}")
        print(f"Args: {json.dumps(executable_args)}")
        print()
        print("Add to your Claude Code MCP settings:")
        print(json.dumps(snippet, indent=2))
        sys.exit(0)

    elif args.command == "configure":
        from mne_mcp import wizard

        if args.reset:
            path = __import__(
                "mne_mcp.config", fromlist=["reset_config"]
            ).reset_config()
            print(f"Reset defaults to built-in values (removed {path}).")
            wizard.show_config()
            sys.exit(0)
        if args.show:
            wizard.show_config()
            sys.exit(0)
        if args.set:
            wizard.set_values(args.set)
            sys.exit(0)
        wizard.run_wizard()
        sys.exit(0)

    elif args.command == "verify":
        from mne_mcp.connection import verify_connection

        try:
            result = verify_connection(registered=args.client == "psyclaw")
        except (OSError, ValueError) as error:
            print(f"Verification failed: {error}", file=sys.stderr)
            sys.exit(2)
        print(json.dumps(result, indent=2))
        sys.exit(0)

    elif args.command == "setup":
        from mne_mcp.claude_config import configure_clients, select_clients
        from mne_mcp.connection import verify_connection

        try:
            clients = select_clients(args.clients)
            connection = verify_connection()
            result = configure_clients(clients, with_skills=not args.no_skills)
            if "psyclaw" in clients:
                connection = verify_connection(registered=True)
        except (OSError, ValueError, json.JSONDecodeError) as e:
            print(f"Setup failed: {type(e).__name__}: {e}", file=sys.stderr)
            sys.exit(2)

        print("=== MNE-MCP setup ===")
        print(
            f"[MCP     ] connected; {connection['tool_count']} tools; mne_check_status OK"
        )
        if not connection["mne_available"]:
            print(
                "[MNE     ] unavailable: MCP is connected, but analysis needs MNE in this interpreter."
            )
        for r in result["clients"]:
            line = f"[{r['client']:<8}] {r['status']:<9} -> {r['path']}"
            if r.get("backup"):
                line += f"   (backup: {r['backup']})"
            print(line)
        sk = result["skills"]
        if sk is not None:
            if sk.get("error"):
                print(f"[skills  ] {sk['error']}")
            else:
                print(f"[skills  ] installed {sk['installed']} -> {sk['dest']}")
        ag = result.get("agents")
        if ag is not None:
            if ag.get("error"):
                print(f"[agents  ] {ag['error']}")
            else:
                print(f"[agents  ] installed {ag['installed']} -> {ag['dest']}")
        print()
        print(
            "Restart your client(s) to load the 'mne' server"
            + ("" if args.no_skills else " and skills/agents")
            + "."
        )
        if "psyclaw" in clients:
            print(
                "PsyClaw: run /reload (or restart), then list the mne server tools and call mne_check_status."
            )
        sys.exit(0)

    elif args.command == "configure-claude":
        settings_path = None
        if args.settings_file:
            from pathlib import Path

            settings_path = Path(args.settings_file).expanduser()
        elif args.local:
            settings_path = get_default_settings_path(local=True)

        result = configure_claude_settings(settings_path, local=args.local)
        print("=== Claude Code configuration updated ===")
        print(f"Status: {result['status']}")
        print(f"Settings: {result['settings_path']}")
        if result["backup_path"]:
            print(f"Backup: {result['backup_path']}")
        print()
        print("Configured MCP entry:")
        print(json.dumps({SERVER_KEY: result["entry"]}, indent=2))
        print()
        print("Restart Claude Code to load the updated MCP server.")
        sys.exit(0)

    elif args.command == "serve":
        from mne_mcp.server import mcp

        transport = getattr(args, "transport", "stdio")
        if transport == "stdio":
            mcp.run(transport="stdio")
        elif transport == "streamable-http":
            mcp.run(transport="streamable-http", host=args.host, port=args.port)
        elif transport == "sse":
            import warnings

            warnings.warn(
                "SSE transport is deprecated. Use streamable-http instead.",
                UserWarning,
            )
            mcp.run(transport="sse", host=args.host, port=args.port)


if __name__ == "__main__":
    main()
