from sys import argv


def main(argv: list[str] = argv[1:]):
    try:
        if not argv:
            from .impl import mcp

            return mcp.run("stdio", show_banner=False)

        from argparse import ArgumentParser

        parser = ArgumentParser("gh-mcp", description="Refined MCP server for GitHub GraphQL API")
        transport_group = parser.add_mutually_exclusive_group()
        transport_group.add_argument("--stdio", action="store_true", help="Run with stdio transport (default)")
        transport_group.add_argument("--http", action="store_true", help="Run with streamable-http transport")
        parser.add_argument("--host", default="localhost", help="Host to run the HTTP server on")
        parser.add_argument("--port", type=int, help="Port to run the HTTP server on")
        args = parser.parse_args(argv)

        from .impl import mcp

        if args.http:
            mcp.run("http", show_banner=False, port=args.port, host=args.host)
        else:
            mcp.run("stdio", show_banner=False)

    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
