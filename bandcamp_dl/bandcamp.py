import sys
import datetime
import json
import logging

import bs4
import requests
from requests.adapters import HTTPAdapter
from urllib.parse import urljoin

try:
    from urllib3.util import create_urllib3_context
except ImportError:
    from urllib3.util.ssl_ import create_urllib3_context

from bandcamp_dl import __version__
from bandcamp_dl.bandcampjson import BandcampJSON

class SSLAdapter(HTTPAdapter):
    def __init__(self, ssl_context=None, **kwargs):
        self.ssl_context = ssl_context
        super().__init__(**kwargs)

    def init_poolmanager(self, *args, **kwargs):
        kwargs['ssl_context'] = self.ssl_context
        return super().init_poolmanager(*args, **kwargs)

    def proxy_manager_for(self, *args, **kwargs):
        kwargs['ssl_context'] = self.ssl_context
        return super().proxy_manager_for(*args, **kwargs)


# Create the SSL context with the custom ciphers
ctx = create_urllib3_context()
ctx.load_default_certs()

DEFAULT_CIPHERS = ":".join(
    [
        "ECDHE+AESGCM",
        "ECDHE+CHACHA20",
        "DHE+AESGCM",
        "DHE+CHACHA20",
        "ECDH+AESGCM",
        "DH+AESGCM",
        "ECDH+AES",
        "DH+AES",
        "RSA+AESGCM",
        "RSA+AES",
        "!aNULL",
        "!eNULL",
        "!MD5",
        "!DSS",
        "!AESCCM",
    ]
)
ctx.set_ciphers(DEFAULT_CIPHERS)

