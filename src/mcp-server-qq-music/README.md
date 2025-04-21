# QQ Music MCP Server

## Tools

- check login status
- login
- search songs
- get song detail

## Usage

```json
{
    "mcpServers": {
        "qq-music": {
            "command": "uvx",
            "args": [
                "mcp-server-qq-music"
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
        "qq-music": {
            "command": "uv",
            "args": [
                "--directory",
                "/<path to mcp-servers folder>",
                "run",
                "mcp-server-qq-music"
            ]
        }
    }
}
```

or

```shell
npx @modelcontextprotocol/inspector uv run mcp-server-qq-music
```
