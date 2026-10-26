from contextlib import suppress
from json import JSONDecodeError, dumps, loads
from os import environ
from typing import Literal

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from fastmcp.server.dependencies import get_http_headers
from mcp.types import ToolAnnotations
from pydantic import Field

from .utils import run_subprocess
from .yaml import readable_yaml_dumps

__version__ = "0.3.8"

mcp = FastMCP("gh", version=__version__, include_fastmcp_meta=False)

mcp.instructions = "Access GitHub with GraphQL and exact code search."


DEFAULT_JQ = r"""
def process:
    if type == "object" then
        if has("text") and (.text | type == "string") then
            if (.text | split("\n") | length) > 10 then
                del(.text) + {lines: (.text | split("\n") | to_entries | map("\(.key + 1)\t\(.value)") | join("\n"))}
            else
                .
            end
        else
            with_entries(.value |= process)
        end
    elif type == "array" then
        map(process)
    else
        .
    end;
.data | process
"""


@mcp.tool(title="GitHub GraphQL")
async def github_graphql(query: str, jq: str = DEFAULT_JQ):
    """
    Execute authenticated GitHub GraphQL queries and mutations through gh CLI.

    Batch independent evidence needed for the task into one query: combine relevant repository metadata, issues/PRs, commits, and files using nested selections, aliases, fragments, or nodes(ids:). Select only needed fields and bound connections. Reuse returned facts; query again to resolve remaining uncertainty.

    Use jq on the full response to return compact facts, source URLs, and relevant file excerpts with original line numbers. For example, .data.repository | {url, pr: (.pullRequest | {state, headRefOid})}. jq runs after GitHub responds: it reduces tool output, not the query's server-side cost.

    Use known repository/ref/path identifiers directly. Read files with object(expression:"REF:PATH") { ... on Blob { text } }. A successful read already establishes that file at that ref; extra directory listings or commit-existence checks add no evidence. For unknown paths, use narrow Tree listings or code search, then read the relevant files.

    Follow pageInfo { hasNextPage endCursor } when complete lists are needed. Introspect uncertain fields only. Default jq: .data and numbered text over 10 lines; jq="": unfiltered response. Read source for code claims and cite commit-pinned line links; otherwise cite the relevant GitHub objects.
    """

    cmd = ["gh", "api", "graphql", "--input", "-"]

    if jq:
        cmd.extend(["--jq", jq])

    ret = await run_subprocess(cmd, input=dumps({"query": query}, ensure_ascii=False).encode(), env=_get_env())

    result = ret.stdout or ret.stderr or ""

    if not result.strip():
        raise ToolError("[[ The response is empty. Please adjust your query and try again! ]]")

    result = result.replace("\r\n", "\n")

    with suppress(JSONDecodeError):
        data = loads(result)

        if ret.returncode:
            raise ToolError(readable_yaml_dumps(data))
        return readable_yaml_dumps(data)

    return result


@mcp.tool(title="GitHub Code Search", annotations=ToolAnnotations(readOnlyHint=True))
async def github_code_search(
    code_snippet: str = Field(description="Search exact string you want to find. DO NOT use any wildcard syntax."),
    extension: str = Field(default_factory=str),
    filename: str = Field(default_factory=str),
    owner: list[str] = Field(default_factory=list),
    repo: list[str] = Field(default_factory=list, description="Format: owner/repo"),
    language: str = Field(default_factory=str),
    match_type: Literal["content", "path"] = "content",
):
    """
    Search files on GitHub with code snippets. This is not a fuzzy search, so provide exact substrings you want to find.

    Normally you should try different queries and combinations of filters until you get useful results.
    If you are searching for something generic, try thinking in reverse about what the code might be, and search for that code snippet instead.
    """

    if any("/" not in i for i in repo):
        raise ToolError("Please provide the `repo` option in the format 'owner/repo'")

    if not any((extension, filename, owner, repo, language)) and len(code_snippet) - 3 * (code_snippet.count(" ") + code_snippet.count(".")) < 7:
        raise ToolError("Query too broad. Please refine your search.")

    cmd = ["gh", "search", "code", code_snippet, "--limit", "100"]

    if extension:
        cmd += ["--extension", extension]
    if filename:
        cmd += ["--filename", filename]
    for i in owner:
        cmd += ["--owner", i]
    for i in repo:
        cmd += ["--repo", i]
    if language:
        cmd += ["--language", language]

    if match_type == "path":
        cmd += ["--match", "path", "--json", "url", "--jq", ".[] | .url"]
    else:
        cmd += ["--json", "url,textMatches"]

    ret = await run_subprocess(cmd, env=_get_env())

    if ret.returncode:
        raise ToolError(ret.stdout or ret.stderr or "[[ An unknown error occurred during the code search. ]]")

    if match_type == "path":
        return ret.stdout or ret.stderr

    assert ret.stdout is not None

    data = loads(ret.stdout)
    for item in data:
        item["fragments"] = [i["fragment"] for i in item.pop("textMatches")]

    return readable_yaml_dumps(data)


def _get_env():
    gh_token = get_http_headers().get("x-gh-token")
    return environ | {"GH_TOKEN": gh_token} if gh_token else None
