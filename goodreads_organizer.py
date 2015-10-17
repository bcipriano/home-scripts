#!/usr/bin/env python
"""
Use the Goodreads API to organize your book collection.

Currently sorts by author and date of author's first published work.

Requirements:
- The goodreads Python API wrapper from sefakilic: https://github.com/sefakilic/goodreads. 
  Must be available in import path, so either install it systemwide or place in the same folder as this script.
- Create a file called gr_config.py to live in the same folder as this script.
  Define GR_KEY and GR_SECRET values in that file, these must correspond to your
  Goodreads Developer Key and Secret. 

"""

import argparse
import sys

from goodreads import client

import gr_config

class Book(object):
  def __init__(self, title, pub_date):
    self.title = title
    self.pub_date = pub_date

  def __cmp__(self, other):
    return self.pub_date - other.pub_date

  def __str__(self):
    return '%s (%s)' % (self.title, self.pub_date)

  def __repr__(self):
    return self.__str__()


class AuthorBlock(object):
  def __init__(self, id, name):
    self.id = id
    self.name = name
    self.books = []

  def __cmp__(self, other):
    return self.get_earliest_pub_date() - other.get_earliest_pub_date()

  def __str__(self):
    return self.name.encode('utf-8')

  def __repr__(self):
    return self.__str__()

  def add_book(self, book_title, book_pub_date):
    self.books.append(Book(book_title, book_pub_date))
    self.books.sort()

  def get_earliest_pub_date(self):
    return self.books[0].pub_date


def main():
  parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
  parser.parse_args()

  sys.stdout.write('Authorizing, close browser window when done\n')

  # Authenticate with Goodreads
  gc = client.GoodreadsClient(gr_config.GR_KEY, gr_config.GR_SECRET)
  gc.authenticate()
  # Get authenticated user
  user = gc.user()

  sys.stdout.write('Gathering book list...')
  sys.stdout.flush()

  # We're going to look through reviews for all books in the
  # "read" shelf and flatten that list.
  user_books = []
  page_num = 0
  while True:
    page_num += 1
    try:
      for review_num, review in enumerate(user.reviews(page=page_num)):
        if 'read' in review.shelves:
          user_books.append(review.book)
    except KeyError as e:
      if e.message.lower() == 'review':
        break
      raise

  sys.stdout.write('found %d books\n' % len(user_books))

  authors_by_id = {}

  for book_num, shelf_book in enumerate(user_books):
    sys.stdout.write('\rGrouping books by author...%d%%' % int(float(book_num) / len(user_books) * 100))
    sys.stdout.flush()
    author_id = shelf_book['authors']['author']['id']
    if author_id not in authors_by_id:
      authors_by_id[author_id] = AuthorBlock(
          shelf_book['authors']['author']['id'], 
          shelf_book['authors']['author']['name'])
    pub_date_response = gc.request('/book/show.xml', {
        'id': shelf_book['id']['#text']
    })
    if '#text' in pub_date_response['book']['work']['original_publication_year']:
      pub_year = int(pub_date_response['book']['work']['original_publication_year']['#text'])
    elif '@nil' in pub_date_response['book']['work']['original_publication_year']:
      pub_year = int(pub_date_response['book']['publication_year'])
    else:
      raise Exception('invalid response for book %s: %s' % (shelf_book['title'], str(pub_date_response)))
    authors_by_id[author_id].add_book(shelf_book['title'], pub_year)

  sys.stdout.write('\rGrouping books by author...done.\n')

  sys.stdout.write('Sorting...')
  sys.stdout.flush()

  authors_list = [a for a in authors_by_id.itervalues()]
  authors_list.sort()

  sys.stdout.write('done.\n')

  sys.stdout.write('Final list:\n')

  for author in authors_list:
    print author
    for book in author.books:
      print '  %s' % book

if __name__ == '__main__':
  main()
