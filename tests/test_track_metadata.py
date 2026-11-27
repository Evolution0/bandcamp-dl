from bandcamp_dl.bandcamp import Bandcamp


def track(**overrides):
    base = {"duration": 60.0, "track_num": 1, "title": "One", "artist": "Loopy",
            "title_link": "/album/first", "has_lyrics": False, "lyrics": None,
            "file": {"mp3-128": "https://t4.bcbits.com/stream/one"}}
    return {**base, **overrides}


def test_a_scheme_less_stream_url_gets_a_scheme():
    # Bandcamp hands out some stream urls without a scheme, which requests refuses to fetch
    metadata = Bandcamp().get_track_metadata(track(file={"mp3-128": "//t4.bcbits.com/stream/one"}))

    assert metadata["url"] == "http://t4.bcbits.com/stream/one"


def test_an_offered_format_that_is_not_mp3_128_has_no_url():
    only_flac = track(file={"flac": "https://t4.bcbits.com/stream/one"})

    assert Bandcamp().get_track_metadata(only_flac)["url"] is None


def test_the_stream_url_is_kept_as_it_is_when_it_is_absolute():
    absolute = track(file={"mp3-128": "https://t4.bcbits.com/stream/one"})

    assert Bandcamp().get_track_metadata(absolute)["url"] == "https://t4.bcbits.com/stream/one"


def test_literal_crlf_escapes_become_real_newlines():
    metadata = Bandcamp().get_track_metadata(
        track(has_lyrics=True, lyrics="first line\\r\\nsecond line"))

    assert metadata["lyrics"] == "first line\nsecond line"


def test_lyrics_only_land_on_a_track_that_declares_them():
    assert "lyrics" not in Bandcamp().get_track_metadata(track(has_lyrics=False, lyrics="ignored"))
    assert "lyrics" not in Bandcamp().get_track_metadata(track(has_lyrics=True, lyrics=None))
    assert Bandcamp().get_track_metadata(
        track(has_lyrics=True, lyrics="kept"))["lyrics"] == "kept"


def test_a_track_that_advertises_lyrics_never_fetched_has_no_key():
    # Without --embed-lyrics parse() no longer writes the key at all, and a release
    # that advertises lyrics used to be read as a missing key
    declared = track(has_lyrics=True)
    del declared["lyrics"]

    assert "lyrics" not in Bandcamp().get_track_metadata(declared)


def test_a_private_track_makes_the_album_incomplete():
    bandcamp = Bandcamp()

    bandcamp.tracks = [track(), track(file=None)]
    assert bandcamp.all_tracks_available() is False

    bandcamp.tracks = [track(), track()]
    assert bandcamp.all_tracks_available() is True


def test_the_album_url_is_built_from_the_artist_slug():
    assert Bandcamp.generate_album_url("loopy", "first", "album") == \
        "https://loopy.bandcamp.com/album/first"
