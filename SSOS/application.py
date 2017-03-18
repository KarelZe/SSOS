# -*- coding: utf-8 -*-
import os
import requests
from selenium import webdriver

# set Keys for Genius API-Requests
try:
    client_id = os.environ["CLIENT_ID"]
    client_secret = os.environ["CLIENT_SECRET"]
    client_access_token = os.environ["CLIENT_ACCESS_TOKEN"]
except KeyError:
    raise RuntimeError("client_data not set")


def genius_get_artists(search_term, access_token):
    """
    Function returns genius primary artist's id given name
    :param search_term: Artist's name e.g. Adele
    :param access_token: access_token for API query
    :return: artist_id: Genius ID for given artist.
    """
    # todo: simplify: crawl for first match only. Assume this is best match
    page = 1

    while page <= 1:
        params = {'q': search_term, 'page': page}

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
        # name = result['primary_artist']['name']
        # artist = {'id': id, 'name': name}
        page += 1
    return artist_id


def genius_get_lyrics(artist_id, access_token):
    """
    Function returns a list of songs for a given artist.
    :param artist_id: artist id e.g. 640 for Adele
    :param access_token: access token for API query
    :return: list with downloaded data. Contains url, title etc.
    """
    # todo: improve url chaining
    url = requests.compat.urljoin('https://api.genius.com/artists/',
                                  str(artist_id) + '/songs')

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
        response = requests.get(url=url, headers=headers, params=params)
        json = response.json()
        response = json['response']
        track_lyric_urls.append(response['songs'][0])
        # break if there are no more pages to parse
        if response['next_page'] is not None:
            page = response['next_page']
        else:
            break
    return track_lyric_urls


def lyric_scraper(url):
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


def main():
    search_term = 'Radiohead'
    print('fetch artist_id...')
    artist_id = genius_get_artists(search_term, client_access_token)
    print('fetch track-lyric_urls...')
    track_lyric_urls = genius_get_lyrics(artist_id, client_access_token)
    print('scrape lyrics from url...')
    lyrics = lyric_scraper(track_lyric_urls[0]['url'])
    print(lyrics)


if __name__ == '__main__':
    main()
