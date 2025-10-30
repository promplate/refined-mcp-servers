# Refined MCP server for GitHub

> [!TIP]
> If you haven't read the article [The second wave of MCP: Building for LLMs, not developers](https://vercel.com/blog/the-second-wave-of-mcp-building-for-llms-not-developers) by Vercel, I highly recommend checking it out to understand why we're building this project.

[GitHub's official MCP Server](https://github.com/github/github-mcp-server) exposes dozens of low-level tools that bloat token usage and are mostly impractical for LLMs. `gh-mcp` achieves the best of both worlds by providing powerful interfaces: GitHub GraphQL and Code Search, wrapped with smart abstractions.

This project does 3 things differently:

1. **Powerful interfaces** — exposes GraphQL and Code Search instead of atomized endpoints. LLMs already understand these APIs.
2. **YAML output** — makes nested data and file content readable without escaping.
3. **Clean abstractions** — `gh` handles authentication and low-level details. And LLMs know how to use its `--jq` option to filter.

Swapping in `gh-mcp` delivers better performance at lower cost for any GitHub interactions.

## Installation

with uv:

```sh
uvx mcp-hmr
```

MCP config:

```json
{
    "mcpServers": {
        "gh": {
            "command": "uvx",
            "args": ["gh-mcp"]
        }
    }
}
```

If you prefer serving it via streamable-http:

```sh
uvx gh-mcp --http
```

> [!NOTE]
> This project requires `gh` CLI to be installed and authenticated. Please follow the instructions at [cli.github.com](https://cli.github.com/) to set it up. And then you can login via `gh auth login`. Check that `gh auth status` works before using this MCP server.
