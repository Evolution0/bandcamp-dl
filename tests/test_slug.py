from bandcamp_dl.slug import slugify_name


def test_punctuation_between_words_is_deleted_rather_than_turned_into_a_separator():
    # python-slugify replaces a disallowed char with its separator, which would have
    # renamed everything the old library filed without it ("AC/DC" -> "ac-dc"), so the
    # character filter runs before the library is called
    assert slugify_name('AC/DC') == 'acdc'
    assert slugify_name("Don't Live Here Anymore") == 'dont-live-here-anymore'
    assert slugify_name('1,000') == '1000'


def test_the_allow_list_keeps_the_extra_chars_a_release_name_uses():
    assert slugify_name('tilde~name') == 'tilde~name'
    assert slugify_name('snake_case') == 'snake_case'
    # an '&' is only kept when the user allowed it, same as --ok-chars always did
    assert slugify_name('Foo&Bar', ok='-~') == 'foobar'
    assert slugify_name('Foo~Bar', ok='-~') == 'foo~bar'


def test_a_space_char_the_allow_list_does_not_carry_falls_back_to_the_first_allowed_char():
    # --space-char cannot insert a character that --ok-chars would strip, so the option
    # pair falls back exactly as the old library did
    assert slugify_name('First Mix', ok='-~', space_replacement='.') == 'first-mix'
    assert slugify_name('First Mix', ok='-~', space_replacement='~') == 'first~mix'
    assert slugify_name('First Mix', ok='', space_replacement='.') == 'firstmix'


def test_keep_spaces_leaves_the_whitespace_a_name_carries_alone():
    assert slugify_name('First Mix', spaces=True, lower=False) == 'First Mix'
    # runs of spaces are whitespace in the name, not separators to fold
    assert slugify_name('Hello   World', spaces=True, lower=False) == 'Hello   World'
    # non-breaking and other separator spaces become a plain space
    assert slugify_name('First\u00a0Mix', spaces=True, lower=False) == 'First Mix'


def test_ascii_only_transliterates_the_script_instead_of_removing_it():
    assert slugify_name('Ærød Striße', only_ascii=True) == 'aerod-strisse'
    assert slugify_name('日本', only_ascii=True) == 'ri-ben'
    assert slugify_name('日本') == '日本'


def test_a_transliteration_does_not_leave_spaces_at_the_ends_of_a_name():
    # '、' transliterates to " "; the old library filtered its result again and stripped
    # the outcome, which the plain library call would have kept
    assert slugify_name('日本、', only_ascii=True) == 'ri-ben'


def test_html_entities_in_a_title_stay_ordinary_text():
    # python-slugify decodes numeric and named references by default, which would turn
    # a title that spells out an entity into its punctuation
    assert slugify_name('&amp;') == 'amp'
    assert slugify_name('&#39;quote') == '39quote'


def test_case_folding_is_off_when_the_case_option_already_dealt_with_it():
    assert slugify_name('MiXeD CaSe', lower=False) == 'MiXeD-CaSe'
    assert slugify_name('MiXeD CaSe') == 'mixed-case'
    # the parser publishes album_id and track_id as ints
    assert slugify_name(7, lower=False) == '7'


def test_a_dash_at_the_edge_of_a_name_is_now_trimmed():
    # the one user visible change of the swap: a dash is python-slugify's separator,
    # so it folds runs of it and trims it from the ends of the name, where the
    # library that was used before left an allowed dash in place
    assert slugify_name('- leading dash') == 'leading-dash'
    assert slugify_name('Warm Up - ') == 'warm-up'


def test_a_name_of_only_dashes_comes_back_empty():
    assert slugify_name('---') == ''
    assert slugify_name('---', ok='') == ''
