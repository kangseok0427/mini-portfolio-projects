import ipaddress
import os
import socket
import time
from urllib.parse import urlsplit, urljoin
from urllib.robotparser import RobotFileParser
import httpx

USER_AGENT = "PortfolioProductCollector/1.0"


class PublicFetcher:
    """Allowlisted public HTTP only; obey robots and never bypass login/blocks."""

    def __init__(self):
        self.hosts = {
            s.strip().lower()
            for s in os.getenv("ALLOWED_HOSTS", "books.toscrape.com").split(",")
            if s.strip()
        }
        self.timeout = float(os.getenv("REQUEST_TIMEOUT", "10"))
        self.delay = max(0.2, float(os.getenv("REQUEST_DELAY", "0.5")))
        self.robots = {}
        self.last_request = 0.0

    def validate(self, url):
        p = urlsplit(url)
        if p.scheme not in {"https", "http"} or p.username or p.password:
            raise ValueError("공개 HTTP(S) URL만 사용할 수 있습니다")
        if p.hostname not in self.hosts or p.port not in {None, 80, 443}:
            raise ValueError(
                "승인된 도메인이 아닙니다. ALLOWED_HOSTS 설정을 확인하세요"
            )
        try:
            addresses = socket.getaddrinfo(
                p.hostname,
                p.port or (443 if p.scheme == "https" else 80),
                type=socket.SOCK_STREAM,
            )
        except socket.gaierror:
            # Some managed/proxy environments resolve DNS at the proxy. The
            # exact administrator-approved host allowlist remains mandatory.
            if not any(
                os.getenv(k)
                for k in ("HTTPS_PROXY", "HTTP_PROXY", "https_proxy", "http_proxy")
            ):
                raise
            addresses = []
        for address in addresses:
            if not ipaddress.ip_address(address[4][0]).is_global:
                raise ValueError("내부 네트워크 주소에는 접속하지 않습니다")
        return p

    def _request(self, url):
        for _ in range(4):
            self.validate(url)
            wait = self.delay - (time.monotonic() - self.last_request)
            if wait > 0:
                time.sleep(wait)
            with httpx.Client(timeout=self.timeout, follow_redirects=False) as client:
                with client.stream(
                    "GET", url, headers={"User-Agent": USER_AGENT}
                ) as response:
                    self.last_request = time.monotonic()
                    if response.status_code in {301, 302, 303, 307, 308}:
                        target = urljoin(url, response.headers.get("location", ""))
                        if (urlsplit(target).scheme, urlsplit(target).netloc) != (
                            urlsplit(url).scheme,
                            urlsplit(url).netloc,
                        ):
                            raise ValueError(
                                "다른 도메인으로 리다이렉트되어 수집을 중단했습니다"
                            )
                        origin = (
                            f"{urlsplit(target).scheme}://{urlsplit(target).netloc}"
                        )
                        if origin in self.robots and not self.robots[origin].can_fetch(
                            USER_AGENT, target
                        ):
                            raise ValueError(
                                "리다이렉트 경로의 수집이 허용되지 않습니다"
                            )
                        url = target
                        continue
                    chunks, size = [], 0
                    for chunk in response.iter_bytes():
                        size += len(chunk)
                        if size > 3_000_000:
                            raise ValueError("페이지가 너무 큽니다")
                        chunks.append(chunk)
                    return (
                        response.status_code,
                        b"".join(chunks).decode("utf-8", errors="replace"),
                        url,
                    )
        raise ValueError("리다이렉트가 너무 많습니다")

    def fetch(self, url):
        p = self.validate(url)
        origin = f"{p.scheme}://{p.netloc}"
        if origin not in self.robots:
            code, body, _ = self._request(origin + "/robots.txt")
            robot = RobotFileParser()
            if code == 404:
                robot.parse(["User-agent: *", "Allow: /"])
            elif code == 200:
                robot.parse(body.splitlines())
            else:
                raise ValueError(f"robots.txt 접근 실패 ({code}); 수집을 중단했습니다")
            self.robots[origin] = robot
        if not self.robots[origin].can_fetch(USER_AGENT, url):
            raise ValueError("robots.txt에서 수집을 허용하지 않습니다")
        code, body, final = self._request(url)
        if code != 200:
            raise ValueError(f"HTTP {code}: 해당 페이지는 건너뜁니다")
        return body, final
