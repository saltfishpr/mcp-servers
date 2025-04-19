# RedNote MCP Server

## Tools

- check login status
- login
- search notes

## Usage

```json
{
    "mcpServers": {
        "git": {
            "command": "uvx",
            "args": [
                "mcp-server-rednote"
            ]
        }
    }
}
```

## Debugging

```shell
git clone https://github.com/saltfishpr/mcp-servers.git
```

```json
{
    "mcpServers": {
        "git": {
            "command": "uv",
            "args": [
                "--directory",
                "/<path to mcp-servers git repo>",
                "run",
                "mcp-server-rednote"
            ]
        }
    }
}
```

or

```shell
npx @modelcontextprotocol/inspector uv run mcp-server-rednote
```
