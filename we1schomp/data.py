# -*- coding: utf-8 -*-
"""
"""

import html
import json
import os
import string
import sys
import time
from gettext import gettext as _
from logging import getLogger

import bleach
import regex as re
from unidecode import unidecode


def load_articles(path, no_skip=False):
    """
    """

    log = getLogger(__name__)
    articles = []
    count = 0

    log.debug(_('Searching for JSON files in %s.'), path)
    for json_data, json_file in load_json_files_from_path(path):

        # If a file already has stuff in the "content" key, that implies
        # we've already scraped it, so we can safely skip it here.
        if json_data['content'] != '' and not no_skip:
            log.info(_('Skipping: %s'), json_file)
            continue

        # Keep track of how many files we've loaded so we can report how many
        # we've skipped.
        log.info(_('Loading: %s'), json_file)
        count += 1
        articles.append(json_data)

    log.info(_('Found %s files, %s skipped.'), count, len(articles) - count)
    return articles


def load_json_files_from_path(path):
    """
    """

    for json_file in [f for f in os.listdir(path) if f.endswith('.json')]:

        filename = os.path.join(path, json_file)
        with open(filename, 'r', encoding='utf-8') as infile:
            json_data = json.load(infile)

        yield json_data, json_file


def save_article(article, config):
    """
    """

    log = getLogger(__name__)
    path = config['OUTPUT_PATH']

    # Update existing files first.
    filename = ''
    for json_data, json_file in load_json_files_from_path(path):
        if json_data['doc_id'] == article['doc_id']:
            filename = json_file
            log.info(_('Saving (overwrite): %s'), filename)
            break

    # Otherwise make a new file.
    if filename == '':

        # Use Mirrormask timestamp format.
        now = time.localtime()
        timestamp = '{y}{m:02d}{d:02d}'.format(
            y=now.tm_year, m=now.tm_mon, d=now.tm_mday)

        # We want to store the search term in the filename if possible.
        # There might be a better way to do this--especially if we eventually
        # have to consider complex boolean search strings.
        term = slugify(article['search_term'])

        filename = config['OUTPUT_FILENAME'].format(
            index='{index}',
            timestamp=timestamp,
            site=article['pub_short'],
            term=slugify(term)
        )

        # Increment filenames.
        for x in range(sys.maxsize):
            temp_filename = filename.format(index=x)
            if not os.path.exists(os.path.join(path, temp_filename)):
                filename = temp_filename
                break
        
        log.info(_('Saving: %s'), filename)

    filename = os.path.join(path, filename)
    with open(filename, 'w', encoding='utf-8') as outfile:
        json.dump(article, outfile, ensure_ascii=False, indent=2)


def clean_string(dirty_string, regex_string=None):
    """
    """

    # Start by Bleaching out the HTML.
    dirty_string = bleach.clean(dirty_string, tags=[], strip=True)
    dirty_string = html.unescape(dirty_string)  # Get rid of &lt;, etc.

    # Ideally we shouldn't need this since all the content is being handled
    # "safely," but the LexisNexis import script does it, so we'll do it too
    # in case some other part of the process is expecting ASCII-only text.
    ascii_string = unidecode(dirty_string)

    # Regex processing. Experimental!
    # This looks for:
    # - URL strings, common in blog posts, etc., and probably not useful for
    #   topic modelling.
    # - Irregular punctuation, i.e. punctuation left over from formatting
    #   or HTML symbols that Bleach missed.
    if not regex_string:
        regex_string = r'http(.*?)\s|[^a-zA-Z0-9\s\.\,\!\"\'\-\:\;\p{Sc}]'
    ascii_string = re.sub(re.compile(regex_string), ' ', ascii_string)

    ascii_string = ''.join([x for x in ascii_string if x in string.printable])
    ascii_string = ' '.join(ascii_string.split())
    ascii_string = ascii_string.replace(' .', '.')  # ??

    return ascii_string


def slugify(title_string):
    """
    """

    title_string = clean_string(title_string, r'[^a-zA-Z0-9]')
    title_string = title_string.replace(' ', '-').lower()
    return title_string
