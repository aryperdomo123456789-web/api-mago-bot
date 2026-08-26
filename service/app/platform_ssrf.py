from __future__ import annotations

import socket
from ipaddress import ip_address
from urllib.parse import urlparse


class UnsafeWebhookEndpoint(ValueError):
    """Endpoint não comprovadamente público ou não permitido pela política."""


_BLOCKED_HOSTS = {
    "localhost",
    "localhost.localdomain",
    "metadata.google.internal",
    "metadata",
    "instance-data.ec2.internal",
}


def _resolved_addresses(hostname: str) -> set[str]:
    try:
        records = socket.getaddrinfo(hostname, None, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise UnsafeWebhookEndpoint("webhook host could not be resolved") from exc
    addresses = {record[4][0] for record in records if record[4]}
    if not addresses:
        raise UnsafeWebhookEndpoint("webhook host has no address")
    return addresses


def validate_webhook_endpoint(endpoint_url: str) -> str:
    """Valida URL e resolve DNS no momento da operação.

    A validação é repetida no worker antes de cada delivery para reduzir o risco de
    DNS rebinding e impedir alvos privados, link-local e metadata services.
    """
    parsed = urlparse(endpoint_url.strip())
    hostname = (parsed.hostname or "").lower().rstrip(".")
    if parsed.scheme != "https" or not hostname:
        raise UnsafeWebhookEndpoint("webhook endpoint must use HTTPS with a hostname")
    if parsed.username or parsed.password or parsed.fragment:
        raise UnsafeWebhookEndpoint("webhook endpoint cannot contain credentials or fragment")
    if hostname in _BLOCKED_HOSTS or hostname.endswith((".local", ".internal", ".localhost")):
        raise UnsafeWebhookEndpoint("webhook endpoint hostname is not public")
    if parsed.port not in (None, 443):
        raise UnsafeWebhookEndpoint("webhook endpoint must use port 443")

    try:
        literal = ip_address(hostname)
        addresses = {str(literal)}
    except ValueError:
        addresses = _resolved_addresses(hostname)

    for address in addresses:
        parsed_address = ip_address(address)
        if not parsed_address.is_global:
            raise UnsafeWebhookEndpoint("webhook endpoint resolves to a non-public address")
    return endpoint_url.strip()
