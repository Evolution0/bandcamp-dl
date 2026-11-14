bandcamp-dl
===========
|PyPI pyversions| |PyPI download month| |PyPI license| |GitHub release| |GitHub commits|

Download audio from `bandcamp.com`_

Synopsis
--------

``bandcamp-dl URL``

Installation
------------

From PyPI
~~~~~~~~~

``pip3 install bandcamp-downloader``

Some linux distros may require that python3-pip is installed first.

From Wheel
~~~~~~~~~~

1. Download the wheel (``.whl``) from PyPI or the Releases page
2. ``cd`` to the directory containing the ``.whl`` file
3. ``pip install <filename>.whl``

[OSX] From Homebrew
~~~~~~~~~~~~~~~~~~~

``brew install bandcamp-dl``

[Arch] From the AUR
~~~~~~~~~~~~~~~~~~~

``yay -S bandcamp-dl-git``

From Source
~~~~~~~~~~~

1. Clone the project or `download and extract the zip`_
2. ``cd`` to the project directory
3. Run ``pip install .``

Description
-----------

bandcamp-dl is a small command-line app to download audio from
bandcamp.com. It requires the Python interpreter, version 3.4 (or
higher) and is not platform specific. It is released to the public
domain, which means you can modify it, redistribute it or use it how
ever you like.

Details
-------

::

    Usage:
        bandcamp-dl [options] [URL]

    Arguments:
        URL         Bandcamp album/track URL

Options
-------

::

    Options:
      -h, --help            show this help message and exit
      -v, --version         Show version
      -d, --debug           Verbose logging
      --artist ARTIST       Specify an artist's slug to download their full discography.
      --track TRACK         Specify a track's slug to download a single track. Must be used with --artist.
      --album ALBUM         Specify an album's slug to download a single album. Must be used with --artist.
      --template TEMPLATE   Output filename template, default: %{artist}/%{album}/%{track} - %{title}
      --base-dir BASE_DIR   Base location of which all files are downloaded
      -f, --full-album      Download only if all tracks are available
      -o, --overwrite       Overwrite tracks that already exist. Default is False.
      -n, --no-art          Skip grabbing album art
      -e, --embed-lyrics    Embed track lyrics (If available)
      -g, --group           Use album/track Label as iTunes grouping
      -r, --embed-art       Embed album art (If available)
      --cover-quality {0,10,16}
                              Set the cover art quality. 0 is source, 10 is album page (1200x1200), 16 is default embed
                              (700x700).
      -y, --no-slugify      Disable slugification of track, album, and artist names
      -c OK_CHARS, --ok-chars OK_CHARS
                              Specify allowed chars in slugify, default: -_~
      -s SPACE_CHAR, --space-char SPACE_CHAR
                              Specify the char to use in place of spaces, default: -
      -a, --ascii-only      Only allow ASCII chars (北京 (capital of china) -> bei-jing-capital-of-china)
      -k, --keep-spaces     Retain whitespace in filenames
      -x {lower,upper,camel,none}, --case-convert {lower,upper,camel,none}
                              Specify the char case conversion logic, default: lower
      --no-confirm          Override confirmation prompts. Use with caution
      --embed-genres        Embed album/track genres
      --truncate-album LENGTH
                              Truncate album title to a maximum length. 0 for no limit.
      --truncate-track LENGTH
                              Truncate track title to a maximum length. 0 for no limit.
      --progress {auto,plain}
                              Progress output: "auto" shows a line per track that updates in place,
                              "plain" shows one rewritten line. Default is auto.

Filename Template
-----------------

The ``--template`` option allows users to indicate a template for the
output file names and directories. Templates can be built using special
tokens with the format of ``%{artist}``. Here is a list of allowed
tokens:

-  ``trackartist``: The artist name.
-  ``artist``: The album artist name.
-  ``album``: The album name.
-  ``track``: The track number.
-  ``title``: The track title.
-  ``date``: The album date.
-  ``label``: The album label.

The default template is: ``%{artist}/%{album}/%{track} - %{title}``.

Bugs
----

Bugs should be reported `here`_. Please include the URL and/or options
used as well as the output when using the `--debug` option.

For discussions, join us in `Discord`_.

