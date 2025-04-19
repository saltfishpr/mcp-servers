import argparse
import asyncio
import logging

from playwright.async_api import async_playwright

from .rednote import RedNote
from .server import serve

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s -%(filename)s:%(lineno)d - %(message)s",
)


def main():
    """Main entry point for the package."""
    parser = argparse.ArgumentParser(description="RedNote MCP Server")
    parser.add_argument(
        "--state_path",
        default="~/.mcp/rednote/state.json",
        help="Path to the browser state file",
    )
    args = parser.parse_args()
    asyncio.run(async_main(args.state_path))


async def async_main(storage_state_path: str) -> None:
    async with async_playwright() as p:
        async with RedNote(
            p, headless=False, storage_state_path=storage_state_path
        ) as rednote:
            await serve(rednote)


if __name__ == "__main__":
    main()
