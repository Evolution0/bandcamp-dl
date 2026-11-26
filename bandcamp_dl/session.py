"""The requests session every Bandcamp request goes through

Kept in one place so the downloader and the parser cannot end up talking to Bandcamp
with different TLS settings.
"""

import requests
from requests.adapters import HTTPAdapter
from requests_ratelimiter import LimiterAdapter
from urllib3.util import create_urllib3_context

# Create the SSL context with the custom ciphers
ctx = create_urllib3_context()
ctx.load_default_certs()

DEFAULT_CIPHERS = ":".join(
    [
        "ECDHE+AESGCM",
        "ECDHE+CHACHA20",
        "DHE+AESGCM",
        "DHE+CHACHA20",
        "ECDH+AESGCM",
        "DH+AESGCM",
        "ECDH+AES",
        "DH+AES",
        "RSA+AESGCM",
        "RSA+AES",
        "!aNULL",
        "!eNULL",
        "!MD5",
        "!DSS",
        "!AESCCM",
    ]
)
ctx.set_ciphers(DEFAULT_CIPHERS)


class SSLContextMixin:
    """Injects our SSL context into the adapter's connection pools

    Mixed into both adapters: mounting two adapters on the same 'https://' prefix replaces
    the first one, so rate limiting used to silently drop the custom ciphers.
    """

    def __init__(self, ssl_context=None, **kwargs):
        self.ssl_context = ssl_context
        super().__init__(**kwargs)

    def init_poolmanager(self, *args, **kwargs):
        if self.ssl_context is not None:
            kwargs['ssl_context'] = self.ssl_context
        return super().init_poolmanager(*args, **kwargs)

    def proxy_manager_for(self, *args, **kwargs):
        if self.ssl_context is not None:
            kwargs['ssl_context'] = self.ssl_context
        return super().proxy_manager_for(*args, **kwargs)


class SSLAdapter(SSLContextMixin, HTTPAdapter):
    """Plain adapter that uses our custom SSL context"""


class RateLimitedSSLAdapter(SSLContextMixin, LimiterAdapter):
    """Rate limiting adapter that also keeps our custom SSL context"""


def make_session(limit_req_per_minute: int = 0) -> requests.Session:
    """Build a session that speaks to Bandcamp with our SSL context

    :param limit_req_per_minute: cap on requests per minute, 0 for no limit
    :return: a requests.Session with the matching adapter mounted on https://
    """
    session = requests.Session()
    if 0 < limit_req_per_minute:
        session.mount('https://', RateLimitedSSLAdapter(ssl_context=ctx,
                                                        per_minute=limit_req_per_minute))
    else:
        session.mount('https://', SSLAdapter(ssl_context=ctx))
    return session
