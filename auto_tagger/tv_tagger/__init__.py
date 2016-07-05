
import glob
import logging
import os
import re
import subprocess
import sys
import textwrap

import requests


TVDB_API = 'https://api.thetvdb.com'


class TVTagger(object):
  def __init__(self):
    self._init_logger()
    self._verify_api_key_exists()
    self._login_and_set_headers()

  def _init_logger(self):
    formatter = logging.Formatter('%(asctime)s %(levelname)s: %(message)s')
    self.logger = logging.getLogger('auto_tagger')
    self.logger.setLevel(logging.INFO)
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    self.logger.addHandler(handler)

  def _verify_api_key_exists(self):
    if 'TVDB_API_KEY' not in globals():
      if os.environ.get('TVDB_API_KEY'):
        global TVDB_API_KEY
        TVDB_API_KEY = os.environ.get('TVDB_API_KEY')
      else:
        self.logger.error('TVDB_API_KEY is not set.')
        sys.exit(1)

  def _login_and_set_headers(self):
    self.headers = {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
    }
    r = requests.post('%s/login' % TVDB_API,
                      data='{"apikey": "%s"}' % TVDB_API_KEY,
                      headers=self.headers)
    if r.status_code != 200:
      self.logger.error('error logging in: %d: %s', r.status_code, r.text)
      sys.exit(1)
    self.headers['Authorization'] = 'Bearer %s' % r.json().get('token')

  def _get_show_details(self, show_name):
    r = requests.get('%s/search/series' % TVDB_API,
                     params={'name': show_name},
                     headers=self.headers)

    if r.status_code != 200:
      if r.status_code == 404:
        self.logger.error('show not found, exiting')
      else:
        self.logger.error('unexpected error: %d: %s', r.status_code, r.text)
      sys.exit(1)

    shows_found = r.json().get('data')

    if len(shows_found) > 1:
      shows_by_id = {}

      self.logger.warning('multiple shows matching name %s were found', show_name)
      for match in shows_found:
        lead = '%d: %s (%s, %s):' % (match.get('id'),
                                     match.get('seriesName'),
                                     match.get('network'),
                                     match.get('firstAired'))
        show_text = '%s %s' % (lead, match.get('overview'))
        fill = ' '.rjust(len(lead)+1)
        wrapper = textwrap.TextWrapper(width=150, subsequent_indent=fill)
        print wrapper.fill(show_text)
        print ''

        shows_by_id[str(match.get('id'))] = match

      match_id = raw_input('Enter the ID of the correct match, or "q" to exit: ')
      if match_id == 'q':
        self.logger.error('aborting')
        sys.exit(1)

      return shows_by_id[match_id]

    return shows_found[0]

  def _get_title_card_image(self, show_dir):
    possible_titles = glob.glob(os.path.join(show_dir, 'title.*'))
    if not possible_titles:
      self.logger.error('no title card image was found. exiting.')
      sys.exit(1)

    title_card = possible_titles[0]
    if os.path.splitext(title_card)[1] not in ('.jpg', '.png'):
      self.logger.error('found title card image %s but it is not a jpg '
                        'or png.', title_card)
      sys.exit(1)

    return title_card

  def _get_series_episodes(self, series_id, show_name):
    last_page = None
    current_page = 1

    episodes = {}

    while last_page is None or current_page <= last_page:
      r = requests.get('%s/series/%d/episodes' % (TVDB_API, series_id),
                       params={'page':current_page}, headers=self.headers)
      if r.status_code != 200:
        self.logger.error('error getting episodes for series %d page %d: %d: %s',
                          series_id, current_page, r.status_code, r.text)
        sys.exit(1)

      if last_page is None:
        last_page = r.json().get('links').get('last')

      for ep_details in r.json().get('data'):
        if str(ep_details.get('airedSeason')) not in episodes:
          episodes[str(ep_details.get('airedSeason'))] = []
        episodes[str(ep_details.get('airedSeason'))].append(
            Episode(ep_details.get('id'),
                    show_name,
                    int(ep_details.get('airedSeason')),
                    int(ep_details.get('airedEpisodeNumber')),
                    ep_details.get('episodeName')))

      current_page += 1

    return episodes

  def _add_to_library(self, ep_filepath, ep, title_card):
    script_path = os.path.join(os.path.abspath(os.path.dirname(__file__)),
                               'add_to_library_and_tag_tv_show.scpt')
    cmd = ['osascript', script_path, ep_filepath, ep.show_name,
           str(ep.season_num), str(ep.ep_num), unicode(ep), title_card]
    print cmd
    #return
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = p.communicate()
    if p.returncode:
      self.logger.error('error adding episode to library. rc: %d, stdout: %s, stderr: %s',
                        p.returncode, out, err)
      sys.exit(1)

  def add_to_library_and_tag(self, show_dir):
    dir_split = show_dir.rstrip('/').split('/')
    show_name_from_dir = dir_split[-1]
    self.logger.info('detected show name "%s"', show_name_from_dir)

    show_details = self._get_show_details(show_name_from_dir)
    self.logger.info('found show "%s", ID %d',
                     show_details.get('seriesName'), show_details.get('id'))

    title_card = self._get_title_card_image(show_dir)
    self.logger.info('found title card image %s', title_card)

    episodes = self._get_series_episodes(show_details.get('id'), show_name_from_dir)

    for child_dirname in os.listdir(show_dir):
      season_dir = os.path.join(show_dir, child_dirname)
      if not os.path.isdir(season_dir):
        continue

      self.logger.info('found season directory %s', season_dir)

      season_num_from_dir = int(child_dirname.split()[-1])
      self.logger.info('determined season number %d', season_num_from_dir)

      # check TVDB for that episode, error if not found
      season_eps = episodes.get(str(season_num_from_dir))
      if not season_eps:
        self.logger.error('no episodes were found in TVDB for season %d',
                          season_num_from_dir)
        sys.exit(1)

      for ep_filename in os.listdir(season_dir):
        match = re.search(r'S(?P<season>\d{1,2})E(?P<episode>\d{1,2})',
                          ep_filename)
        if not match:
          continue

        if os.path.splitext(ep_filename)[1] not in ('.m4v', '.mp4'):
          continue

        self.logger.info('found episode %s', ep_filename)

        season_num_from_file = int(match.group('season'))
        ep_num_from_file = int(match.group('episode'))

        self.logger.info('detected season number %d and episode number %d',
                         season_num_from_file, ep_num_from_file)

        if season_num_from_file != season_num_from_dir:
          self.logger.error('season number for file %s is %d, does not match directory season %d',
                            ep_filename, season_num_from_file, season_num_from_dir)

        for ep in season_eps:
          if ep.ep_num == ep_num_from_file:
            break
        else:
          self.logger.error('episode %d was not found in TVDB', ep_num_from_file)
          sys.exit(1)

        self.logger.info('found episode in TVDB %s', ep)

        self._add_to_library(os.path.join(season_dir, ep_filename), ep, title_card)
        self.logger.info('added to library')


class Episode(object):
  def __init__(self, id, show_name, season_num, ep_num, title):
    self.id = id
    self.show_name = show_name
    self.season_num = season_num
    self.ep_num = ep_num
    self.title = title

  def __str__(self):
    return '%s - S%02dE%02d - %s' % (self.show_name, self.season_num,
                                     self.ep_num, self.title)

  def __repr__(self):
    return self.__str__()
