import socket
import requests
import dns.resolver
import os
from urllib.parse import urlparse
from datetime import datetime
import time

from app.config import Config
from app.utils.security import validate_target, is_private_ip

VT_API_KEY = os.environ.get('VT_API_KEY', '')

# Common ports
COMMON_PORTS = [
    21, 22, 23, 25, 53, 80, 110, 135, 139, 143, 443, 445,
    465, 587, 993, 995, 1433, 3306, 3389
]

def dns_lookup(host):
    records = {}
    for qtype in ['A', 'AAAA', 'MX', 'NS', 'TXT']:
        try:
            answers = dns.resolver.resolve(host, qtype, timeout=Config.DNS_TIMEOUT)
            records[qtype] = [str(r) for r in answers]
        except:
            records[qtype] = []
    return records

def scan_common_ports(host):
    open_ports = []
    for port in COMMON_PORTS:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(Config.PORT_SCAN_TIMEOUT)
        result = sock.connect_ex((host, port))
        sock.close()
        if result == 0:
            open_ports.append(port)
    return open_ports

def get_http_info(host, scheme='https'):
    # We'll try both, but primarily use HTTPS
    info = {}
    for s in ['http', 'https']:
        url = f"{s}://{host}"
        try:
            # Use requests with redirect control
            session = requests.Session()
            # Set max redirects and validate each redirect
            session.max_redirects = Config.MAX_REDIRECTS
            resp = session.get(url, timeout=Config.REQUEST_TIMEOUT, allow_redirects=True)
            # Check final URL
            final_url = resp.url
            # Validate final URL (SSRF)
            try:
                validate_target(final_url)
            except ValueError:
                # If redirect leads to private IP, treat as error
                info[s] = {'error': 'Redirect to invalid target'}
                continue
            # Limit response size
            if len(resp.content) > Config.MAX_RESPONSE_SIZE:
                info[s] = {'error': 'Response too large'}
                continue
            info[s] = {
                'status_code': resp.status_code,
                'headers': dict(resp.headers),
                'final_url': final_url,
                'response_time': resp.elapsed.total_seconds()
            }
        except requests.exceptions.Timeout:
            info[s] = {'error': 'Timeout'}
        except Exception as e:
            info[s] = {'error': str(e)}
    return info

def check_url_safety(url):
    if not VT_API_KEY:
        return {'error': 'VirusTotal API key not set'}
    try:
        encoded = requests.utils.quote(url, safe='')
        resp = requests.get(
            f"https://www.virustotal.com/api/v3/urls/{encoded}",
            headers={"x-apikey": VT_API_KEY},
            timeout=Config.REQUEST_TIMEOUT
        )
        if resp.status_code == 200:
            data = resp.json()
            stats = data.get('data', {}).get('attributes', {}).get('last_analysis_stats', {})
            return {
                'malicious': stats.get('malicious', 0),
                'suspicious': stats.get('suspicious', 0),
                'total_vendors': sum(stats.values()),
                'is_safe': stats.get('malicious', 0) == 0 and stats.get('suspicious', 0) == 0
            }
        else:
            return {'error': 'VirusTotal API error (rate limit?)'}
    except Exception as e:
        return {'error': str(e)}

def compute_score(results):
    # Simplified scoring
    score = 0
    # Threat intelligence: 35%
    ti = results.get('safety_check', {})
    if ti.get('is_safe', False):
        score += 35
    elif ti.get('malicious', 0) == 0 and ti.get('suspicious', 0) > 0:
        score += 20
    else:
        score += 0
    # DNS: 15% (just presence of records)
    dns = results.get('dns', {})
    dns_score = 15 if any(dns.values()) else 0
    score += dns_score
    # Network Exposure: 25% (fewer open ports = better)
    ports = results.get('open_ports', [])
    # Penalize risky ports: 22, 23, 3306, 3389, etc.
    risky = [22, 23, 3306, 3389, 445, 135, 139]
    risky_open = sum(1 for p in ports if p in risky)
    net_score = max(0, 25 - risky_open * 5)
    score += net_score
    # HTTP: 25%
    http = results.get('http', {})
    http_score = 0
    for s in ['http', 'https']:
        if s in http and http[s] and isinstance(http[s], dict) and 'status_code' in http[s]:
            if 200 <= http[s]['status_code'] < 400:
                http_score += 12.5
            else:
                http_score += 0
    score += http_score
    return int(score)