When you submit a request, please re-read it once to avoid a couple of
mistakes (you can and should use this as a checklist):

Are you using the latest version?
---------------------------------

This should report that you're up-to-date. About 20% of the reports we
receive are already fixed, but people are using outdated versions. This
goes for feature requests as well.

Is the issue already documented?
--------------------------------

Make sure that someone has not already opened the issue you're trying to
open. Search at the top of the window or at `Issues`_. If there is an
issue, feel free to write something along the lines of "This affects me
as well, with version 2015.01.01. Here is some more information on the
issue: ...". While some issues may be old, a new post into them often
spurs rapid activity.

Why are existing options not enough?
------------------------------------

Before requesting a new feature, please have a quick peek at 
`the list of supported options`_.  Many feature requests are for
features that actually exist already!  Please, absolutely do show off
your work in the issue report and detail how the existing similar
options do *not* solve your problem.

Does the issue involve one problem, and one problem only?
---------------------------------------------------------

Some of our users seem to think there is a limit of issues they can or
should open. There is no limit of issues they can or should open. While
it may seem appealing to be able to dump all your issues into one
ticket, that means that someone who solves one of your issues cannot
mark the issue as closed. Typically, reporting a bunch of issues leads
to the ticket lingering since nobody wants to attack that behemoth,
until someone mercifully splits the issue into multiple ones.

Is anyone going to need the feature?
------------------------------------

Only post features that you (or an incapable friend you can
personally talk to) require. Do not post features because they seem like
a good idea. If they are really useful, they will be requested by
someone who requires them.

Is your question about bandcamp-dl?
-----------------------------------

It may sound strange, but some bug reports we receive are completely
unrelated to bandcamp-dl and relate to a different or even the
reporter's own application. Please make sure that you are actually using
bandcamp-dl. If you are using a UI for bandcamp-dl, report the bug to
the maintainer of the actual application providing the UI. On the other
hand, if your UI for bandcamp-dl fails in some way you believe is
related to bandcamp-dl, by all means, go ahead and report the bug.

Dependencies
------------

- `BeautifulSoup4`_ - HTML Parsing
- `Demjson`_- JavaScript dict to JSON conversion
- `Mutagen`_ - ID3 Encoding
- `Requests`_ - for retrieving the HTML

Copyright
---------

bandcamp-dl is released into the public domain by the copyright holders

This README file was inspired by the `youtube-dl`_ docs and is likewise
released into the public domain.


.. _download and extract the zip: https://github.com/evolution0/bandcamp-dl/archive/master.zip
.. _here: https://github.com/evolution0/bandcamp-dl/issues
.. _Discord: https://discord.gg/nwdT4MP
.. _bandcamp.com: https://www.bandcamp.com
.. _Issues: https://github.com/evolution0/bandcamp-dl/search?type=Issues
.. _the list of supported options: https://github.com/evolution0/bandcamp-dl/blob/master/README.rst#synopsis
.. _BeautifulSoup4: https://pypi.python.org/pypi/beautifulsoup4 
.. _Demjson: https://pypi.python.org/pypi/demjson
.. _Mutagen: https://pypi.python.org/pypi/mutagen
.. _Requests: https://pypi.python.org/pypi/requests
.. _youtube-dl: https://github.com/rg3/youtube-dl/blob/master/README.md

.. |PyPI pyversions| image:: https://img.shields.io/pypi/pyversions/bandcamp-downloader.svg
   :target: https://pypi.python.org/pypi/bandcamp-downloader/


.. |PyPI download month| image:: https://img.shields.io/pypi/dm/bandcamp-downloader.svg
   :target: https://pypi.python.org/pypi/bandcamp-downloader/


.. |PyPI license| image:: https://img.shields.io/pypi/l/bandcamp-downloader.svg
   :target: https://pypi.python.org/pypi/bandcamp-downloader/


.. |GitHub release| image:: https://img.shields.io/github/release/evolution0/bandcamp-dl.svg
   :target: https://GitHub.com/evolution0/bandcamp-dl/releases/


.. |GitHub commits| image:: https://img.shields.io/github/commits-since/evolution0/bandcamp-dl/v0.0.17.svg
   :target: https://GitHub.com/evolution0/bandcamp-dl/commit/
