# Copyright 2013,2014 Music Technology Group - Universitat Pompeu Fabra
#
# This file is part of Dunya
#
# Dunya is free software: you can redistribute it and/or modify it under the
# terms of the GNU Affero General Public License as published by the Free Software
# Foundation (FSF), either version 3 of the License, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
# PARTICULAR PURPOSE.  See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with
# this program.  If not, see http://www.gnu.org/licenses/

from .log import log
import urllib.request, urllib.error, urllib.parse
import xml.etree.ElementTree as etree
import time

import musicbrainzngs as mb
mb.set_useragent("Dunya", "0.1")
mb.set_rate_limit(False)
mb.set_hostname("musicbrainz.s.upf.edu")

MUSICBRAINZ_COLLECTION_CARNATIC = ""
MUSICBRAINZ_COLLECTION_HINDUSTANI = ""
MUSICBRAINZ_COLLECTION_MAKAM = ""

headers={"User-Agent": "Dunya/0.1 python-musicbrainzngs"}

def ws_ids(xml):
    ids = []
    tree = etree.fromstring(xml)
    count = int(list(list(tree)[0])[2].attrib["count"])
    for rel in list(list(list(tree)[0])[2]):
        ids.append(rel.attrib["id"])
    return (count, ids)


def _get_items_in_collection(collectionid, collectiontype):
    items = []
    count = 25
    offset = 0
    while offset < count:
        try:
            log.debug("offset", offset)
            url = "https://beta.musicbrainz.org/ws/2/collection/%s/%s?offset=%d" % (collectionid, collectiontype, offset)
            req = urllib.request.Request(url, headers=headers)
            xml = urllib.request.urlopen(req).read()
            count, ids = ws_ids(xml)
            items.extend(ids)
        except urllib.error.HTTPError as e:
            if e.code != 503:
                # if we get ratelimited, sleep and try again.
                # any other error, re-raise
                raise
        else:
            offset += 25
        finally:
            time.sleep(1)
    return items

def get_releases_in_collection(collection):
    """Get a list of the releases in the specified musicbrainz collection"""
    return _get_items_in_collection(collection, "releases")

def get_works_in_collection(collection):
    """Get a list of the works in the specified musicbrainz collection"""
    return _get_items_in_collection(collection, "works")

def get_collection_name(collection):
    """ Get the name of a collection """
    url = "http://musicbrainz.org/ws/2/collection/%s/releases" % (collection, )
    req = urllib.request.Request(url, headers=headers)
    xml = urllib.request.urlopen(req).read()
    tree = etree.fromstring(xml)
    name = list(list(tree)[0])[0]
    return name.text

def get_recordings_from_release(release):
    rel = mb.get_release_by_id(release, includes=["recordings"])["release"]
    recordings = []
    for m in rel.get("medium-list", []):
        for t in m.get("track-list", []):
            recordings.append(t["recording"]["id"])
    return recordings

def get_tags_from_recording(recording):
    rec = mb.get_recording_by_id(recording, includes=["tags"])["recording"]
    return rec.get("tag-list", [])

def get_works_from_recording(recording):
    rec = mb.get_recording_by_id(recording, includes=["work-rels"])["recording"]
    return rec.get("work-relation-list", [])

def get_work_attributes(workid):
    work = mb.get_work_by_id(workid)["work"]
    return work.get("attribute-list", [])
