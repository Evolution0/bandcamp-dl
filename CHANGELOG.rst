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
