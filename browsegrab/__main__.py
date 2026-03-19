"""CLI entry point for browsegrab."""

from __future__ import annotations

import asyncio
import json
import sys

try:
    import click
except ImportError:
    print("CLI requires: pip install browsegrab[cli]", file=sys.stderr)
    sys.exit(1)

from browsegrab import BrowseGrabConfig, BrowseSession, __version__


@click.group()
@click.version_option(__version__, prog_name="browsegrab")
def main():
    """browsegrab — Token-efficient browser agent for local LLMs."""


@main.command()
@click.argument("url")
@click.option("--format", "-f", "fmt", type=click.Choice(["tree", "text", "json"]), default="tree", help="Output format")
@click.option("--interactive-only", "-i", is_flag=True, help="Show only interactive elements")
def snapshot(url: str, fmt: str, interactive_only: bool):
    """Take an accessibility tree snapshot of a URL."""
    config = BrowseGrabConfig.from_env()
    config.snapshot.filter_interactive_only = interactive_only

    async def _run():
        async with BrowseSession(config) as session:
            await session.navigate(url)
            snap = await session.snapshot()
            return snap

    try:
        snap = asyncio.run(_run())
    except KeyboardInterrupt:
        sys.exit(130)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)

    if fmt == "json":
        data = {
            "url": snap.url,
            "title": snap.title,
            "ref_count": snap.ref_count,
            "token_estimate": snap.token_estimate,
            "tree": snap.tree_text,
        }
        click.echo(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        click.echo(f"URL: {snap.url}")
        click.echo(f"Title: {snap.title}")
        click.echo(f"Interactive elements: {snap.ref_count}")
        click.echo(f"Estimated tokens: {snap.token_estimate}")
        click.echo("---")
        click.echo(snap.tree_text)


@main.command()
@click.argument("url")
@click.option("--scope", "-s", default=None, help="CSS selector to scope content extraction")
@click.option("--json-output", "-j", is_flag=True, help="Output as JSON")
def extract(url: str, scope: str | None, json_output: bool):
    """Extract page content as compressed DOM (AX tree + markdown)."""
    config = BrowseGrabConfig.from_env()

    async def _run():
        async with BrowseSession(config) as session:
            await session.navigate(url)
            return await session.extract_content(scope=scope)

    try:
        content = asyncio.run(_run())
    except KeyboardInterrupt:
        sys.exit(130)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)

    if json_output:
        click.echo(json.dumps({"content": content}, ensure_ascii=False, indent=2))
    else:
        click.echo(content)


@main.command()
@click.argument("url")
@click.argument("objective")
@click.option("--steps", "-n", type=int, default=None, help="Max steps (default: 10)")
@click.option("--json-output", "-j", is_flag=True, help="Output as JSON")
def browse(url: str, objective: str, steps: int | None, json_output: bool):
    """Agentic browse: LLM plans actions to achieve an objective."""
    config = BrowseGrabConfig.from_env()

    async def _run():
        async with BrowseSession(config) as session:
            return await session.browse(url, objective, max_steps=steps)

    try:
        result = asyncio.run(_run())
    except KeyboardInterrupt:
        sys.exit(130)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)

    if json_output:
        click.echo(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
    else:
        status = "OK" if result.success else "FAILED"
        click.echo(f"[{status}] {result.url}")
        click.echo(f"Steps: {result.total_steps} | Tokens: {result.total_tokens} | Time: {result.processing_time_ms:.0f}ms")
        if result.error:
            click.echo(f"Error: {result.error}")
        if result.content:
            click.echo("---")
            click.echo(result.content[:3000])


if __name__ == "__main__":
    main()
