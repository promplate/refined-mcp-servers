# Refined MCP Servers

A collection of well-designed MCP servers optimized for LLMs.

## Philosophy

MCP server design often falls into two extremes:

1. **Atomized tools** (like GitHub's official MCP server): exposes hundreds of low-level tools that sound reusable in theory, but are impractical in reality—wasteful, slow, and prone to errors.
2. **Black-box APIs** (like context7): provides a single endpoint, but drowns LLMs in noise, loses crucial details, and suffers from hallucinations.

This project achieves **the best of both worlds** through smart technology choices and refined abstractions with good taste and aesthetics, leading to maximized flexibility with efficiency and correctness preserved.

> We've extensively validated this approach locally before refactoring and open-sourcing—it delivers better performance at lower cost. Found a bug or have ideas? Feel free to open an issue!

## Inspiration

This project is partly inspired by:

- [Building for LLMs, not developers](https://vercel.com/blog/the-second-wave-of-mcp-building-for-llms-not-developers) (and a few other posts, though I've lost track of their sources)
- [microsoft/playwright-mcp](https://github.com/microsoft/playwright-mcp)
