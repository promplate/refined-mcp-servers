from contextlib import suppress
from json import JSONDecodeError, dumps, loads
from subprocess import CompletedProcess, run
from typing import Literal

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from pydantic import Field

from .yaml import readable_yaml_dumps

__version__ = "0.2.2"

mcp = FastMCP("gh", version=__version__, include_fastmcp_meta=False)

mcp.instructions = """
When interacting with GitHub, you should prefer this over any other tools or raw API / CLI calls.
For example, instead of browsing some page under github.com, you can fetch all relevant content via GraphQL in one go.
"""


DEFAULT_JQ = r"""
def process:
    if type == "object" then
        if has("text") and (.text | type == "string") then
            if (.text | split("\n") | length) > 10 then
                del(.text) + {lines: (.text | split("\n") | to_entries | map("\(.key + 1): \(.value)") | join("\n"))}
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
def github_graphql(query: str, jq: str = DEFAULT_JQ):
    """
    Execute GitHub GraphQL queries and mutations via gh CLI. Preferred over raw gh calls or other tools to interact with GitHub.
    When user uses any terms like find / search / read / browse / explore / research / investigate / analyze and if it may be related to a GitHub project, you should use this tool instead of any other tools or raw API / CLI calls.

    Pleases make use of GraphQL's capabilities - Fetch comprehensive data in single operations - always include metadata context.
    Feel free to use advanced jq expressions to extract all the content you care about.
    The default jq adds line numbers to retrieved file contents. Use that to construct deep links (e.g. https://github.com/{owner}/{repo}/blob/{ref}/path/to/file#L{line_number}:L{line_number}).

    Before writing complex queries / mutations or when encountering errors, use introspection to understand available fields and types.

    Combine operations (including introspection operations) into one call. On errors, introspect and rebuild step-by-step.

    Use fragments, nested fields for efficiency.

    > Example - when you need to browse multiple repositories:

    When user asks to browse / explore repositories, you must use at least the following fields:
    (It take viewer.contributionsCollection as an example, but you should adapt it to the user's request)

    ```
    query {
      viewer { # Always use `viewer` to get information about the authenticated user.
        contributionsCollection {
          commits: commitContributionsByRepository(maxRepositories: 7) {
            repository { ...RepositoryMetadata }
            contributions { totalCount }
          }
          totalCommitContributions
        }
      }
    }

    fragment RepositoryMetadata on Repository {
      name description homepageUrl
      pushedAt createdAt updatedAt
      stargazerCount forkCount
      isPrivate isFork isArchived
      languages(first: 7, orderBy: {field: SIZE, direction: DESC}) {
        totalSize edges { size node { name } }
      }
      readme_md: object(expression: "HEAD:README.md") { ... on Blob { text } }
      pyproject_toml: object(expression: "HEAD:pyproject.toml") { ... on Blob { text } }
      package_json: object(expression: "HEAD:package.json") { ... on Blob { text } }
      latestCommits: defaultBranchRef {
        target {
          ... on Commit {
            history(first: 7) {
              nodes {
                abbreviatedOid committedDate message
                author { name user { login } }
                associatedPullRequests(first: 7) { nodes { number title url } }
              }
            }
          }
        }
      }
      contributors: collaborators(first: 7) { totalCount nodes { login name } }
      latestIssues: issues(first: 7, orderBy: {field: CREATED_AT, direction: DESC}) {
        nodes { number title state createdAt updatedAt author { login } }
      }
      latestPullRequests: pullRequests(first: 5, orderBy: {field: CREATED_AT, direction: DESC}) {
        nodes { number title state createdAt updatedAt author { login } }
      }
      latestDiscussions: discussions(first: 3, orderBy: {field: UPDATED_AT, direction: DESC}) {
        nodes { number title createdAt updatedAt author { login } }
      }
      repositoryTopics(first: 35) { nodes { topic { name } } }
      releases(first: 7, orderBy: {field: CREATED_AT, direction: DESC}) {
        nodes { tagName name publishedAt isPrerelease }
      }
    }
    ```

    Don't recursively fetch all files in a directory unless:
    1. You know the files are not too many.
    2. The user specifically requests it.
    3. You provide a jq filter to limit results (e.g. isGenerated field).

    The core principle is to fetch as much relevant metadata as possible in a single operation, rather than file contents.
    Before answering, make sure you've viewed the raw file on GitHub that resolves the user's request, and you should proactively provide the deep link to the code.
    """

    cmd = ["gh", "api", "graphql", "--input", "-"]

    if jq:
        cmd.extend(["--jq", jq])

    ret: CompletedProcess = ...  # type: ignore

    for _ in range(3):  # Retry up to 3 times on network issues
        ret = run(cmd, input=dumps({"query": query}, ensure_ascii=False), capture_output=True, text=True, encoding="utf-8")
        if ret.returncode == 4:
            raise ToolError("[[ No GitHub credentials found. Please log in to gh CLI or provide --token parameter when starting this MCP server! ]]")
        if ret.returncode < 2:
            is_error = ret.returncode == 1
            break
    else:
        msg = f"gh returned non-zero exit code {ret.returncode}"
        raise ToolError(f"{msg}:\n{details}" if (details := ret.stdout or ret.stderr) else msg)

    result = ret.stdout or ret.stderr or ""

    if not result.strip():
        raise ToolError("[[ The response is empty. Please adjust your query and try again! ]]")

    result = result.replace("\r\n", "\n")

    with suppress(JSONDecodeError):
        data = loads(result)

        if is_error:
            raise ToolError(readable_yaml_dumps(data))
        return readable_yaml_dumps(data)

    return result


@mcp.tool(title="GitHub Code Search")
def github_code_search(
    code_snippet: str = Field(description="Not a fuzzy search. Grep exact code snippet you want to find. Modifiers or wildcards not supported."),
    extension: str = Field(default_factory=str),
    filename: str = Field(default_factory=str),
    owner: list[str] = Field(default_factory=list),
    repo: list[str] = Field(default_factory=list, description="Format: owner/repo"),
    language: str = Field(default_factory=str),
    match_type: Literal["content", "path"] = "content",
):
    """
    Search files on GitHub with code snippets.

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

    ret: CompletedProcess = ...  # type: ignore
    for _ in range(3):  # Retry up to 3 times on network issues
        ret = run(cmd, capture_output=True, text=True, encoding="utf-8")
        if ret.returncode == 4:
            raise ToolError("[[ No GitHub credentials found. Please log in to gh CLI or provide --token parameter when starting this MCP server! ]]")
        if ret.returncode < 2:
            is_error = ret.returncode == 1
            break
    else:
        msg = f"gh returned non-zero exit code {ret.returncode}"
        raise ToolError(f"{msg}:\n{details}" if (details := ret.stdout or ret.stderr) else msg)

    if is_error:
        raise ToolError(ret.stdout or ret.stderr or "[[ An unknown error occurred during the code search. ]]")

    if match_type == "path":
        return ret.stdout or ret.stderr

    assert ret.stdout is not None

    data = loads(ret.stdout)
    for item in data:
        item["fragments"] = [i["fragment"] for i in item.pop("textMatches")]

    return readable_yaml_dumps(data)
