#!/usr/bin/env python
"""
Tags media by querying the TVDB API.
"""


import argparse

import tv_tagger


def main():
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument('--show-dir', required=True,
      help='Directory containing media to be tagged.')
  args = parser.parse_args()

  tagger = tv_tagger.TVTagger()
  tagger.add_to_library_and_tag(args.show_dir)


if __name__ == '__main__':
  main()
