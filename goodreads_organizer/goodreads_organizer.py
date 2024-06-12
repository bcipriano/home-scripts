#!/usr/bin/env python
"""
Organize your book collection using Goodreads data.

Currently sorts by author and date of author's first published work.

The Goodreads API has been deprecated, so this requires a manual
export of your Goodreads data.

To use:
1. Go to Goodreads and export your books list: https://www.goodreads.com/review/import
2. Place the downloaded file in the same directory as this script.
3. Run the script:
   ```
   $ python goodreads_organizer.py
   ```
"""

import argparse
import csv
import os

class Book(object):
  def __init__(self, title, pub_date):
    self.title = title
    self.pub_date = pub_date

  def __cmp__(self, other):
    return self.pub_date - other.pub_date

  def __lt__(self, other):
    return self.pub_date < other.pub_date

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

  def __lt__(self, other):
    return self.get_earliest_pub_date() < other.get_earliest_pub_date()

  def __str__(self):
    return self.name

  def add_book(self, book_title, book_pub_date):
    self.books.append(Book(book_title, book_pub_date))
    self.books.sort()

  def get_earliest_pub_date(self):
    return self.books[0].pub_date


def main():
  parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
  parser.parse_args()

  goodreads_export_csv = os.path.join(os.path.dirname(__file__), 'goodreads_library_export.csv')

  if not os.path.exists(goodreads_export_csv):
    print('Goodreads CSV export does not exist at path %s' % goodreads_export_csv)

  with open(goodreads_export_csv) as fp:
    book_data = [{k: v for k, v in row.items()}
         for row in csv.DictReader(fp, skipinitialspace=True)]
  print('Goodreads data read from %s' % goodreads_export_csv)

  user_books = []
  for book in book_data:
    if book['Exclusive Shelf'] == 'read':
      user_books.append(book)

  print('Found %d books' % len(user_books))

  authors_by_id = {}
  for book_num, shelf_book in enumerate(user_books):
    author_id = shelf_book['Author']
    if author_id not in authors_by_id:
      authors_by_id[author_id] = AuthorBlock(
          shelf_book['Author'],
          shelf_book['Author'])
    authors_by_id[author_id].add_book(
      shelf_book['Title'],
      int(shelf_book['Original Publication Year']))

  print('Done grouping books by author.')

  authors_list = [a for a in authors_by_id.values()]
  authors_list.sort()

  print('Done sorting books list.')
  print('Final list:')

  for author in authors_list:
    print(author)
    for book in author.books:
      print('  %s' % book)

if __name__ == '__main__':
  main()
