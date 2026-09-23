import logging

import demjson3


class BandcampJSON:
    def __init__(self, body, debugging: bool = False):
        self.body = body
        self.json_data = []
        self.logger = logging.getLogger("bandcamp-dl").getChild("JSON")
        self.logger.disabled = debugging

    def generate(self):
        """Grabbing needed data from the page"""
        self.get_pagedata()
        self.get_js()
        return self.json_data

    def get_pagedata(self):
        self.logger.debug(" Grab pagedata JSON..")
        pagedata = self.body.find('div', {'id': 'pagedata'})['data-blob']
        self.json_data.append(pagedata)

    def get_js(self):
        """Get <script> element containing the data we need and return the raw JS"""
        self.logger.debug(" Grabbing embedded scripts..")
        embedded_scripts_raw = [self.body.find("script", {"type": "application/ld+json"}).string]
        for script in self.body.find_all('script'):
            try:
                album_info = script['data-tralbum']
                embedded_scripts_raw.append(album_info)
            except Exception:
                continue
        for script in embedded_scripts_raw:
            js_data = self.js_to_json(script)
            self.json_data.append(js_data)

    def js_to_json(self, js_data):
        """Convert JavaScript dictionary to JSON"""
        self.logger.debug(" Converting JS to JSON..")
        # Decode with demjson first to reformat keys and lists
        decoded_js = demjson3.decode(js_data)
        return demjson3.encode(decoded_js)
