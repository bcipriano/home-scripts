#!/usr/bin/env python
"""
Tags media by querying the TVDB API.
"""


import argparse
import glob
import logging
import os
import pprint
import re
import subprocess
import sys
import textwrap

import requests


TVDB_API = 'https://api.thetvdb.com'


def _get_logger():
  formatter = logging.Formatter('%(asctime)s %(levelname)s: %(message)s')
  logger = logging.getLogger('auto_tagger')
  logger.setLevel(logging.INFO)
  handler = logging.StreamHandler()
  handler.setFormatter(formatter)
  logger.addHandler(handler)
  return logger


def _verify_api_key_exists(logger):
  if 'TVDB_API_KEY' not in globals():
    if os.environ.get('TVDB_API_KEY'):
      global TVDB_API_KEY
      TVDB_API_KEY = os.environ.get('TVDB_API_KEY')
    else:
      logger.error('TVDB_API_KEY is not set.')
      sys.exit(1)


def _login_and_get_headers(logger):
  headers = {
    'Content-Type': 'application/json',
    'Accept': 'application/json',
  }

  r = requests.post('%s/login' % TVDB_API,
                    data='{"apikey": "%s"}' % TVDB_API_KEY,
                    headers=headers)
  if r.status_code != 200:
    logger.error('error logging in: %d: %s' % (r.status_code, r.text))
    sys.exit(1)

  headers['Authorization'] = 'Bearer %s' % r.json().get('token')
  return headers


def _get_show_details(show_name, headers, logger):
  r = requests.get('%s/search/series' % TVDB_API,
                   params={'name': show_name},
                   headers=headers)

  if r.status_code != 200:
    if r.status_code == 404:
      logger.error('show not found, exiting')
    else:
      logger.error('unexpected error: %d: %s' % (r.status_code, r.text))
    sys.exit(1)

  shows_found = r.json().get('data')

  if len(shows_found) > 1:
    shows_by_id = {}

    logger.warning('multiple shows matching name %s were found' % show_name)
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
      logger.error('aborting')
      sys.exit(1)

    return shows_by_id[match_id]

  return shows_found[0]


def _get_title_card_image(show_dir, logger):
  possible_titles = glob.glob(os.path.join(show_dir, 'title.*'))
  if not possible_titles:
    logger.error('no title card image was found. exiting.')
    sys.exit(1)

  title_card = possible_titles[0]
  if os.path.splitext(title_card)[1] not in ('.jpg', '.png'):
    logger.error(('found title card image %s but it is not a jpg '
                  'or png.') % title_card)
    sys.exit(1)

  return title_card


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


def _get_series_episodes(series_id, show_name, headers):
  last_page = None
  current_page = 1

  episodes = {}

  while last_page is None or current_page <= last_page:
    r = requests.get('%s/series/%d/episodes' % (TVDB_API, series_id),
                     params={'page':current_page}, headers=headers)
    if r.status_code != 200:
      logger.error(('error getting episodes for series %d page %d: '
                    '%d: %s') % (series_id, current_page,
                                 r.status_code, r.text))
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


def _add_to_library(ep_filepath, ep, title_card):
  script_path = os.path.join(os.path.abspath(os.path.dirname(__file__)),
                             'add_to_library_and_tag_tv_show.scpt')
  cmd = ['osascript', script_path, ep_filepath, ep.show_name,
         str(ep.season_num), str(ep.ep_num), str(ep), title_card]
  p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
  out, err = p.communicate()
  if p.returncode:
    logger.error(('error adding episode to library. rc: %d, stdout: %s, '
                  'stderr: %s') % (p.returncode, out, err))
    sys.exit(1)


def main():
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument('--show-dir', required=True, help=('Directory containing '
                                                         'media.'))
  args = parser.parse_args()

  logger = _get_logger()
  _verify_api_key_exists(logger)
  headers = _login_and_get_headers(logger)

  dir_split = args.show_dir.rstrip('/').split('/')
  show_name_from_dir = dir_split[-1]
  logger.info('detected show name "%s"' % show_name_from_dir)

  show_details = _get_show_details(show_name_from_dir, headers, logger)
  logger.info('found show "%s", ID %d' % (show_details.get('seriesName'),
                                          show_details.get('id')))

  title_card = _get_title_card_image(args.show_dir, logger)
  logger.info('found title card image %s' % title_card)

  episodes = _get_series_episodes(show_details.get('id'), show_name_from_dir,
                                  headers)

  for child_dirname in os.listdir(args.show_dir):
    season_dir = os.path.join(args.show_dir, child_dirname)
    if not os.path.isdir(season_dir):
      continue

    logger.info('found season directory %s' % season_dir)

    season_num_from_dir = int(child_dirname.split()[-1])
    logger.info('determined season number %d' % season_num_from_dir)

    # check TVDB for that episode, error if not found
    season_eps = episodes.get(str(season_num_from_dir))
    if not season_eps:
      logger.error(('no episodes were found in TVDB for season '
                    '%d') % season_num_from_dir)
      sys.exit(1)

    for ep_filename in os.listdir(season_dir):
      match = re.search(r'S(?P<season>\d{1,2})E(?P<episode>\d{1,2})',
                        ep_filename)
      if not match:
        continue

      if os.path.splitext(ep_filename)[1] not in ('.m4v', '.mp4'):
        continue

      logger.info('found episode %s' % ep_filename)

      season_num_from_file = int(match.group('season'))
      ep_num_from_file = int(match.group('episode'))

      logger.info('detected season number %d and episode number %d' % (
          season_num_from_file, ep_num_from_file))

      if season_num_from_file != season_num_from_dir:
        logger.error(('season number for file %s is %d, does not match '
                      'directory season %d') % (ep_filename,
                                                season_num_from_file,
                                                season_num_from_dir))

      for ep in season_eps:
        if ep.ep_num == ep_num_from_file:
          break
      else:
        logger.error('episode %d was not found in TVDB' % ep_num_from_file)
        sys.exit(1)

      logger.info('found episode in TVDB %s' % ep)

      _add_to_library(os.path.join(season_dir, ep_filename), ep, title_card)
      logger.info('added to library')


if __name__ == '__main__':
  main()
