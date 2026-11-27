from types import SimpleNamespace

from bandcamp_dl.bandcampdownloader import BandcampDownloader
from bandcamp_dl.config import CASE_CAMEL, CASE_LOWER, CASE_NONE, CASE_UPPER

TEMPLATE = "%{artist}/%{album}/%{track} - %{title}"


def make_config(**overrides):
    values = dict(limit_req_per_minute=0, template=TEMPLATE, base_dir="out",
                  untitled_path_from_slug=False, no_slugify=False, truncate_album=0,
                  truncate_track=0, ascii_only=False, ok_chars="-_~", space_char="-",
                  keep_spaces=False, case_mode=CASE_LOWER, overwrite=False, debug=True,
                  embed_art=False, embed_genres=False, embed_lyrics=False, group=False,
                  no_confirm=True, retag=False, progress="auto")
    return SimpleNamespace(**{**values, **overrides})


def make_downloader(**overrides):
    return BandcampDownloader(make_config(**overrides), "https://loopy.bandcamp.com/album/first")


def track(**overrides):
    base = {"artist": "Loopy", "albumartist": "Big Band", "album": "First Mix",
            "title": "One Two", "date": "2026", "label": "Loopy Store", "track": "1",
            "album_id": "7", "track_id": "11",
            "url": "https://loopy.bandcamp.com/album/first"}
    return {**base, **overrides}


def path_for(downloader, track_dict, case_mode=CASE_LOWER):
    return downloader.template_to_path(track_dict, False, "-_~", "-", False, case_mode)


def test_case_lower_folds_every_name_to_lower_case():
    assert path_for(make_downloader(), track()) == "out/big-band/first-mix/01 - one-two.mp3"


def test_case_upper_upper_cases_the_text_before_slugifying_it():
    # Slugify lowercases the result, so the case choice has to be applied to the content first
    path = path_for(make_downloader(), track(), CASE_UPPER)

    assert path == "out/BIG-BAND/FIRST-MIX/01 - ONE-TWO.mp3"


def test_case_camel_capitalizes_each_word_after_the_separators():
    path = path_for(make_downloader(), track(), CASE_CAMEL)

    assert path == "out/Big-Band/First-Mix/01 - One-Two.mp3"


def test_case_none_keeps_the_case_bandcamp_published():
    path = path_for(make_downloader(), track(), CASE_NONE)

    assert path == "out/Big-Band/First-Mix/01 - One-Two.mp3"


def test_no_slugify_leaves_the_spaces_and_punctuation_in_the_name():
    path = path_for(make_downloader(no_slugify=True), track())

    assert path == "out/Big Band/First Mix/01 - One Two.mp3"


def test_a_track_without_an_artist_is_filed_under_the_album_artist():
    # A private-pressing track carries no artist; the path used to end up with the album
    # artist missing and a literal None left in it
    path = path_for(make_downloader(), track(artist=None))

    assert path == "out/big-band/first-mix/01 - one-two.mp3"


def test_a_single_without_a_number_is_called_single():
    assert path_for(make_downloader(), track(track="None")).endswith("single - one-two.mp3")


def test_an_untitled_album_can_take_its_folder_from_the_url_slug():
    downloader = make_downloader(untitled_path_from_slug=True)

    path = path_for(downloader, track(album="Untitled",
                                      url="https://loopy.bandcamp.com/album/some-odd-title"))

    assert "some-odd-title" in path
    assert "untitled" not in path


def test_a_token_the_track_does_not_carry_replaces_with_an_empty_string():
    tokenless = {key: value for key, value in track().items() if key != "label"}

    assert path_for(make_downloader(template="%{label}/%{title}"),
                    tokenless) == "out//one-two.mp3"


def test_a_token_set_to_none_replaces_with_an_empty_string_too():
    # Most releases have no seller entry, so label arrives as None; the folder used to be
    # named "none", or "None" with --no-slugify
    downloader = make_downloader(template="%{label}/%{title}")

    assert path_for(downloader, track(label=None)) == "out//one-two.mp3"
    assert path_for(make_downloader(template="%{label}/%{title}", no_slugify=True),
                    track(label=None)) == "out//One Two.mp3"


def test_the_integer_ids_parse_publishes_survive_the_case_options():
    # parse() reports album_id/track_id as ints, and upper/camel called str methods on them
    downloader = make_downloader(template="%{album}/%{album_id}/%{track_id}")

    assert path_for(downloader, track(album_id=7, track_id=11), CASE_UPPER) == "out/FIRST-MIX/7/11.mp3"
    assert path_for(downloader, track(album_id=7, track_id=11), CASE_CAMEL) == "out/First-Mix/7/11.mp3"


def test_a_cached_slug_cannot_leak_another_case_mode():
    # The slug of a value is kept for the whole run, so the case mode is part of the key:
    # one downloader asked twice must not answer the second call with the first result
    downloader = make_downloader()

    assert path_for(downloader, track(), CASE_LOWER).endswith("01 - one-two.mp3")
    assert path_for(downloader, track(), CASE_UPPER).endswith("01 - ONE-TWO.mp3")


def test_no_base_dir_still_ends_in_an_mp3_file():
    # base_dir None leaves the file in the current directory; only the directory part goes
    path = make_downloader(base_dir=None).template_to_path(track(), False, "-_~", "-", False,
                                                           CASE_LOWER)

    assert path == "big-band/first-mix/01 - one-two.mp3"
