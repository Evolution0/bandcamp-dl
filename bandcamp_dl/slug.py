"""Slugs for file and directory names, built on python-slugify.

The project used to call ``unicode-slugify`` (mozilla's fork, pinned to an unmerged
pull request) directly because that library took bandcamp-dl's whole option set as
arguments. python-slugify covers normalisation, transliteration, case folding and
separator collapsing, but it has no allow-list of extra characters and replaces
unwanted characters with its separator where the old library deleted them, so
:func:`_sanitize` runs before the call.

Two output differences follow from the swap, both about the dash that sits in the
default allow-list, and neither reachable through a release name that is not
punctuation at either end:

* python-slugify uses a dash as its separator, so it folds a dash run and trims
  the dash at the start and end of a name: ``- leading dash`` used to keep its
  leading dash.
* a handful of characters whose lower case form carries a combining mark (U+0130
  and friends) end up separated instead of keeping the invisible mark.
"""
import re
import unicodedata
from functools import lru_cache

from slugify import slugify

# The default allow-list, mirrored from config.OK_CHARS
SLUG_OK = '-_~'


@lru_cache(maxsize=8)
def _separator_pattern(space_replacement: str) -> re.Pattern:
    """The pattern that collapses a run of separators, built once per separator char

    :param space_replacement: the character standing in for a space
    :return: a compiled pattern matching any run of that char or of whitespace
    """
    return re.compile(rf'[{re.escape(space_replacement)}\s]+')


@lru_cache(maxsize=8)
def _allowed_pattern(allowed: str) -> re.Pattern:
    """The pattern that drops everything outside an allow-list, built once per allow-list

    :param allowed: the characters that survive the filter
    :return: a compiled pattern matching everything else
    """
    return re.compile(rf'[^\w{re.escape(allowed)}]+')


def _sanitize(text: str, ok: str) -> str:
    """Keep letters, digits and the allowed extras, and delete everything else.

    Separators (Unicode category Z*) become a plain space so that they take part
    in the separator collapsing later on.

    :param text: already normalised text
    :param ok: characters outside the alphanumerics that survive the filter
    :return: the filtered text, stripped of surrounding whitespace
    """
    kept = []
    for char in text:
        category = unicodedata.category(char)[0]
        if category in 'LN' or char in ok:
            kept.append(char)
        elif category == 'Z':
            kept.append(' ')
    return ''.join(kept).strip()


def slugify_name(text: str, ok: str = SLUG_OK, only_ascii: bool = False, spaces: bool = False,
                 lower: bool = True, space_replacement: str = '-') -> str:
    """Turn one metadata value into a path component.

    The signature matches the options bandcamp-dl exposes on the command line
    (``--ok-chars``, ``--ascii-only``, ``--keep-spaces``, ``--space-char``) and the
    case conversion, so the behaviour of an existing library does not change.

    :param text: the metadata value, any type the parser publishes
    :param ok: extra characters to keep, see :func:`_sanitize`
    :param only_ascii: transliterate, so that the name carries ascii characters only
    :param spaces: retain whitespace instead of replacing it
    :param lower: fold the text to lower case
    :param space_replacement: character to use in place of spaces
    :return: the path component
    """
    core = _sanitize(unicodedata.normalize('NFKC', str(text)), ok)

    if not spaces:
        # A separator the user has not allowed in --ok-chars cannot be inserted into
        # the name, so it falls back to the first allowed char, as the old library did
        if space_replacement and space_replacement not in ok:
            space_replacement = ok[0] if ok else ''
        # Collapsing is done here rather than left to the library because a dash the
        # user allowed in --ok-chars is an ordinary character, not a separator to fold
        core = _separator_pattern(space_replacement).sub(space_replacement, core)
        allowed = ok + space_replacement
    else:
        allowed = ok + ' '

    return slugify(
        core,
        # HTML entities are ordinary text in a release title, not markup to decode
        entities=False,
        decimal=False,
        hexadecimal=False,
        allow_unicode=not only_ascii,
        lowercase=lower,
        # The separators are already in place, nothing is left for the library to map
        separator='-',
        # Everything outside the allow-list has been filtered out already, so this
        # only catches what the transliteration of --ascii-only invents
        regex_pattern=_allowed_pattern(allowed),
    ).strip()
    # The strip is not redundant: a transliteration can leave whitespace at either
    # end ('、' becomes " ", a full width comma) where the old library re-filtered
    # the transliterated text before returning it
