import re
import os
import logging

from mutagen.flac import FLAC, Picture
import mutagen.id3 as id3
from mutagen.id3 import ID3NoHeaderError

logger = logging.getLogger(__name__)


# unicode symbols
COPYRIGHT, PHON_COPYRIGHT = "\u2117", "\u00a9"
# if a metadata block exceeds this, mutagen will raise error
# and the file won't be tagged
FLAC_MAX_BLOCKSIZE = 16777215

ID3_LEGEND = {
    "album": id3.TALB,
    "albumartist": id3.TPE2,
    "artist": id3.TPE1,
    "date": id3.TDAT,
    "genre": id3.TCON,
    "performer": id3.TOPE,
    "title": id3.TIT2,
    "year": id3.TYER,
}


def _get_title(track_dict):
    title = track_dict["title"]
    version = track_dict.get("version")
    if version:
        title = f"{title} ({version})"
    # for classical works
    if track_dict.get("work"):
        title = f"{track_dict['work']}: {title}"

    return title

# Use KeyError catching instead of dict.get to avoid empty tags
def tag_flac(
    filename, root_dir, final_name, d: dict, album, istrack=True, em_image=False
):
    """
    Tag a FLAC file

    :param str filename: FLAC file path
    :param str root_dir: Root dir used to get the cover art
    :param str final_name: Final name of the FLAC file (complete path)
    :param dict d: Track dictionary from Qobuz_client
    :param dict album: Album dictionary from Qobuz_client
    :param bool istrack
    :param bool em_image: Embed cover art into file
    """
    audio = FLAC(filename)

    audio["TITLE"] = _get_title(d)

    audio["TRACKNUMBER"] = str(d["track_number"])  # TRACK NUMBER

    if "Disc " in final_name:
        audio["DISCNUMBER"] = str(d["media_number"])

    artist_ = d.get("performer", {}).get("name")  # TRACK ARTIST
    if istrack:
        audio["ARTIST"] = artist_ or d["album"]["artist"]["name"]  # TRACK ARTIST
    else:
        audio["ARTIST"] = artist_ or album["artist"]["name"]

    if istrack:
        audio["GENRE"] = d["album"]["genre"]["name"]
        audio["ALBUMARTIST"] = d["album"]["artist"]["name"]
        audio["TRACKTOTAL"] = str(d["album"]["tracks_count"])
        audio["ALBUM"] = d["album"]["title"]
        audio["DATE"] = d["album"]["release_date_original"]
    else:
        audio["GENRE"] = album["genre"]["name"]
        audio["ALBUMARTIST"] = album["artist"]["name"]
        audio["TRACKTOTAL"] = str(album["tracks_count"])
        audio["ALBUM"] = album["title"]
        audio["DATE"] = album["release_date_original"]

    audio.save()
    os.rename(filename, final_name)


def tag_mp3(filename, root_dir, final_name, d, album, istrack=True, em_image=False):
    """
    Tag an mp3 file

    :param str filename: mp3 temporary file path
    :param str root_dir: Root dir used to get the cover art
    :param str final_name: Final name of the mp3 file (complete path)
    :param dict d: Track dictionary from Qobuz_client
    :param bool istrack
    :param bool em_image: Embed cover art into file
    """

    try:
        audio = id3.ID3(filename)
    except ID3NoHeaderError:
        audio = id3.ID3()

    # temporarily holds metadata
    tags = dict()
    tags["title"] = _get_title(d)
    artist_ = d.get("performer", {}).get("name")  # TRACK ARTIST
    if istrack:
        tags["artist"] = artist_ or d["album"]["artist"]["name"]  # TRACK ARTIST
    else:
        tags["artist"] = artist_ or album["artist"]["name"]

    if istrack:
        tags["genre"] = d["album"]["genre"]["name"]
        tags["albumartist"] = d["album"]["artist"]["name"]
        tags["album"] = d["album"]["title"]
        tags["date"] = d["album"]["release_date_original"]
        tracktotal = str(d["album"]["tracks_count"])
    else:
        tags["genre"] = album["genre"]["name"]
        tags["albumartist"] = album["artist"]["name"]
        tags["album"] = album["title"]
        tags["date"] = album["release_date_original"]
        tracktotal = str(album["tracks_count"])

    tags["year"] = tags["date"][:4]

    audio["TRCK"] = id3.TRCK(encoding=3, text=f'{d["track_number"]}/{tracktotal}')
    audio["TPOS"] = id3.TPOS(encoding=3, text=str(d["media_number"]))

    # write metadata in `tags` to file
    for k, v in tags.items():
        id3tag = ID3_LEGEND[k]
        audio[id3tag.__name__] = id3tag(encoding=3, text=v)

    audio.save(filename, "v2_version=3")
    os.rename(filename, final_name)
