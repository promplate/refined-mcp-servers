from os import environ
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
        parser.add_argument("--token", help="Specify the GitHub token", metavar="GITHUB_TOKEN")
        args = parser.parse_args(argv)

        if args.host != "localhost" or args.port is not None:
            if args.stdio:
                parser.error("Cannot use --host or --port with --stdio")
            args.http = True

        if args.token:
            environ["GH_TOKEN"] = args.token

        from .impl import mcp

        if args.http:
            from starlette.middleware import Middleware
            from starlette.middleware.cors import CORSMiddleware
            from uvicorn import Config, Server

            app = mcp.http_app(
                stateless_http=True,
                json_response=True,
                middleware=[
                    Middleware(
                        CORSMiddleware,
                        allow_origins=["*"],
                        allow_methods=["*"],
                        allow_headers=["mcp-protocol-version", "mcp-session-id", "Authorization", "Content-Type"],
                        expose_headers=["mcp-session-id"],
                    )
                ],
            )
            Server(Config(app, host=args.host, port=args.port or 8000, timeout_graceful_shutdown=0.1)).run()  # type: ignore
        else:
            mcp.run("stdio", show_banner=False)

    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
