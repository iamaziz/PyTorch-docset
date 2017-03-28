#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Author: Aziz Alto

"""
Dependency:
- requests
- BeautifulSoup4
- httrack
"""

try:
    from urllib import urlretrieve as retrieve
except ImportError:
    from urllib.request import urlretrieve as retrieve
import sqlite3
import os
import plistlib
import string
import requests
from bs4 import BeautifulSoup


class Docset(object):
    def __init__(self, name, website, pages, icon_url):
        self.name = name
        self.website = website
        self.pages = pages
        self.docset_name = '{}.docset'.format(self.name)
        self.setup_docset()
        self.add_infoplist()
        self.cur, self.db = self.connect_db()
        self.scrape_urls()
        self.report()
        retrieve(icon_url, self.docset_name + "/icon.png")

    def setup_docset(self, download_html=False):

        output = self.docset_name + '/Contents/Resources/Documents/'
        if not os.path.exists(output):
            os.makedirs(output)
        cmd = """
            cd {0} &&
            httrack -%v2 -T60 -R99 --sockets=7 -%c1000 -c10 -A999999999 -%N0 --disable-security-limits -F 'Mozilla/5.0 (X11; Linux i686) AppleWebKit/535.19 (KHTML, like Gecko) Ubuntu/11.10 Chromium/18.0.1025.168' --mirror --keep-alive --robots=0 "{1}" -n -* +*.css +*css.php +*.ico +*/fonts/* +*.svg +*.ttf +fonts.googleapis.com* +*.woff +*.eot +*.png +*.jpg +*.gif +*.jpeg +*.js +{1}* -github.com* +raw.github.com* &&
            rm -rf hts-* &&
            mkdir -p Contents/Resources/Documents &&
            mv -f *.* Contents/Resources/Documents/
            """.format(self.docset_name, self.website)
        if download_html:
            os.system(cmd)

    def connect_db(self):
        db = sqlite3.connect(self.docset_name + '/Contents/Resources/docSet.dsidx')
        cursor = db.cursor()
        cursor.execute('DROP TABLE searchIndex;')
        cursor.execute('CREATE TABLE searchIndex(id INTEGER PRIMARY KEY, name TEXT, type TEXT, path TEXT);')
        cursor.execute('CREATE UNIQUE INDEX anchor ON searchIndex (name, type, path);')
        return cursor, db

    def scrape_urls(self):

        idx = (i + j for i in string.lowercase for j in string.lowercase)
        pages = self.pages
        for p in pages:
            # base path of current page
            base_path = pages[p].split("//")[1]
            # soup each page
            html = requests.get(pages[p]).text
            soup = BeautifulSoup(html, 'html.parser')
            # find href and populate entries to db
            for a in soup.findAll('a', class_='reference internal'):
                entry_name = a.text.strip()
                path = a.get('href')
                if p == 'Guide':
                    entry_name = '{}: {}'.format(idx.next(), entry_name.encode('ascii', 'ignore'))
                path = base_path + path
                self.update_db(entry_name, p, path)

    def update_db(self, entry_name, typ, path):

        self.cur.execute("SELECT rowid FROM searchIndex WHERE path = ?", (path,))
        dbpath = self.cur.fetchone()
        self.cur.execute("SELECT rowid FROM searchIndex WHERE name = ?", (entry_name,))
        dbname = self.cur.fetchone()
        if dbpath is None and dbname is None:
            self.cur.execute('INSERT OR IGNORE INTO searchIndex(name, type, path) VALUES (?,?,?)',
                             (entry_name, typ, path))
            print('DB add >> name: {0} | type: {1} | path: {2}'.format(entry_name, typ, path))
        else:
            print("record exists")

    def add_infoplist(self):

        index_file = self.website.split("//")[1]
        plist_path = os.path.join(self.docset_name, "Contents", "Info.plist")
        plist_cfg = {
            'CFBundleIdentifier': self.name,
            'CFBundleName': self.name,
            'DocSetPlatformFamily': self.name.lower(),
            'DashDocSetFamily': 'python',
            'isDashDocset': True,
            'isJavaScriptEnabled': True,
            'dashIndexFilePath': index_file
        }
        plistlib.writePlist(plist_cfg, plist_path)

    def report(self):

        self.cur.execute('SELECT count(*) FROM searchIndex;')
        entry = self.cur.fetchone()
        print("{} entry.".format(entry))
        # commit and close db
        self.db.commit()
        self.db.close()


if __name__ == '__main__':

    name = 'PyTorch'
    index_page = 'http://pytorch.org/docs/'
    entry_pages = {
        'func': 'http://pytorch.org/docs/',
        'Guide': 'http://pytorch.org/tutorials/'
    }
    icon = 'https://avatars2.githubusercontent.com/u/21003710?v=3&s=200'

    Docset(name, index_page, entry_pages, icon_url=icon)
