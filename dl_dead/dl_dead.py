#!/usr/bin/env python
"""
Downloads Grateful Dead shows from archive.org.

Provide a link to the URL of the "details" page, for example:

$ ./dl_dead.py https://archive.org/details/gd71-12-10.shnf

NOTE from Brian:
This script is now mostly defunct, as archive.org no longer allows downloading of most
soundboard shows. If used it should only be used to download freely available shows.
"""

import argparse
import os
import sys
import urllib

import requests

DL_CHUNK_SIZE = 1024

def main():
  parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
  parser.add_argument('show_url', help='URL of the show\'s "details" page')
  parser.add_argument('dest_dir', help='directory to download to')
  args = parser.parse_args()

  print('downloading show from %s' % args.show_url)

  show_url = urllib.parse.urlparse(args.show_url)
  archive_root = '%s://%s' % (show_url.scheme, show_url.netloc)
  print('archive root %s' % archive_root)

  # get page source
  details_src = requests.get(args.show_url).text

  # find m3u file
  m3u_path = None
  for src_line in details_src.split('\n'):
    if '.m3u' in src_line:
      href = src_line.find('href=')
      first_quote = src_line.find('"', href)
      second_quote = src_line.find('"', first_quote+1)
      m3u_path = src_line[first_quote+1:second_quote]
      break

  if m3u_path is None:
    print('m3u URL was not found')
    sys.exit(1)

  print('found m3u at path %s' % m3u_path)

  # download m3u file
  m3u_url = '%s%s' % (archive_root, m3u_path)
  print('downloading m3u from URL %s' % m3u_url)
  mp3_list = [line.strip() for line in requests.get(m3u_url).text.split('\n') if line.strip()]
  print('found %d files' % len(mp3_list))

  # create output folder
  output_dir = os.path.join(os.path.abspath(args.dest_dir), os.path.basename(show_url.path).split('.')[0])
  print('creating output directory %s' % output_dir)
  if not os.path.exists(output_dir):
    os.makedirs(output_dir)

  # download each song file
  for mp3_num, mp3_url in enumerate(mp3_list):
    print('downloading %d of %d' % (mp3_num+1, len(mp3_list)))
    print('--> src: %s' % mp3_url)
    mp3_dest = os.path.join(output_dir, os.path.basename(urllib.parse.urlparse(mp3_url).path))
    print('--> dest: %s' % mp3_dest)
    mp3_resp = requests.get(mp3_url, stream=True)
    if mp3_resp.status_code == 200:
      total_len = float(mp3_resp.headers.get('content-length'))
      progress = 0
      sys.stdout.write('--> progress: 0%')
      with open(mp3_dest, 'wb') as fp:
        for chunk in mp3_resp.iter_content(DL_CHUNK_SIZE):
          fp.write(chunk)
          progress += DL_CHUNK_SIZE
          sys.stdout.write('\r--> progress: %d%%' % (100 * progress / total_len))
      print('')
    else:
      print('--> error %d: %s' % (mp3_resp.status_code, mp3_resp.text))

  print('done!')

if __name__ == '__main__':
  main()
