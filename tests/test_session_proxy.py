from bandcamp_dl.session import SSLAdapter, ctx


def test_pools_behind_a_proxy_keep_the_custom_ciphers():
    # A proxy manager is a separate pool manager: without the mixin an HTTPS proxy would
    # negotiate Bandcamp's TLS with urllib3's default ciphers
    adapter = SSLAdapter(ssl_context=ctx)

    manager = adapter.proxy_manager_for("https://proxy.example")

    assert manager.connection_pool_kw["ssl_context"] is ctx


def test_a_plain_adapter_leaves_the_context_to_requests():
    adapter = SSLAdapter()

    assert adapter.proxy_manager_for("https://proxy.example").connection_pool_kw.get(
        "ssl_context") is None
    adapter.init_poolmanager(1, 1, block=False)
    assert adapter.poolmanager.connection_pool_kw.get("ssl_context") is None