class Bandcamp:
    def __init__(self):
        self.headers = {'User-Agent': f'bandcamp-dl/{__version__} '
                        f'(https://github.com/evolution0/bandcamp-dl)'}
        self.soup = None
        self.tracks = None
        self.logger = logging.getLogger("bandcamp-dl").getChild("Main")

        # Mount the adapter with the custom SSL context to the session
        self.session = requests.Session()
        self.adapter = SSLAdapter(ssl_context=ctx)
        self.session.mount('https://', self.adapter)

    def parse(self, url: str, art: bool = True, lyrics: bool = False, genres: bool = False,
              debugging: bool = False, cover_quality: int = 0) -> dict or None:
        """Requests the page, cherry-picks album info

        :param url: album/track url
        :param art: if True download album art
        :param lyrics: if True fetch track lyrics
        :param genres: if True fetch track tags
        :param debugging: if True then verbose output
        :return: album metadata
        """

        try:
            response = self.session.get(url, headers=self.headers)
        except requests.exceptions.MissingSchema:
            return None

        if not response.ok:
            self.logger.debug(" Status code: %s", response.status_code)
            print(f"The Album/Track requested does not exist at: {url}")
            sys.exit(2)

        try:
            self.soup = bs4.BeautifulSoup(response.text, "lxml")
        except bs4.FeatureNotFound:
            self.soup = bs4.BeautifulSoup(response.text, "html.parser")

        self.logger.debug(" Generating BandcampJSON..")
        bandcamp_json = BandcampJSON(self.soup, debugging).generate()
        page_json = {}
        for entry in bandcamp_json:
            page_json = {**page_json, **json.loads(entry)}
        self.logger.debug(" BandcampJSON generated..")

        self.logger.debug(" Generating Album..")
        self.tracks = page_json['trackinfo']

        track_ids = {}
        if 'track' in page_json and 'itemListElement' in page_json['track']:
            for item in page_json['track']['itemListElement']:
                track_url = item['item']['@id']
                for prop in item['item'].get('additionalProperty', []):
                    if prop.get('name') == 'track_id':
                        track_ids[track_url] = prop.get('value')
                        break

        track_nums = [track['track_num'] for track in self.tracks]
        if len(track_nums) != len(set(track_nums)):
            self.logger.debug(" Duplicate track numbers found, re-numbering based on position..")
            track_positions = {}
            if 'track' in page_json and 'itemListElement' in page_json['track']:
                for item in page_json['track']['itemListElement']:
                    track_url = item['item']['@id']
                    position = item['position']
                    track_positions[track_url] = position

            if "/track/" in page_json['url']:
                artist_url = page_json['url'].rpartition('/track/')[0]
            else:
                artist_url = page_json['url'].rpartition('/album/')[0]

            for track in self.tracks:
                full_track_url = f"{artist_url}{track['title_link']}"
                if full_track_url in track_positions:
                    track['track_num'] = track_positions[full_track_url]
                else:
                    self.logger.debug(f" Could not find position for track: {full_track_url}")
                    track['track_num'] = self.tracks.index(track) + 1

        album_release = page_json['album_release_date']
        if album_release is None:
            album_release = page_json['current']['release_date']
            if album_release is None:
                album_release = page_json['embed_info']['item_public']

        try:
            album_title = page_json['current']['title']
        except KeyError:
            album_title = page_json['trackinfo'][0]['title']

        try:
            label = page_json['item_sellers'][f'{page_json["current"]["selling_band_id"]}']['name']
        except KeyError:
            label = None

        album_id = None
        track_id_from_music_recording = None

        if page_json.get('@type') == 'MusicRecording':
            if 'additionalProperty' in page_json:
                for prop in page_json['additionalProperty']:
                    if prop.get('name') == 'track_id':
                        track_id_from_music_recording = prop.get('value')
                        album_id = track_id_from_music_recording
                        self.logger.debug(f" Single track page, found track_id: {track_id_from_music_recording}")
                        break
        elif page_json.get('@type') == 'MusicAlbum':
            if 'albumRelease' in page_json:
                for release in page_json['albumRelease']:
                    if 'additionalProperty' in release:
                        for prop in release['additionalProperty']:
                            if prop.get('name') == 'item_id':
                                album_id = prop.get('value')
                                self.logger.debug(f" Album page, found album_id: {album_id}")
                                break
                    if album_id:
                        break

        album = {
            "tracks": [],
            "title": album_title,
            "artist": page_json['artist'],
            "label": label,
            "full": False,
            "art": "",
            "date": str(datetime.datetime.strptime(album_release, "%d %b %Y %H:%M:%S GMT").year),
            "url": url,
            "genres": "",
            "album_id": album_id
        }

        if "/track/" in page_json['url']:
            artist_url = page_json['url'].rpartition('/track/')[0]
        else:
            artist_url = page_json['url'].rpartition('/album/')[0]

        for track in self.tracks:
            full_track_url = f"{artist_url}{track['title_link']}"
            if track_id_from_music_recording:
                track['track_id'] = track_id_from_music_recording
            else:
                track['track_id'] = track_ids.get(full_track_url)

            if lyrics:
                track['lyrics'] = self.get_track_lyrics(f"{artist_url}"
                                                        f"{track['title_link']}#lyrics")

            if track['file'] is not None:
                track = self.get_track_metadata(track)
                album['tracks'].append(track)

        album['full'] = self.all_tracks_available()
        if art:
            album['art'] = self.get_album_art(cover_quality)
        if genres:
            album['genres'] = "; ".join(page_json['keywords'])

        self.logger.debug(" Album generated..")
        self.logger.debug(" Album URL: %s", album['url'])

        return album

    def get_track_lyrics(self, track_url):
        self.logger.debug(" Fetching track lyrics..")
        track_page = self.session.get(track_url, headers=self.headers)
        try:
            track_soup = bs4.BeautifulSoup(track_page.text, "lxml")
        except bs4.FeatureNotFound:
            track_soup = bs4.BeautifulSoup(track_page.text, "html.parser")
        track_lyrics = track_soup.find("div", {"class": "lyricsText"})
        if track_lyrics:
            self.logger.debug(" Lyrics retrieved..")
            return track_lyrics.text
        else:
            self.logger.debug(" Lyrics not found..")
            return ""

    def all_tracks_available(self) -> bool:
        """Verify that all tracks have a url

        :return: True if all urls accounted for
        """
        for track in self.tracks:
            if track['file'] is None:
                return False
        return True

    def get_track_metadata(self, track: dict or None) -> dict:
        """Extract individual track metadata

        :param track: track dict
        :return: track metadata dict
        """
        self.logger.debug(" Generating track metadata..")
        track_metadata = {
            "duration": track['duration'],
            "track": str(track['track_num']),
            "title": track['title'],
            "artist": track['artist'],
            "track_id": track.get('track_id'),
            "url": None
        }

        if 'mp3-128' in track['file']:
            if 'https' in track['file']['mp3-128']:
                track_metadata['url'] = track['file']['mp3-128']
            else:
                track_metadata['url'] = "http:" + track['file']['mp3-128']
        else:
            track_metadata['url'] = None

        if track['has_lyrics'] is not False:
            if track['lyrics'] is not None:
                track_metadata['lyrics'] = track['lyrics'].replace('\\r\\n', '\n')

        self.logger.debug(" Track metadata generated..")
        return track_metadata

    @staticmethod
    def generate_album_url(artist: str, slug: str, page_type: str) -> str:
        """Generate an album url based on the artist and album name

        :param artist: artist name
        :param slug: Slug of album/track
        :param page_type: Type of page album/track
        :return: url as str
        """
        return f"http://{artist}.bandcamp.com/{page_type}/{slug}"

    def get_album_art(self, quality: int = 0) -> str:
        """Find and retrieve album art url from page

        :param quality: The quality of the album art to retrieve
        :return: url as str
        """
        try:
            url = self.soup.find(id='tralbumArt').find_all('a')[0]['href']
            return f"{url[:-6]}{quality}{url[-4:]}"
        except None:
            pass

    def get_full_discography(self, artist: str, page_type: str) -> list:
        """Generate a list of album and track urls based on the artist name

        :param artist: artist name
        :param page_type: Type of page, it should be music but it's a parameter so it's not
                          hardcoded
        :return: urls as list of strs
        """

        album_urls = set()

        music_page_url = f"https://{artist}.bandcamp.com/{page_type}"
        self.logger.info(f"Scraping discography from: {music_page_url}")

        try:
            response = self.session.get(music_page_url, headers=self.headers)
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Could not fetch artist page {music_page_url}: {e}")
            return []

        try:
            soup = bs4.BeautifulSoup(response.text, "lxml")
        except bs4.FeatureNotFound:
            soup = bs4.BeautifulSoup(response.text, "html.parser")

        music_grid = soup.find('ol', {'id': 'music-grid'})
        if not music_grid:
            self.logger.warning("Could not find music grid on the page. No albums found.")
            return []

        if 'data-client-items' in music_grid.attrs:
            self.logger.debug("Found data-client-items attribute. Parsing for album URLs.")
            try:
                json_string = bs4.BeautifulSoup(music_grid['data-client-items'], "html.parser").text
                items = json.loads(json_string)
                for item in items:
                    if 'page_url' in item:
                        full_url = urljoin(music_page_url, item['page_url'])
                        album_urls.add(full_url)
            except (json.JSONDecodeError, TypeError) as e:
                self.logger.error(f"Failed to parse data-client-items JSON: {e}")

        self.logger.debug("Scraping all <li> elements in the music grid for links.")
        for a in music_grid.select('li.music-grid-item a'):
            href = a.get('href')
            if href:
                full_url = urljoin(music_page_url, href)
                album_urls.add(full_url)

        self.logger.info(f"Found a total of {len(album_urls)} unique album/track links.")
        return list(album_urls)
