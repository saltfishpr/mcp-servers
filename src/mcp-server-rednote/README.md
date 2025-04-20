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
        "rednote": {
            "command": "uv",
            "args": [
                "--directory",
                "/<path to mcp-servers folder>",
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
