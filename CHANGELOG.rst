Changelog:
==========

Version 0.0.5
-------------
- [Enhancement] ID3 Data Windows Explorer Compatibility. (Courtesy of
  `Bendito999 <https://github.com/Bendito999>`_)
- [Enhancement] Will now use lxml if available, it is not a requirement.
- [Bugfix] ``--base-dir`` will now create the specified directory rather
  than fail.
- [Enhancement] If a file is incomplete it will be redownloaded on next
  run.
- [Bugfix] Fixed
  `#62 <https://github.com/iheanyi/bandcamp-dl/issues/62>`_.
- [Dependency] Wgetter is no longer required.
- [Dependency] Latest versions of dependencies now used.

Version 0.0.6
-------------
- [Enhancement] Added the option to skip the downloading of album art.
- [Enhancement] Individual track downloads work now.
- [Bugfix] Fixed imports, now working when installed via pip.
- [Note] Last version to officially support Python 2.7.x
- [Bugfix] Fixed an encoding issue with accented characters in the
  filepath. (Thanks `oaubert <https://github.com/oaubert>`_)

Version 0.0.7
-------------
- [Enhancement] Will now resume if it finds a valid ``not.finished``
  file.
- [Enhancement] Interrupting downloads is safe, they will resume on next
  run.
- [Enhancement] Interrupting encoding is safe, it will finish on next
  run.
- [Enhancement] CLI output is now much neater.
- [Bugfix] Partial albums (some previews disabled) will now download
  properly.
- [Dependency] Slimit is no longer required.
- [Dependency] Ply is no longer required.
- [Dependency] demjson is now required.
- [Bugfix] Downloading singles is now fixed.
- [Bugfix] Monkey-patched Requests to fix compatability with Python
  versions before 3.6.
- [Enhancement] Added a --group option to insert a group tag (iTunes)

Version 0.0.8
-------------
- [Enhancement] --embed-art option to forcibly embed album art (if
  available)
- [Enhancement] --track option for downloading individual tracks and
  singles.

Unreleased
----------
- [Bugfix] Artists whose pages redirect forever between
  ``name.bandcamp.com`` and a broken custom domain (``TooManyRedirects``)
  now download through Bandcamp's mobile API instead. Lyrics are not
  available on this path.
- [Bugfix] That fallback finds the band behind a url on the band's own domain
  (``music.businesscasual.biz`` for instance) by following the redirects to its
  ``bandcamp.com`` subdomain, instead of taking the first label of the host as the
  band name, which looked such a band up as ``music`` and reported the release as
  missing. Playlist tracklists carry those custom domain urls, so playlists were
  the usual way to hit it.
- [Bugfix] An artist page on the band's own domain (``bandcamp-dl
  https://music.businesscasual.biz``) is now recognised as an artist page; it used
  to be dropped without a word because the host is not ``*.bandcamp.com``. A root
  page whose band cannot be found is reported and fails the run with exit code 1.
- [Enhancement] An HTTP 429 from Bandcamp is now explained instead of being swallowed
  by the retry loops: the run is making too many requests too quickly and should use
  ``--limit-req-per-minute``. The advice is given once per run, and once per album
  while downloading, not per retried request or skipped release. A rate limited band
  lookup warns too, because it otherwise only reads as "no such band".
- [Bugfix] Album art is no longer saved from a failed response. The file was opened
  before the request, so a 429 or error page body became ``cover.jpg``; the resume test
  was only whether that file exists, so the garbage stayed the album's art forever and
  ``--embed-art`` tagged every track with it. A cover is now written only from a
  successful non-empty body, an existing file must carry an image signature to be reused
  (so a poisoned folder heals itself), and a dead art url costs at most two requests
  per album instead of one per track.
- [Bugfix] Page requests now wait and retry when Bandcamp rate limits them
  (HTTP 429). A page that still fails is reported with its HTTP status
  instead of "does not exist", and a failed artist/label page exits with
  code 2 instead of silently finding no albums.
- [Bugfix] Artist pages that list releases only as music grid links (no
  ``data-client-items``) no longer return an empty discography. Grid links
  and ``data-client-items`` are now combined.
- [Bugfix] HTTP error responses are no longer saved as tracks, and an
  empty or partial leftover ``.mp3.tmp`` file is redownloaded instead of
  tagged. Both caused ``HeaderNotFoundError: can't sync to MPEG frame``.
  Failed downloads now give up after 3 attempts instead of retrying forever.
- [Bugfix] Creating an album folder no longer fails with
  ``FileExistsError`` when the folder already exists but a flaky network
  mount reported it missing.
- [Bugfix] ``--embed-art`` no longer crashes with ``TypeError`` on albums
  that have no cover art.
- [Enhancement] ``--retag`` rewrites the tags of tracks that already exist
  (for example to add genres with ``--embed-genres``) without downloading
  them again.
- [Enhancement] New per-track progress display: one line per track that
  updates in place, with a spinner, bar, size and speed, then ✔ or ✘. Use
  ``--progress plain`` for the previous single-line output. Adds the
  ``rich`` dependency.
- [Note] ``bandcamp_dl.config.load()`` now reads the config file and returns
  the options as a dataclass; the run bookkeeping is no longer stored beside
  the options and so never needs filtering out on the way to the file. Two
  startup lines changed: "Config dir exists." now says "Config file exists."
  and opening the file no longer names the mode it was opened in.
- [Enhancement] A run now shares one HTTP session between the parser and every
  album's downloader: one connection pool, one rate limit and one TLS handshake
  set instead of a fresh set per album.
- [Enhancement] The HTML parser BeautifulSoup should use is chosen once per run.
  Without ``lxml`` installed, every page used to pay a failed ``lxml`` attempt
  before falling back to the built-in parser.
- [Enhancement] Tracks whose album page reports ``has_lyrics`` as false are
  no longer fetched one page per track for lyrics that were then dropped; an
  album without lyrics costs no extra requests with ``--embed-lyrics``.
- [Enhancement] Path components are slugified once per distinct value rather than
  once per track, the cover image is read once per album instead of once per
  tagged track, downloads arrive in a fixed 64 KiB chunk instead of a hundredth
  of the file, and the plain progress display asks for the terminal width once
  per track instead of once per chunk.
- [Bugfix] A track the page says carries lyrics no longer raises ``KeyError``
  when ``--embed-lyrics`` was not asked for.
- [Note] The artist page scraping no longer reaches the label page fallback through
  an ``AttributeError``, and a ``data-client-items`` attribute is read as JSON
  instead of being parsed as HTML first. Neither changes which urls end up in
  the queue.
