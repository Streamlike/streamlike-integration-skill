#!/usr/bin/env python3
"""Query the Streamlike OpenAPI descriptions without loading them into a context window.

The REST API description is around 2.5 MB, which no agent should read whole. This tool answers the
questions that actually come up: which endpoints exist, what does one take, what does it return.

    openapi_lookup.py tags
    openapi_lookup.py list [--tag Medias] [--grep audio]
    openapi_lookup.py show /medias --method post
    openapi_lookup.py search "audio track"
    openapi_lookup.py fields /medias/{media_id}

Use --ws to query the webservices description instead of the API one. Files are downloaded to
./openapi/ on first use and reused afterwards; --refresh downloads them again.
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import urllib.request

SOURCES = {
    "api": ("https://api.streamlike.com/openapi.json", "openapi/api.json"),
    "ws": ("https://cdn.streamlike.com/openapi.json", "openapi/ws.json"),
}


def load(which, refresh=False):
    url, path = SOURCES[which]
    here = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(here, path)
    if refresh or not os.path.exists(path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        sys.stderr.write("downloading %s\n" % url)
        download(url, path)
    with open(path, "rb") as handle:
        return json.load(handle)


def download(url, path):
    """Fetch a URL to a file, falling back to curl when Python has no CA bundle."""
    try:
        with urllib.request.urlopen(url, timeout=120) as response:
            data = response.read()
        with open(path, "wb") as handle:
            handle.write(data)
        return
    except Exception as error:  # noqa: BLE001 - any transport failure is worth the fallback
        if not shutil.which("curl"):
            raise
        sys.stderr.write("python download failed (%s), retrying with curl\n" % error)
    subprocess.run(["curl", "-fsSL", url, "-o", path], check=True)


def operations(spec):
    for path, methods in sorted(spec.get("paths", {}).items()):
        for method, operation in methods.items():
            if isinstance(operation, dict):
                yield path, method.upper(), operation


def first_line(text):
    return (text or "").strip().split("\n")[0]


def cmd_tags(spec, _args):
    counts = {}
    for _path, _method, operation in operations(spec):
        for tag in operation.get("tags") or ["(untagged)"]:
            counts[tag] = counts.get(tag, 0) + 1
    for tag in sorted(counts):
        print("%-24s %d" % (tag, counts[tag]))


def cmd_list(spec, args):
    for path, method, operation in operations(spec):
        tags = operation.get("tags") or []
        if args.tag and args.tag.lower() not in [t.lower() for t in tags]:
            continue
        line = "%-6s %-52s %s" % (method, path, first_line(operation.get("summary")))
        if args.grep and args.grep.lower() not in line.lower():
            continue
        print(line)


def cmd_search(spec, args):
    needle = args.term.lower()
    for path, method, operation in operations(spec):
        haystack = " ".join([
            path,
            operation.get("summary") or "",
            operation.get("description") or "",
            " ".join(p.get("name", "") for p in operation.get("parameters") or []),
        ]).lower()
        if needle in haystack:
            print("%-6s %-52s %s" % (method, path, first_line(operation.get("summary"))))


def cmd_show(spec, args):
    methods = spec.get("paths", {}).get(args.path)
    if not methods:
        hint = [seg for seg in args.path.split('/') if seg and not seg.startswith('{')]
        sys.exit("unknown path: %s (try: search %s)" % (args.path, hint[-1] if hint else args.path))
    for method, operation in methods.items():
        if not isinstance(operation, dict):
            continue
        if args.method and method.lower() != args.method.lower():
            continue
        print("=" * 78)
        print("%s %s   [%s]" % (method.upper(), args.path, ", ".join(operation.get("tags") or [])))
        print("=" * 78)
        # The summary is usually the truncated first line of the description; print the richer one.
        summary = (operation.get("summary") or "").strip()
        description = (operation.get("description") or "").strip()
        print(description[: args.max_description] if description else summary)
        params = operation.get("parameters") or []
        path_params = [p for p in params if p.get("in") == "path"]
        other_params = [p for p in params if p.get("in") != "path"]
        writes = method.lower() in ("post", "patch", "put")

        def dump(title, items):
            if not items:
                return
            print()
            print(title)
            for param in items:
                schema = param.get("schema") or {}
                kind = schema.get("type", "")
                if kind == "array":
                    kind = "array[]"
                flag = "required" if param.get("required") else ""
                print("  %-28s %-10s %-9s %s" % (
                    param.get("name"), kind, flag,
                    first_line(param.get("description"))[:80]))

        dump("URL parameters:", path_params)
        dump("Body fields (JSON payload, or the multipart 'resource' part when files are sent):"
             if writes else "Query parameters:", other_params)
        responses = operation.get("responses") or {}
        if responses:
            print()
            print("Responses:")
            for code in sorted(responses):
                print("  %-5s %s" % (code, first_line(responses[code].get("description"))))


def cmd_fields(spec, args):
    methods = spec.get("paths", {}).get(args.path)
    if not methods:
        sys.exit("unknown path: %s" % args.path)
    method = args.method or ("get" if "get" in methods else list(methods)[0])
    operation = methods.get(method.lower())
    if not operation:
        sys.exit("no %s on %s" % (method, args.path))
    for code, response in sorted((operation.get("responses") or {}).items()):
        schema = (response.get("content", {})
                  .get("application/json", {})
                  .get("schema", {}))
        props = schema.get("properties") or {}
        if not props:
            continue
        print("--- %s %s" % (code, first_line(response.get("description"))))
        for name in sorted(props):
            prop = props[name] or {}
            print("  %-46s %-8s %s" % (
                name, prop.get("type", ""), first_line(prop.get("description"))[:60]))


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--ws", action="store_true", help="query the webservices description")
    parser.add_argument("--refresh", action="store_true", help="re-download the description")
    parser.add_argument("--max-description", type=int, default=4000)
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("tags").set_defaults(func=cmd_tags)

    p_list = sub.add_parser("list")
    p_list.add_argument("--tag")
    p_list.add_argument("--grep")
    p_list.set_defaults(func=cmd_list)

    p_search = sub.add_parser("search")
    p_search.add_argument("term")
    p_search.set_defaults(func=cmd_search)

    p_show = sub.add_parser("show")
    p_show.add_argument("path")
    p_show.add_argument("--method")
    p_show.set_defaults(func=cmd_show)

    p_fields = sub.add_parser("fields")
    p_fields.add_argument("path")
    p_fields.add_argument("--method")
    p_fields.set_defaults(func=cmd_fields)

    args = parser.parse_args()
    spec = load("ws" if args.ws else "api", refresh=args.refresh)
    args.func(spec, args)


if __name__ == "__main__":
    main()
