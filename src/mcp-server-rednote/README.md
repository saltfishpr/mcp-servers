# RedNote MCP Server

## Usage

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

## Debugging

```shell
npx @modelcontextprotocol/inspector uv run mcp-server-rednote
```