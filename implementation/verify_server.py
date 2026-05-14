"""End-to-end smoke test against the running FastMCP HTTP server.

Run the server first (e.g. `docker compose up`), then:

    python implementation/verify_server.py [--url http://localhost:8000/mcp]
"""

from __future__ import annotations

import argparse
import asyncio
import sys

from fastmcp import Client


async def run(url: str) -> int:
    failures: list[str] = []

    def check(name: str, ok: bool, detail: str = "") -> None:
        mark = "PASS" if ok else "FAIL"
        print(f"[{mark}] {name}" + (f" — {detail}" if detail else ""))
        if not ok:
            failures.append(name)

    async with Client(url) as client:
        tools = await client.list_tools()
        tool_names = {t.name for t in tools}
        check(
            "tool discovery",
            {"search", "insert", "aggregate"}.issubset(tool_names),
            f"found {sorted(tool_names)}",
        )

        resources = await client.list_resources()
        resource_uris = {str(r.uri) for r in resources}
        check(
            "schema://database resource exposed",
            any(u.startswith("schema://database") for u in resource_uris),
            f"resources={sorted(resource_uris)}",
        )

        try:
            templates = await client.list_resource_templates()
            template_uris = {t.uriTemplate for t in templates}
            check(
                "schema://table/{table_name} template exposed",
                any("schema://table/" in u for u in template_uris),
                f"templates={sorted(template_uris)}",
            )
        except Exception as e:  # older servers may not implement templates listing
            check("schema://table template exposed", False, f"error: {e}")

        r = await client.call_tool(
            "search",
            {
                "table": "students",
                "filters": [{"column": "cohort", "op": "=", "value": "A1"}],
                "order_by": "score",
                "descending": True,
            },
        )
        data = r.data if hasattr(r, "data") else r
        check(
            "search students cohort=A1",
            isinstance(data, dict) and data.get("count", 0) > 0,
            f"count={data.get('count') if isinstance(data, dict) else data}",
        )

        r = await client.call_tool(
            "insert",
            {
                "table": "students",
                "values": {"name": "Verify Bot", "cohort": "A1", "score": 7.0},
            },
        )
        data = r.data if hasattr(r, "data") else r
        check(
            "insert returns id",
            isinstance(data, dict) and isinstance(data.get("id"), int),
            f"id={data.get('id') if isinstance(data, dict) else data}",
        )

        r = await client.call_tool(
            "aggregate",
            {
                "table": "students",
                "metric": "avg",
                "column": "score",
                "group_by": "cohort",
            },
        )
        data = r.data if hasattr(r, "data") else r
        check(
            "aggregate avg score group by cohort",
            isinstance(data, dict) and len(data.get("rows", [])) >= 2,
            f"rows={data.get('rows') if isinstance(data, dict) else data}",
        )

        r = await client.read_resource("schema://database")
        text = r[0].text if r else ""
        check("read schema://database", "students" in text and "courses" in text)

        r = await client.read_resource("schema://table/students")
        text = r[0].text if r else ""
        check("read schema://table/students", "cohort" in text)

        r = await client.call_tool("search", {"table": "hackers"})
        data = r.data if hasattr(r, "data") else r
        check(
            "invalid table returns error",
            isinstance(data, dict) and "error" in data,
            f"got {data}",
        )

    print()
    if failures:
        print(f"{len(failures)} check(s) failed: {failures}")
        return 1
    print("All checks passed.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://localhost:8000/mcp")
    args = parser.parse_args()
    return asyncio.run(run(args.url))


if __name__ == "__main__":
    sys.exit(main())
