# -*- coding: utf-8 -*-
import base64
import os
import nltk
import requests

from bs4 import BeautifulSoup

class Artist(object):
    def __init__(self):
        self.artist_name = None
        self.artist_uri = None
        self.albums = None
        # can contain array with dicts containing track_uri, track_name and valence
        self.tracks = None


class Genius(object):
    def _get(self, url, payload=None, web=False):
        """
        Generalized get function to access endpoints or web page
        :param url: url specifying endpoint e. g. https://api.spotify.com/v1/audio-features/{id}
        :param payload: parameters e.g. {q:'albums'}
        :return: json: response as json.
        """
        headers = {'Authorization': 'Bearer {}'.format(self.client_access_token),
                   'user-agent': 'curl/7.9.8 (i686-pc-linux-gnu) \
                    libcurl 7.9.8 (OpenSSL 0.9.6b) (ipv6 enabled)'
                   }
        if web is True:
            r = requests.get(url, params=payload, headers=headers)
        else:
            r = requests.get(self.api_endpoint.format(url), params=payload, headers=headers)

        if r.status_code == requests.codes.ok:
            if web is True:
                return r
            else:
                return r.json()
        else:
            raise RuntimeError()

    def genius_get_lyric_features(self, tracks, artist_name):
        track_name = [track['track_name'] for track in tracks]

        for track in track_name:
            params = {'q': track + '&' + artist_name}
            url = 'search'
            json = self._get(url, params)["response"]["hits"][0]["result"]
            if str.lower(json['primary_artist']['name']) == str.lower(artist_name):
                lyric_url = json['url']
                lyrics = self._get(lyric_url, None, True)
                soup = BeautifulSoup(lyrics.text, 'html.parser')
                lyric_text = soup.find("lyrics").get_text()
                print(lyric_text)
                print(self.lyric_analysis(lyric_text))
            # on error return sadness score of 0 = Not sad
            else:
                print(0)

    def lyric_analysis(self, lyrics):
        """
        Method returns train.txt file to to dictionary, tokenizes lyrics text
        and runs it against dictionary. lyrical_sadness is calculated from total
        count of sad words in relation to total word count. Plurals currently not
        supported.
        :param lyrics:
        :return: lyrical_sadness
        """

        # tokenize text, look up in dict
        tokenizer = nltk.RegexpTokenizer(r'\w+')
        tokens = tokenizer.tokenize(lyrics)
        word_count = max(len(tokens), 1)
        sad_count = 0

        # search for word in dictionary, increase sad_count for match
        for word in tokens:
            if str.lower(word) in self.dictionary:
                sad_count += 1
        return sad_count / word_count

    def __init__(self):
        self.api_endpoint = 'http://api.genius.com/{}'
        # set Keys for Genius API-Requests
        try:
            self.client_access_token = os.environ["CLIENT_ACCESS_TOKEN"]
            # open sad dictionary
            self.dictionary = {}
            with open("train.txt") as f:
                for line in f:
                    (key, val) = line.split()
                    self.dictionary[key] = val
        except KeyError:
            raise RuntimeError("client_data not set")


