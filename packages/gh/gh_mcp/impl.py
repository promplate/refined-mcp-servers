from contextlib import suppress
from json import JSONDecodeError, dumps, loads
from subprocess import CompletedProcess, run

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError

from .yaml import readable_yaml_dumps

__version__ = "0.1.0"

mcp = FastMCP("gh", version=__version__, include_fastmcp_meta=False)

mcp.instructions = """
When interacting with GitHub, you should prefer this over any other tools or raw API / CLI calls.
For example, instead of browsing some page under github.com, you can fetch all relevant content via GraphQL in one go.
"""


@mcp.tool(title="GitHub GraphQL")
def github_graphql(query: str, jq: str | None = ".data", as_yaml: bool = True):
    """
    Execute GitHub GraphQL queries via gh CLI. Preferred over raw gh calls or other ways to interact with GitHub.
    Pleases make use of GraphQL's capabilities - Fetch comprehensive data in single queries - always include metadata context.
    Returns YAML by default for better readability. Use jq to extract specific fields.

    Before writing complex queries / mutations or when encountering errors, use introspection to understand available fields and types:
    ```graphql
    { __type(name: "Query") { fields(includeDeprecated: false) { name description type { name kind } args { name description type { name kind } } } } }
    ```

    > Example - when you need to browse multiple repositories:

    ```graphql
    query {
      hmr: repository(owner: "promplate", name: "hmr") {
        ...RepositoryMetadata
      }

      pythonline: repository(owner: "promplate", name: "pyth-on-line") {
        ...RepositoryMetadata
      }
    }

    fragment RepositoryMetadata on Repository {
      name
      description
      homepageUrl

      pushedAt
      createdAt
      updatedAt

      stargazerCount
      forkCount

      isPrivate
      isFork
      isArchived

      languages(first: 7) {
        totalSize
        edges {
          size
          node { name }
        }
      }

      readme_md: object(expression: "HEAD:README.md") { ... on Blob { text } }
      pyproject_toml: object(expression: "HEAD:pyproject.toml") { ... on Blob { text } }
      package_json: object(expression: "HEAD:package.json") { ... on Blob { text } }

      latestCommits: defaultBranchRef {
        target {
          ... on Commit {
            history(first: 7) {
              nodes {
                abbreviatedOid
                committedDate
                message
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

    > Example - when you need to browse repository files with metadata:

    ```graphql
    query {
      repository(owner: "promplate", name: "hmr") {
        files: object(expression: "HEAD:") {
          ... on Tree {
            entries {
              path # prefer this over `name` - full relative path
              type
              mode
              isGenerated
              object {
                ... on Blob {
                  text
                  isTruncated
                }
                ... on Tree {
                  entries {
                    path
                    type
                    mode
                    isGenerated
                    object {
                      ... on Blob {
                        text
                        isTruncated
                      }
                    }
                  }
                }
              }
            }
          }
        }
        # Get latest commit that touched root
        defaultBranchRef {
          target {
            ... on Commit {
              history(first: 1) {
                nodes {
                  abbreviatedOid
                  message
                  committedDate
                  author { name user { login } }
                }
              }
            }
          }
        }
      }
    }
    ```

    Filter non-generated files recursively at all depths with jq:
    ```bash
    --jq 'def filter_generated: if type == "array" then map(select(.isGenerated | not) | if .object.entries then .object.entries |= [.[] | filter_generated] else . end) else . end; .data.repository.files.entries | filter_generated'
    """

    cmd = ["gh", "api", "graphql", "--input", "-"]

    if jq:
        cmd.extend(["--jq", jq])

    ret: CompletedProcess = ...  # type: ignore

    for _ in range(3):  # Retry up to 3 times on network issues
        ret = run(cmd, input=dumps({"query": query}, ensure_ascii=False), capture_output=True, text=True, encoding="utf-8")
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

        if as_yaml:
            if is_error:
                raise ToolError(readable_yaml_dumps(data))
            return readable_yaml_dumps(data)

    return result
