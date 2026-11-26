import logging
import os
import re

from mutagen.mp3 import MP3
from mutagen.id3 import ID3, TIT1, TIT2, WOAF, USLT, APIC, TCON, TRCK, TPE1, TPE2, TALB, TDRC, TDOR, TDRL
import slugify

from bandcamp_dl import __version__
from bandcamp_dl.config import CASE_LOWER, CASE_UPPER, CASE_CAMEL, CASE_NONE
from bandcamp_dl.progress import make_progress
from bandcamp_dl.session import make_session


class BandcampDownloader:
    def __init__(self, config, urls=None, debugging: bool = False):
        """Initialize variables we will need throughout the Class

        :param config: user config/args
        :param urls: list of urls
        :param debugging: toggle verbose logging
        """
        self.headers = {'User-Agent': f'bandcamp-dl/{__version__} '
                        f'(https://github.com/evolution0/bandcamp-dl)'}

        self.session = make_session(config.limit_req_per_minute)

        self.logger = logging.getLogger("bandcamp-dl").getChild("Downloader")
        # Debug chatter only: warnings and errors should still show without --debug,
        # and the old `disabled = debugging` flag muted them exactly when debugging
        self.logger.setLevel(logging.DEBUG if debugging else logging.WARNING)

        if isinstance(urls, str):
            urls = [urls]

        self.config = config
        self.urls = urls

        self.album_art = None

    def start(self, album: dict) -> bool | None:
        """Start album download process

        :param album: album dict
        :return: False if a track failed, None if the download was cancelled
        """

        if not album['full'] and not self.config.no_confirm:
            choice = input(f"Track list for {album['title']} incomplete, some tracks may be private, download anyway? "
                           "(yes/no): ").lower()
            if choice == "yes" or choice == "y":
                print("Starting download process.")
                return self.download_album(album)
            else:
                print("Cancelling download process.")
                return None
        else:
            return self.download_album(album)

    def template_to_path(self, track: dict, ascii_only, ok_chars, space_char, keep_space,
                         case_mode) -> str:
        """Create valid filepath based on template

        :param track: track metadata
        :param ok_chars: optional chars to allow
        :param ascii_only: allow only ascii chars in filename
        :param keep_space: retain whitespace in filename
        :param case_mode: char case conversion logic (or none / retain)
        :param space_char: char to use in place of spaces
        :return: filepath
        """
        # TODO: Allow overriding most of this in the case of a Playlist with a arg

        self.logger.debug(" Generating filepath/trackname..")
        path = self.config.template
        self.logger.debug(f"\n\tTemplate: {path}")

        def slugify_preset(content):
            # album_id and track_id reach the tokens as ints from parse(), and the case options
            # below are string operations, so whatever a token carries becomes text first
            content = str(content)
            retain_case = case_mode != CASE_LOWER
            if case_mode == CASE_UPPER:
                content = content.upper()
            if case_mode == CASE_CAMEL:
                content = re.sub(r'(((?<=\s)|^|-)[a-z])', lambda x: x.group().upper(), content.lower())
            slugged = slugify.slugify(content, ok=ok_chars, only_ascii=ascii_only,
                                      spaces=keep_space, lower=not retain_case,
                                      space_replacement=space_char)
            return slugged

        template_tokens = ['trackartist', 'artist', 'album', 'title', 'date', 'label', 'track', 'album_id', 'track_id']
        for token in template_tokens:
            key = token
            if token == 'trackartist':
                key = 'artist'
            elif token == 'artist':
                key = 'albumartist'

            if key == 'artist' and track.get('artist') is None:
                self.logger.debug(' Track artist is None, replacing with album artist')
                track['artist'] = track.get('albumartist')

            if self.config.untitled_path_from_slug and token == 'album' and track['album'].lower() == 'untitled':
                track['album'] = track['url'].split("/")[-1].replace("-"," ")

            if token == 'track' and track['track'] == 'None':
                track['track'] = "Single"
            else:
                track['track'] = str(track['track']).zfill(2)

            # A token the release does not carry, e.g. the label of a release with no seller
            # entry, contributes nothing to the path; it used to insert the word "None" there
            value = track.get(key, "")
            if value is None:
                value = ""

            if self.config.no_slugify:
                replacement = str(value)
            else:
                replacement = slugify_preset(value)

            path = path.replace(f'%{{{token}}}', replacement)

        if self.config.base_dir is not None:
            path = f"{self.config.base_dir}/{path}.mp3"
        else:
            path = f"{path}.mp3"

        self.logger.debug(" filepath/trackname generated..")
        self.logger.debug(f"\n\tPath: {path}")
        return path


    def create_directory(self, filename: str) -> str:
        """Create directory based on filename if it doesn't exist

        :param filename: full filename
        :return: directory path
        """
        directory = os.path.dirname(filename)
        self.logger.debug(f" Directory:\n\t{directory}")
        self.logger.debug(" Creating directory if it doesn't exist..")
        # exist_ok rather than an exists() check: on flaky network mounts exists() can
        # report False for a folder that is there
        os.makedirs(directory, exist_ok=True)

        return directory

    def download_album(self, album: dict) -> bool:
        """Download all MP3 files in the album, showing one progress line per track

        :param album: album dict
        :return: True if successful
        """
        with make_progress(self.config.progress, self.config.debug) as self.progress:
            self.progress.album(album)
            return self.download_tracks(album)

    def download_tracks(self, album: dict) -> bool:
        """Download all MP3 files in the album

        :param album: album dict
        :return: True if successful
        """
        album_failed = False
        for track_index, track in enumerate(album['tracks']):
            track_meta = {"artist": track['artist'],
                          "albumartist": album['artist'],
                          "label": album['label'],
                          "album": album['title'],
                          "title": track['title'].replace(f"{track['artist']} - ", "", 1),
                          "track": track['track'],
                          "track_id": track['track_id'],
                          "album_id": album['album_id'],
                          # TODO: Find out why the 'lyrics' key seems to vanish.
                          "lyrics": track.get('lyrics', ""),
                          "date": album['date'],
                          "url": album['url'],
                          "genres": album['genres']}

            path_meta = track_meta.copy()

            if 0 < self.config.truncate_album < len(path_meta['album']):
                path_meta['album'] = path_meta['album'][:self.config.truncate_album]

            if 0 < self.config.truncate_track < len(path_meta['title']):
                path_meta['title'] = path_meta['title'][:self.config.truncate_track]


            filepath = self.template_to_path(path_meta, self.config.ascii_only,
                                            self.config.ok_chars, self.config.space_char,
                                            self.config.keep_spaces, self.config.case_mode)
            filepath = filepath + ".tmp"
            filename = filepath.rsplit('/', 1)[1]
            self.progress.track(track_index, filename)
            dirname = self.create_directory(filepath)

            self.logger.debug(" Current file:\n\t%s", filepath)

            cover_path = dirname + "/cover.jpg"
            if album['art'] and not os.path.exists(cover_path):
                try:
                    with open(cover_path, "wb") as f:
                        r = self.session.get(album['art'], headers=self.headers)
                        f.write(r.content)
                    self.album_art = cover_path
                except Exception as e:
                    print(e)
                    print("Couldn't download album art.")
            elif os.path.exists(cover_path):
                self.album_art = cover_path

            if self.config.retag and os.path.exists(filepath[:-4]):
                # Tag the finished file in place instead of downloading it again;
                # write_id3_tags renames the .tmp back to the final name
                if os.path.exists(filepath):
                    # A stale .tmp from an interrupted run would be silently overwritten
                    # by the rename below, on Windows it would raise instead
                    os.remove(filepath)
                os.rename(filepath[:-4], filepath)
                try:
                    self.write_id3_tags(filepath, track_meta)
                except Exception as e:
                    self.progress.failed(str(e))
                    print(f"Retagging {filename[:-4]} failed, moving on to the next track..")
                    # Never leave a finished track parked under its .tmp name
                    self.rename_tmp_back(filepath)
                    album_failed = True
                continue

            attempts = 0
            skip = False
            file_length = 0

            while True:
                try:
                    r = self.session.get(track['url'], headers=self.headers, stream=True)
                    file_length = int(r.headers.get('content-length', 0))
                    total = int(file_length / 100)
                    if not r.ok:
                        # Never save an error page as audio, mutagen can't read it
                        print(f"{filename[:-4]} failed with HTTP {r.status_code}, retrying..")
                    # A leftover tmp file is only safe to encode if its download had finished
                    elif os.path.exists(filepath) and file_length and \
                            os.path.getsize(filepath) == file_length:
                        self.write_id3_tags(filepath, track_meta)
                        # Set skip to True so that we don't try encoding again
                        skip = True
                        # break out of the try/except and move on to the next file
                        break
                    elif os.path.exists(filepath[:-4]) and self.config.overwrite is not True:
                        self.progress.skipped()
                        skip = True
                        break
                    else:
                        self.progress.downloading(file_length)
                        with open(filepath, "wb") as f:
                            dl = 0
                            for data in r.iter_content(chunk_size=total or 8192):
                                dl += len(data)
                                f.write(data)
                                self.progress.advance(dl)
                        # if the local filesize matches the remote filesize (or the server sent
                        # no length and we got data), move on to encoding
                        local_size = os.path.getsize(filepath)
                        if local_size == file_length or (not file_length and local_size):
                            break
                        print(f"{filename} is incomplete, retrying..")
                    attempts += 1
                    # if the maximum number of retry attempts is reached give up and move on
                    if attempts == 3:
                        self.progress.failed("Maximum retries reached.. skipping.")
                        # Clean up incomplete file
                        if os.path.exists(filepath):
                            os.remove(filepath)
                        skip = True
                        album_failed = True
                        break
                except Exception as e:
                    self.progress.failed(str(e))
                    print(f"{filename[:-4]} failed, moving on to the next track..")
                    # Drop an incomplete file so it is never mistaken for a download, but keep
                    # one that arrived whole and only failed while tagging
                    complete = bool(file_length) and os.path.exists(filepath) and \
                        os.path.getsize(filepath) == file_length
                    if os.path.exists(filepath) and not complete:
                        os.remove(filepath)
                    skip = True
                    album_failed = True
                    break
            if not skip:
                try:
                    self.write_id3_tags(filepath, track_meta)
                except Exception as e:
                    self.progress.failed(str(e))
                    print(f"Tagging {filename[:-4]} failed, the audio is still in {filepath}..")
                    # Keep the downloaded .tmp: the next run re-tags it without downloading again
                    album_failed = True

        if os.path.isfile(f"{self.config.base_dir}/{__version__}.not.finished"):
            os.remove(f"{self.config.base_dir}/{__version__}.not.finished")

        # Remove album art image as it is embedded
        # album_art stays None when the album has no cover
        if self.config.embed_art and self.album_art:
            os.remove(self.album_art)

        return not album_failed

    def rename_tmp_back(self, filepath: str):
        """Put a track that was parked under its .tmp name back under the real one

        :param filepath: the .tmp path
        """
        try:
            if os.path.exists(filepath):
                os.rename(filepath, filepath[:-4])
        except OSError as e:
            self.logger.warning(f"Could not restore {filepath} to {filepath[:-4]}: {e}")

    def write_id3_tags(self, filepath: str, meta: dict):
        """Write metadata to the MP3 file

        :param filepath: name of mp3 file
        :param meta: dict of track metadata
        """
        self.logger.debug(" Encoding process starting..")
        self.progress.tagging()

        audio = MP3(filepath)
        if audio.tags is None:
            audio.add_tags()

        audio.tags.add(WOAF(encoding=3, url=meta["url"]))

        # 'label' is always in meta but is None for releases with no seller entry, and
        # mutagen raises on None text, which used to abort the album midway
        if self.config.group and meta.get('label'):
            audio.tags.add(TIT1(encoding=3, text=meta["label"]))

        if self.config.embed_lyrics:
            audio.tags.add(USLT(encoding=3, lang='eng', desc='', text=meta['lyrics']))

        if self.config.embed_art and self.album_art:
            with open(self.album_art, 'rb') as cover_img:
                cover_bytes = cover_img.read()
                audio.tags.add(APIC(encoding=3, mime='image/jpeg', type=3, desc='Cover', data=cover_bytes))

        if self.config.embed_genres:
            audio.tags.add(TCON(encoding=3, text=meta['genres']))

        if meta['track'].isdigit():
            audio.tags.add(TRCK(encoding=3, text=meta['track']))
        else:
            audio.tags.add(TRCK(encoding=3, text="1"))

        if meta['artist'] is not None:
            audio.tags.add(TPE1(encoding=3, text=meta['artist']))
        else:
            audio.tags.add(TPE1(encoding=3, text=meta['albumartist']))

        audio.tags.add(TIT2(encoding=3, text=meta["title"]))
        audio.tags.add(TPE2(encoding=3, text=meta['albumartist']))
        audio.tags.add(TALB(encoding=3, text=meta['album']))
        # We don't currently separate recording date from release date
        audio.tags.add(TDRC(encoding=3, text=meta["date"]))
        audio.save()

        self.logger.debug(" Encoding process finished..")
        self.logger.debug(" Renaming:\n\t%s -to-> %s", filepath, filepath[:-4])

        try:
            os.rename(filepath, filepath[:-4])
        except OSError:
            os.remove(filepath[:-4])
            os.rename(filepath, filepath[:-4])

        self.progress.finished(os.path.getsize(filepath[:-4]))
