# -*- coding: utf-8 -*-
import base64
import os

import nltk
import requests
import six
from selenium import webdriver

class Artist(object):
    def __init__(self):
        self.artist_name = None
        self.artist_uri = None
        self.albums = None
        self.tracks = None

class Spotify(object):

    def _get(self, url, payload=None, **kwargs):
        headers = {'Accept': 'application/json'}
        r = requests.get(self.api_endpoint.format(url), params=payload, headers=headers)
        if r.status_code == requests.codes.ok:
            return r.json()
        else:
            return None


    def spotify_get_artist(self, artist_name):
        params = {'q': artist_name, 'type': 'artist'}
        # search response for artist name and uri
        json = self._get('search', params)['artists']["items"]
        seed_artists = [{'artist_name': i['name'], 'artist_uri': str.replace(i['uri'], 'spotify:artist:', '')} for i in
                        json]

        # return first match from seed_artists, assume its best.
        return [seed_artist for seed_artist in seed_artists if seed_artist['artist_name'] == artist_name][0]


    def spotify_get_album_id(self, artist):

        params = {'album_type': 'album'}
        album_url = "artists/{}/albums".format(artist['artist_uri'])

        # extract relevant information
        json = self._get(album_url, params)["items"]
        seed_albums = [{'album_name': i['name'], 'album_uri': str.replace(i['uri'], 'spotify:album:', '')}
                       for i in json]

        # save albums name and uri to different lists
        # artist['album_name'] = [albums['album_name'] for albums in seed_albums]
        # artist['album_uri'] = [albums['album_uri'] for albums in seed_albums]
        artist['albums'] = seed_albums
        return artist


    def _authenticate(self):
        # todo: handle refreshing of token better...
        auth_header = base64.b64encode(six.text_type(self.spotify_client_id + ':' + self.spotify_client_secret).encode('ascii'))
        headers = {'Authorization': 'Basic %s' % auth_header.decode('ascii')}
        payload = {'grant_type': 'client_credentials'}
        r = requests.post('https://accounts.spotify.com/api/token', data=payload, headers=headers, verify=True)
        if r.status_code is not 200:
            raise RuntimeError(r.reason)
        return r.json()['access_token']


    def spotify_get_album_tracks(self, artist):
        """ max. 50 tracks per Album ....
        """

        access_token = self._authenticate()
        album_uri = artist['album_uri']
        seed_tracks = []

        # search for track_uri
        for i in album_uri:
            params = {'access_token': access_token, 'limit': 50}
            headers = {'Accept': 'application/json'}
            url = "https://api.spotify.com/v1/albums/{}/tracks".format(i)
            r = requests.get(url, params=params, headers=headers)
            json = r.json()['items']
            tracks_per_album = [{'track_name': i['name'], 'track_uri': str.replace(i['uri'],
                                                                                   'spotify:track:', '')} for i in json]
            seed_tracks += tracks_per_album

        # save to two arrays
        artist['track_name'] = [tracks['track_name'] for tracks in seed_tracks]
        artist['track_uri'] = [tracks['track_uri'] for tracks in seed_tracks]
        return artist


    def spotify_get_audio_features(self, artist):
        access_token = self._authenticate()
        track_uri = artist['track_uri']
        seed_audio_features = []
        for i in track_uri:
            params = {'access_token': access_token}
            headers = {'Accept': 'application/json'}
            url = "https://api.spotify.com/v1/audio-features/{}".format(i)
            r = requests.get(url, params=params, headers=headers)
            json = r.json()
            seed_audio_features += [json['valence']]
        artist['track_valence'] = seed_audio_features
        return artist


    def genius_get_artist(self, artist_name, access_token):
        """
        Function returns genius primary artist's id given name
        :param artist_name: Artist's name e.g. Adele
        :param access_token: access_token for API query
        :return: artist_id: Genius ID for given artist.
        """
        # todo: simplify: crawl for first match only. Assume this is best match
        page = 1

        while page <= 1:
            params = {'q': artist_name, 'page': page}

            # user-agent is required otherwise 403
            headers = {'Authorization': 'Bearer ' + access_token,
                       'user-agent': 'curl/7.9.8 (i686-pc-linux-gnu) \
                        libcurl 7.9.8 (OpenSSL 0.9.6b) (ipv6 enabled)'}

            response = requests.get('https://api.genius.com/search',
                                    params=params, headers=headers)

            json = response.json()
            result = json['response']['hits'][0]['result']

            # return the first primary_artist id and name as a dict, otherwise None
            # for more results use 'for result in body' and save to list
            artist_id = result['primary_artist']['id']
            page += 1
        return artist_id


    def genius_get_lyrics(self, artist_id, access_token):
        """
        Function returns a list of songs for a given artist.
        :param artist_id: artist id e.g. 640 for Adele
        :param access_token: access token for API query
        :return: list with downloaded data. Contains url, title etc.
        """
        url = "https://api.genius.com/artists/{}/songs".format(artist_id)
        # user-agent is required otherwise 403
        headers = {'Authorization': 'Bearer ' + access_token,
                   'user-agent': 'curl/7.9.8 (i686-pc-linux-gnu) \
                            libcurl 7.9.8 (OpenSSL 0.9.6b) (ipv6 enabled)'}

        # array for results, start with page 1
        track_lyric_urls = []
        page = 1

        while True:
            # limit is 50
            params = {'per_page': 50, 'page': page}
            response = requests.get(url=url,
                                    headers=headers, params=params)
            json = response.json()
            response = json['response']
            track_lyric_urls.append(response['songs'][0])
            # break if there are no more pages to parse
            if response['next_page'] is not None:
                page = response['next_page']
            else:
                break
        return track_lyric_urls


    def lyric_scraper(self, url):
        """
        function crawls web page by given url. PhantomJS or any other web browser
        is required as website is loaded using javascript. Copy PhantomJS executable to
        /usr/local/bin/. PhantomJS executable can be downloaded from http://phantomjs.org/
        :param url: Search url
        :return: lyrics: String with lyrics from crawled webpage
        """

        driver = webdriver.PhantomJS()
        driver.get(url)
        lyrics = driver.find_element_by_class_name('lyrics').text
        return lyrics


    def lyric_analysis(self, lyrics):
        """
        Method returns train.txt file to to dictionary, tokenizes lyrics text
        and runs it against dictionary. lyrical_sadness is calculated from total
        count of sad words in relation to total word count.
        :param lyrics:
        :return: lyrical_sadness
        """
        # open sad dictionary
        dictionary = {}
        with open("train.txt") as f:
            for line in f:
                (key, val) = line.split()
                dictionary[key] = val

        # tokenize text, look up in dict
        tokenizer = nltk.RegexpTokenizer(r'\w+')
        tokens = tokenizer.tokenize(lyrics)
        print(tokens)
        word_count = max(len(tokens), 1)
        sad_count = 0

        for word in tokens:
            if str.lower(word) in dictionary:
                sad_count += 1
        return sad_count / word_count

    def __init__(self):
        self.api_endpoint = 'https://api.spotify.com/v1/{}'
        # set Keys for Genius API-Requests
        try:
            self.client_id = os.environ["CLIENT_ID"]
            self.client_secret = os.environ["CLIENT_SECRET"]
            self.client_access_token = os.environ["CLIENT_ACCESS_TOKEN"]
            self.spotify_client_secret = os.environ["SPOTIFY_CLIENT_SECRET"]
            self.spotify_client_id = os.environ["SPOTIFY_CLIENT_ID"]
        except KeyError:
            raise RuntimeError("client_data not set")


    def main(self):
        """
        search_term = 'Adele'
        print('fetch artist_id...')
        artist_id = genius_get_artist(search_term, client_access_token)
        print('fetch track-lyric_urls...')
        track_lyric_urls = genius_get_lyrics(artist_id, client_access_token)
        print('scrape lyrics from url...')
        lyrics = lyric_scraper(track_lyric_urls[0]['url'])
        print(lyrics)
        lyric_analysis(lyrics)
        """
        artist = Artist()
        spotify_artist = self.spotify_get_artist("The Rasmus")
        artist.artist_name = spotify_artist['artist_name']
        artist.artist_uri = spotify_artist['artist_uri']


        print(vars(artist))

        # albums = self.spotify_get_album_id(artist)
        # print(albums)
        """
        tracks = spotify_get_album_tracks(albums)
        saddest_song = spotify_get_audio_features(tracks)
        """
        """
        # Test for Eminem, loose yourself
        lyrics = "The clock's run out, time's up, over, bloah!"
        print(lyric_analysis(lyrics))
        """

custom_spotify = Spotify()
custom_spotify.main()
