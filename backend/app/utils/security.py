import ipaddress
import dns.resolver
from urllib.parse import urlparse
from app.config import Config

def is_private_ip(ip_str):
    try:
        ip = ipaddress.ip_address(ip_str)
        return ip.is_private or ip.is_loopback or ip.is_multicast or ip.is_unspecified
    except ValueError:
        return False

def resolve_hostname(hostname):
    try:
        answers = dns.resolver.resolve(hostname, 'A', timeout=Config.DNS_TIMEOUT)
        return [str(r) for r in answers]
    except:
        return []

def validate_target(target):
    target = target.strip()
    if not target:
        raise ValueError("Empty target")
    if '://' not in target:
        target = 'http://' + target
    parsed = urlparse(target)
    if parsed.scheme not in ('http', 'https'):
        raise ValueError("Only HTTP/HTTPS allowed")
    host = parsed.hostname
    if not host:
        raise ValueError("Invalid hostname")
    ips = resolve_hostname(host)
    if not ips:
        raise ValueError("Could not resolve hostname")
    for ip in ips:
        if is_private_ip(ip):
            raise ValueError("Private IP addresses are not allowed")
    if host in ('localhost', 'localhost.localdomain', '::1'):
        raise ValueError("Localhost not allowed")
    return target, host, parsed.port or (443 if parsed.scheme == 'https' else 80)