class Spotify(object):
    def _get(self, url, payload=None):
        """
        Generalized get function to access endpoints
        :param url: url specifying endpoint e. g. https://api.spotify.com/v1/audio-features/{id}
        :param payload: parameters e.g. {q:'albums'}
        :return: json: response as json.
        """
        headers = {'Accept': 'application/json'}
        r = requests.get(self.api_endpoint.format(url), params=payload, headers=headers)
        if r.status_code == requests.codes.ok:
            return r.json()
        else:
            raise RuntimeError()

    def _authenticate(self):
        """
        authenticate function to obtain access token. spotify_client_id and spotifiy_client_secret
        must be set. Token can expire. Only some API queries require token.
        :return:
        """
        auth_header = base64.b64encode((self.spotify_client_id + ':' + self.spotify_client_secret).encode('ascii'))
        headers = {'Authorization': 'Basic {}'.format(auth_header.decode('ascii'))}
        payload = {'grant_type': 'client_credentials'}
        r = requests.post('https://accounts.spotify.com/api/token', data=payload, headers=headers, verify=True)
        if r.status_code is not 200:
            raise RuntimeError(r.reason)
        return r.json()['access_token']

    def spotify_get_artist(self, artist_name):
        """
        Search for artist_uri by artist name.
        :param artist_name:
        :return: artist: containing artist_uri, and artist_name
        """
        params = {'q': artist_name, 'type': 'artist'}
        # search response for artist name and uri
        json = self._get('search', params)['artists']["items"]
        artists = [{'artist_name': i['name'], 'artist_uri': str.replace(i['uri'], 'spotify:artist:', '')}
                   for i in json]

        # return 1:1 match in seed_artists list, strings are lowercase
        return [artist for artist in artists
                if str.lower(artist['artist_name']) == str.lower(artist_name)][0]

    def spotify_get_albums(self, artist_uri):
        """
        Search for all albums, not singles etc. for given artist
        :param artist_uri:
        :return: albums: array of albums for given artist
        """
        params = {'album_type': 'album'}
        album_url = "artists/{}/albums".format(artist_uri)

        # extract relevant information
        json = self._get(album_url, params)["items"]
        albums = [{'album_name': i['name'], 'album_uri': str.replace(i['uri'], 'spotify:album:', '')}
                  for i in json]
        return albums

    def spotify_get_album_tracks(self, albums):
        """
        Query tracks for given album array. At maximum 50 tracks can be searched,
         due to restrictions of the spotify API.
        :param albums:
        :return: tracks: array with tracks for ALL albums
        """
        access_token = self._authenticate()
        album_uri = [album['album_uri'] for album in albums]
        tracks = []
        # search for track_uri
        for i in album_uri:
            params = {'access_token': access_token, 'limit': 50}
            url = "albums/{}/tracks".format(i)
            json = self._get(url, params)['items']
            tracks_per_album = [{'track_name': i['name'], 'track_uri': str.replace(i['uri'],
                                'spotify:track:', '')} for i in json]
            tracks += tracks_per_album
        return tracks

    def spotify_get_audio_features(self, tracks):
        """
        Get valence score for tracks list, append it to each dictionary.
        :param tracks: tracks array containing track's name and uri.
        :return: tracks: tracks including valence score.
        """
        access_token = self._authenticate()
        track_uri = [track['track_uri'] for track in tracks]
        audio_features = []
        for i in track_uri:
            params = {'access_token': access_token}
            url = "audio-features/{}".format(i)
            json = self._get(url, params)['valence']
            audio_features += [json]

        for index, item in enumerate(tracks):
            tracks[index]['valence'] = audio_features[index]
        return tracks

    def __init__(self):
        self.api_endpoint = 'https://api.spotify.com/v1/{}'
        # set Keys for Genius API-Requests
        try:
            self.spotify_client_secret = os.environ["SPOTIFY_CLIENT_SECRET"]
            self.spotify_client_id = os.environ["SPOTIFY_CLIENT_ID"]
        except KeyError:
            raise RuntimeError("client_data not set")

    def main(self):

        artist = Artist()

        # spotify api queries
        """
        spotify_artist = self.spotify_get_artist("The Rasmus")
        artist.artist_name = spotify_artist['artist_name']
        artist.artist_uri = spotify_artist['artist_uri']
        artist.albums = self.spotify_get_albums(artist.artist_uri)
        artist.tracks = self.spotify_get_album_tracks(artist.albums)
        artist.tracks = self.spotify_get_audio_features(artist.tracks)
        """

        # genius api queries
        genius = Genius()
        artist.tracks = [{'track_name': 'In the shadows'}]
        artist.artist_name = 'The Rasmus'
        genius.genius_get_lyric_features(artist.tracks, artist.artist_name)
        print(vars(artist))


custom_spotify = Spotify()
custom_spotify.main()
