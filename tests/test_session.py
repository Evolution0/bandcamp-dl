from bandcamp_dl.session import SSLAdapter, RateLimitedSSLAdapter, ctx, make_session


def test_the_custom_ssl_context_survives_rate_limiting():
    # Mounting two adapters on 'https://' replaces the first one, so the rate limiter has
    # to carry the SSL context itself instead of being mounted over it
    for limit in (0, 10):
        adapter = make_session(limit_req_per_minute=limit).get_adapter("https://bandcamp.com/")
        assert adapter.ssl_context is ctx


def test_only_limited_sessions_rate_limit():
    assert not isinstance(make_session(0).get_adapter("https://bandcamp.com/"),
                          RateLimitedSSLAdapter)
    assert isinstance(make_session(5).get_adapter("https://bandcamp.com/"),
                      RateLimitedSSLAdapter)


def test_both_adapters_build_their_pools_with_the_custom_context():
    adapters = [SSLAdapter(ssl_context=ctx),
                RateLimitedSSLAdapter(ssl_context=ctx, per_minute=10)]
    for adapter in adapters:
        adapter.init_poolmanager(1, 1, block=False)
        assert adapter.poolmanager.connection_pool_kw['ssl_context'] is ctx