def build_findings(results):
    findings = []
    # Threat findings
    ti = results.get('safety_check', {})
    if ti.get('malicious', 0) > 0:
        findings.append({
            'severity': 'Critical',
            'title': 'Malicious detection by threat intelligence',
            'detail': f"{ti['malicious']} vendors flagged this URL as malicious.",
            'evidence': 'VirusTotal detection',
            'recommendation': 'Do not visit this site; investigate further.'
        })
    elif ti.get('suspicious', 0) > 0:
        findings.append({
            'severity': 'High',
            'title': 'Suspicious activity reported',
            'detail': f"{ti['suspicious']} vendors flagged this URL as suspicious.",
            'evidence': 'VirusTotal detection',
            'recommendation': 'Review the site with caution; consider using a sandbox.'
        })
    # Network findings
    ports = results.get('open_ports', [])
    risky_ports = {22: 'SSH', 23: 'Telnet', 3306: 'MySQL', 3389: 'RDP', 445: 'SMB', 135: 'RPC', 139: 'NetBIOS'}
    for p in ports:
        if p in risky_ports:
            findings.append({
                'severity': 'High',
                'title': f'Exposed {risky_ports[p]} service',
                'detail': f"Port {p}/tcp is open and accessible externally.",
                'evidence': f'{p}/tcp',
                'recommendation': 'Restrict access to this service using a firewall and require authentication.'
            })
    # HTTP findings
    http = results.get('http', {})
    for s in ['http', 'https']:
        if s in http and http[s] and isinstance(http[s], dict):
            headers = http[s].get('headers', {})
            if 'strict-transport-security' not in headers:
                findings.append({
                    'severity': 'Medium',
                    'title': 'Missing HSTS header',
                    'detail': 'The site does not enforce HTTPS via HSTS.',
                    'evidence': 'HTTP response headers',
                    'recommendation': 'Add Strict-Transport-Security header to enforce secure connections.'
                })
            if 'content-security-policy' not in headers:
                findings.append({
                    'severity': 'Medium',
                    'title': 'Missing Content-Security-Policy',
                    'detail': 'The site does not protect against XSS with CSP.',
                    'evidence': 'HTTP response headers',
                    'recommendation': 'Implement a Content-Security-Policy header.'
                })
            if http[s].get('status_code', 0) >= 400:
                findings.append({
                    'severity': 'Low',
                    'title': f'HTTP {http[s]["status_code"]} error',
                    'detail': 'The server returned an error status.',
                    'evidence': f'{s}://{results.get("target")}',
                    'recommendation': 'Investigate the server configuration.'
                })
    # Limit to top 10
    return findings[:10]

def run_recon(target):
    # target already validated by the API
    # Remove protocol and get host
    parsed = urlparse(target if '://' in target else f'http://{target}')
    host = parsed.hostname
    url = target

    start_time = time.time()
    results = {
        'target': target,
        'safety_check': check_url_safety(url),
        'dns': dns_lookup(host),
        'open_ports': scan_common_ports(host),
        'http': get_http_info(host),
        'scan_duration': time.time() - start_time
    }
    # Compute score and findings
    results['score'] = compute_score(results)
    results['findings'] = build_findings(results)
    results['summary'] = 'No critical issues found.' if results['score'] >= 60 else 'Some security issues detected.'

    # Breakdown
    ti_score = 35 if results['safety_check'].get('is_safe', False) else 0
    dns_score = 15 if any(results['dns'].values()) else 0
    net_score = max(0, 25 - sum(1 for p in results['open_ports'] if p in [22,23,3306,3389,445,135,139])*5)
    http_score = 0
    for s in ['http', 'https']:
        if s in results['http'] and results['http'][s] and isinstance(results['http'][s], dict) and 'status_code' in results['http'][s]:
            if 200 <= results['http'][s]['status_code'] < 400:
                http_score += 12.5
    results['breakdown'] = {
        'Threat Intelligence': ti_score,
        'DNS Configuration': dns_score,
        'Network Exposure': net_score,
        'HTTP Security': http_score
    }

    return results