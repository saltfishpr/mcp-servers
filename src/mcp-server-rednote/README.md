# RedNote MCP Server

## Configuration

```json
{
    "mcpServers": {
        "git": {
            "command": "uv",
            "args": [
                "run",
                "mcp-server-rednote"
            ]
        }
    }
}
```

## Debugging

```shell
npx @modelcontextprotocol/inspector uv run mcp-server-rednote
```