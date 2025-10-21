# `gh-mcp` - Refined MCP server for GitHub GraphQL API

> [!TIP]
> If you haven't read the article [The second wave of MCP: Building for LLMs, not developers](https://vercel.com/blog/the-second-wave-of-mcp-building-for-llms-not-developers) by Vercel, I highly recommend checking it out to understand why we're building this project.

[GitHub's official MCP Server](https://github.com/github/github-mcp-server) sucks, because it is exposing millions of tools which takes tens of thousands of tokens to describe, and most of them are useless for LLMs.

This project does 3 things differently:

1. It only exposes the GitHub GraphQL API, which is powerful enough and LLMs are already familiar with it.
2. It returns the JSON response as YAML by default, which makes file content in the returned data more readable (less escaping).
3. It provides a single well-defined tool that wraps around the `gh api graphql` CLI, which takes the authentication and other low-level details away from this implementation. LLMs also know how to use `--jq` to filter the output.

After replacing the official GitHub MCP server with this one, I observed a significant improvement in the performance, cost and speed of my applications that interact with GitHub via LLMs.

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
