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
