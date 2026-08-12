#!/usr/bin/env python3
"""Run read-only layered diagnostics for CC Switch HTTP/SOCKS/WS routing."""

from __future__ import annotations

import argparse
import base64
import json
import os
import socket
import ssl
import urllib.error
import urllib.parse
import urllib.request


def safe_url(value: str) -> str:
    parsed = urllib.parse.urlsplit(value)
    host = parsed.hostname or ""
    if parsed.port:
        host = f"{host}:{parsed.port}"
    return urllib.parse.urlunsplit((parsed.scheme, host, parsed.path, "", ""))


def endpoint(value: str) -> tuple[str, int]:
    parsed = urllib.parse.urlsplit(value)
    if not parsed.hostname:
        raise ValueError(f"Invalid endpoint: {safe_url(value)}")
    default = 443 if parsed.scheme in {"https", "wss"} else 80
    return parsed.hostname, parsed.port or default


def tcp_probe(name: str, value: str, timeout: float) -> dict:
    try:
        host, port = endpoint(value)
        with socket.create_connection((host, port), timeout=timeout):
            return {"layer": name, "target": safe_url(value), "reachable": True, "detail": f"TCP {host}:{port} connected"}
    except Exception as exc:
        return {"layer": name, "target": safe_url(value), "reachable": False, "detail": str(exc)}


def http_probe(url: str, proxy: str, timeout: float, layer: str) -> dict:
    handlers = []
    if proxy:
        handlers.append(urllib.request.ProxyHandler({"http": proxy, "https": proxy}))
    opener = urllib.request.build_opener(*handlers)
    request = urllib.request.Request(url, method="GET", headers={"User-Agent": "codex-ccswitch-diagnostic/1"})
    try:
        with opener.open(request, timeout=timeout) as response:
            body = response.read(512).decode("utf-8", errors="replace")
            return {"layer": layer, "target": safe_url(url), "reachable": True, "status": response.status, "detail": body[:240]}
    except urllib.error.HTTPError as exc:
        body = exc.read(512).decode("utf-8", errors="replace")
        return {"layer": layer, "target": safe_url(url), "reachable": True, "status": exc.code, "detail": body[:240]}
    except Exception as exc:
        return {"layer": layer, "target": safe_url(url), "reachable": False, "detail": str(exc)}


def recv_headers(sock: socket.socket) -> str:
    data = b""
    while b"\r\n\r\n" not in data and len(data) < 16384:
        chunk = sock.recv(2048)
        if not chunk:
            break
        data += chunk
    return data.decode("iso-8859-1", errors="replace")


def websocket_probe(url: str, http_proxy: str, timeout: float) -> dict:
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme not in {"ws", "wss"} or not parsed.hostname:
        return {"layer": "websocket", "target": safe_url(url), "reachable": False, "detail": "URL must use ws:// or wss://"}
    target_host, target_port = endpoint(url)
    path = parsed.path or "/"
    if parsed.query:
        path += f"?{parsed.query}"
    try:
        if http_proxy:
            proxy_host, proxy_port = endpoint(http_proxy)
            sock = socket.create_connection((proxy_host, proxy_port), timeout=timeout)
            if parsed.scheme == "wss":
                sock.sendall(f"CONNECT {target_host}:{target_port} HTTP/1.1\r\nHost: {target_host}:{target_port}\r\n\r\n".encode("ascii"))
                connect_reply = recv_headers(sock)
                if " 200 " not in connect_reply.split("\r\n", 1)[0]:
                    raise RuntimeError(f"proxy CONNECT failed: {connect_reply.splitlines()[0] if connect_reply else 'empty response'}")
                sock = ssl.create_default_context().wrap_socket(sock, server_hostname=target_host)
            request_target = path if parsed.scheme == "wss" else url
        else:
            sock = socket.create_connection((target_host, target_port), timeout=timeout)
            if parsed.scheme == "wss":
                sock = ssl.create_default_context().wrap_socket(sock, server_hostname=target_host)
            request_target = path
        with sock:
            key = base64.b64encode(os.urandom(16)).decode("ascii")
            request = (
                f"GET {request_target} HTTP/1.1\r\n"
                f"Host: {target_host}:{target_port}\r\n"
                "Upgrade: websocket\r\nConnection: Upgrade\r\n"
                f"Sec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n"
            )
            sock.sendall(request.encode("ascii"))
            response = recv_headers(sock)
        status_line = response.split("\r\n", 1)[0] if response else "empty response"
        return {"layer": "websocket", "target": safe_url(url), "reachable": status_line.startswith("HTTP/1.1 101") or status_line.startswith("HTTP/1.0 101"), "status_line": status_line, "detail": "upgrade accepted" if " 101 " in status_line else "endpoint reached but upgrade was not accepted"}
    except Exception as exc:
        return {"layer": "websocket", "target": safe_url(url), "reachable": False, "detail": str(exc)}


def classify_error(text: str) -> dict | None:
    normalized = text.lower()
    if "unsupported_country_region_territory" in normalized or "country, region, or territory not supported" in normalized:
        return {"layer": "oauth", "classification": "unsupported_region", "detail": "OAuth endpoint rejected the observed exit region; verify which process is using which proxy."}
    if "403" in normalized and "forbidden" in normalized:
        return {"layer": "oauth", "classification": "forbidden", "detail": "Request reached the service but was rejected; inspect region, account policy, and endpoint support."}
    if "websocket closed" in normalized or "stream disconnected before completion" in normalized:
        return {"layer": "websocket", "classification": "stream_closed", "detail": "Test the exact WS endpoint and proxy upgrade/tunnel support."}
    return {"layer": "error", "classification": "unrecognized", "detail": "No known CC Switch/OAuth/WS signature found."}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--http-proxy", default="")
    parser.add_argument("--socks-proxy", default="")
    parser.add_argument("--api-base", default="")
    parser.add_argument("--ws-url", default="")
    parser.add_argument("--region-url", default="")
    parser.add_argument("--error-text", default="")
    parser.add_argument("--timeout", type=float, default=5.0)
    args = parser.parse_args()
    results = []
    if args.http_proxy:
        results.append(tcp_probe("http_proxy", args.http_proxy, args.timeout))
    if args.socks_proxy:
        item = tcp_probe("socks_proxy", args.socks_proxy, args.timeout)
        item["detail"] += "; TCP only, application SOCKS5/DNS behavior still requires a client test"
        results.append(item)
    if args.api_base:
        results.append(http_probe(args.api_base, args.http_proxy, args.timeout, "responses_api"))
    if args.ws_url:
        results.append(websocket_probe(args.ws_url, args.http_proxy, args.timeout))
    if args.region_url:
        results.append(http_probe(args.region_url, args.http_proxy, args.timeout, "exit_region"))
    if args.error_text:
        results.append(classify_error(args.error_text))
    if not results:
        parser.error("provide at least one proxy, API, WS, region, or error-text input")
    print(json.dumps(results, ensure_ascii=False, indent=2))
    return 0 if all(item.get("reachable", True) for item in results) else 2


if __name__ == "__main__":
    raise SystemExit(main())
