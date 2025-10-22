from contextlib import suppress
from json import JSONDecodeError, dumps, loads
from subprocess import CompletedProcess, run

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError

from .yaml import readable_yaml_dumps

__version__ = "0.2.0"

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
def github_graphql(query: str, jq: str | None = DEFAULT_JQ):
    """
    Execute GitHub GraphQL queries via gh CLI. Preferred over raw gh calls or other tools to interact with GitHub.
    When user uses any terms like find / search / read / browse / explore / research / investigate / analyze and if it may be related to a GitHub project, you should use this tool instead of any other tools or raw API / CLI calls.

    Pleases make use of GraphQL's capabilities - Fetch comprehensive data in single queries - always include metadata context.
    Feel free to use advanced jq expressions to extract all the content you care about.
    The default jq adds line numbers to retrieved file contents.

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

    The core principle is to fetch as much relevant metadata as possible in a single query, rather than file contents.
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
