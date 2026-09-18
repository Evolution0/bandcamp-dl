import logging
import os
import re
import shutil

from mutagen.mp3 import MP3
from mutagen.id3 import ID3, TIT1, TIT2, WOAF, USLT, APIC, TCON, TRCK, TPE1, TPE2, TALB, TDRC, TDOR, TDRL
import requests
from  requests_ratelimiter import LimiterAdapter
import slugify

from bandcamp_dl import __version__
from bandcamp_dl.config import CASE_LOWER, CASE_UPPER, CASE_CAMEL, CASE_NONE


def print_clean(msg):
    terminal_size = shutil.get_terminal_size()
    print(f'{msg}{" " * (int(terminal_size[0]) - len(msg))}', end='')


class BandcampDownloader:
    def __init__(self, config, urls=None, debugging: bool = False):
        """Initialize variables we will need throughout the Class

        :param config: user config/args
        :param urls: list of urls
        """
        self.headers = {'User-Agent': f'bandcamp-dl/{__version__} '
                        f'(https://github.com/evolution0/bandcamp-dl)'}

        self.session = requests.Session()
        if 0 < config.limit_req_per_minute:
            # Mount the rate-limiting adapter to the session
            self.rate_adapter = LimiterAdapter(per_minute=config.limit_req_per_minute)
            self.session.mount('https://', self.rate_adapter)
        else:
            self.rate_adapter = None

        self.logger = logging.getLogger("bandcamp-dl").getChild("Downloader")
        self.logger.disabled = not debugging

        if type(urls) is str:
            self.urls = [urls]

        self.config = config
        self.urls = urls

        self.album_art = None
        self.track_num = None
        self.num_tracks = None

    def start(self, album: dict):
        """Start album download process

        :param album: album dict
        """

        if not album['full'] and not self.config.no_confirm:
            choice = input("Track list incomplete, some tracks may be private, download anyway? "
                           "(yes/no): ").lower()
            if choice == "yes" or choice == "y":
                print("Starting download process.")
                self.download_album(album)
                return None
            else:
                print("Cancelling download process.")
                return None
        else:
            self.download_album(album)
            return None

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
        self.logger.debug(" Generating filepath/trackname..")
        path = self.config.template
        self.logger.debug(f"\n\tTemplate: {path}")

        def slugify_preset(content):
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
                self.logger.debug('Track artist is None, replacing with album artist')                
                track['artist'] = track.get('albumartist')

            if self.config.untitled_path_from_slug and token == 'album' and track['album'].lower() == 'untitled':
                track['album'] = track['url'].split("/")[-1].replace("-"," ")

            if token == 'track' and track['track'] == 'None':
                track['track'] = "Single"
            else:
                track['track'] = str(track['track']).zfill(2)

            if self.config.no_slugify:
                replacement = str(track.get(key, ""))
            else:
                replacement = slugify_preset(track.get(key, ""))

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
        self.logger.debug(" Directory doesn't exist, creating..")
        if not os.path.exists(directory):
            os.makedirs(directory)

        return directory

    def download_album(self, album: dict) -> bool:
        """Download all MP3 files in the album

        :param album: album dict
        :return: True if successful
        """
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

            self.num_tracks = len(album['tracks'])
            self.track_num = track_index + 1

            filepath = self.template_to_path(path_meta, self.config.ascii_only,
                                            self.config.ok_chars, self.config.space_char,
                                            self.config.keep_spaces, self.config.case_mode)
            filepath = filepath + ".tmp"
            filename = filepath.rsplit('/', 1)[1]
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

            attempts = 0
            skip = False

            while True:
                try:
                    r = self.session.get(track['url'], headers=self.headers, stream=True)
                    file_length = int(r.headers.get('content-length', 0))
                    total = int(file_length / 100)
                    # If file exists and is still a tmp file skip downloading and encode
                    if os.path.exists(filepath):
                        self.write_id3_tags(filepath, track_meta)
                        # Set skip to True so that we don't try encoding again
                        skip = True
                        # break out of the try/except and move on to the next file
                        break
                    elif os.path.exists(filepath[:-4]) and self.config.overwrite is not True:
                        print(f"File: {filename[:-4]} already exists and is complete, skipping..")
                        skip = True
                        break
                    with open(filepath, "wb") as f:
                        if file_length is None:
                            f.write(r.content)
                        else:
                            dl = 0
                            for data in r.iter_content(chunk_size=total):
                                dl += len(data)
                                f.write(data)
                                if not self.config.debug:
                                    done = int(50 * dl / file_length)
                                    print_clean(f'\r({self.track_num}/{self.num_tracks}) '
                                                f'[{"=" * done}{" " * (50 - done)}] :: '
                                                f'Downloading: {filename[:-8]}')
                    local_size = os.path.getsize(filepath)
                    # if the local filesize before encoding doesn't match the remote filesize
                    # redownload
                    if local_size != file_length and attempts != 3:
                        print(f"{filename} is incomplete, retrying..")
                        continue
                    # if the maximum number of retry attempts is reached give up and move on
                    elif attempts == 3:
                        print("Maximum retries reached.. skipping.")
                        # Clean up incomplete file
                        os.remove(filepath)
                        break
                    # if all is well continue the download process for the rest of the tracks
                    else:
                        break
                except Exception as e:
                    print(e)
                    print("Downloading failed..")
                    return False
            if not skip:
                self.write_id3_tags(filepath, track_meta)

        if os.path.isfile(f"{self.config.base_dir}/{__version__}.not.finished"):
            os.remove(f"{self.config.base_dir}/{__version__}.not.finished")

        # Remove album art image as it is embedded
        if self.config.embed_art and hasattr(self, "album_art"):
            os.remove(self.album_art)

        return True

    def write_id3_tags(self, filepath: str, meta: dict):
        """Write metadata to the MP3 file

        :param filepath: name of mp3 file
        :param meta: dict of track metadata
        """
        self.logger.debug(" Encoding process starting..")

        filename = filepath.rsplit('/', 1)[1][:-8]

        if not self.config.debug:
            print_clean(f'\r({self.track_num}/{self.num_tracks}) [{"=" * 50}] '
                        f':: Encoding: {filename}')

        audio = MP3(filepath)
        if audio.tags is None:
            audio.add_tags()

        audio.tags.add(WOAF(encoding=3, url=meta["url"]))

        if self.config.group and 'label' in meta:
            audio.tags.add(TIT1(encoding=3, text=meta["label"]))

        if self.config.embed_lyrics:
            audio.tags.add(USLT(encoding=3, lang='eng', desc='', text=meta['lyrics']))

        if self.config.embed_art:
            with open(self.album_art, 'rb') as cover_img:
                cover_bytes = cover_img.read()
                audio.tags.add(APIC(encoding=3, mime='image/jpeg', type=3, desc='Cover', data=cover_bytes))

        if self.config.embed_genres:
            audio.tags.add(TCON(encoding=3, text=meta['genres']))

        if meta['track'].isdigit():
            audio.tags.add(TRCK(encoding=3, text=meta['track']))
        else:
            audio.tags.add(TRCK(encoding=3, text=1))

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

        if self.config.debug:
            return

        print_clean(f'\r({self.track_num}/{self.num_tracks}) [{"=" * 50}] :: Finished: {filename}')
