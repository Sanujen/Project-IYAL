#!/usr/bin/env python
# -*- coding: utf-8 -*-

##############################################################################
#                                                                            #
# Author : Arulalan.T <arulalant@gmail.com>                                  #
# Date : 04.08.2014                                                          #
#                                                                            #
# This file is part of txt2uni                                               #
#                                                                            #
# txt2uni is free software: you can redistribute it and/or                   #
# modify it under the terms of the GNU General Public License as published by#
# the Free Software Foundation, either version 3 of the License, or (at your #
# option) any later version. This program is distributed in the hope that it #
# will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty#
# of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General#
# Public License for more details. You should have received a copy of the GNU#
# General Public License along with this program. If not, see                #
# <http://www.gnu.org/licenses/>.                                            #
#                                                                            #
##############################################################################

from collections import OrderedDict
from iyal_quality_analyzer.utils.legacy_converter.encode2utf8 import (
    anjal2utf8,
    bamini2utf8,
    boomi2utf8,
    dinakaran2utf8,
    dinamani2utf8,
    dinathanthy2utf8,
    kavipriya2utf8,
    murasoli2utf8,
    mylai2utf8,
    nakkeeran2utf8,
    roman2utf8,
    tab2utf8,
    tam2utf8,
    tscii2utf8,
    pallavar2utf8,
    indoweb2utf8,
    koeln2utf8,
    libi2utf8,
    oldvikatan2utf8,
    webulagam2utf8,
    diacritic2utf8,
    shreelipi2utf8,
    softview2utf8,
    tace2utf8,
    vanavil2utf8,
)

__all__ = [
    "anjal2unicode",
    "bamini2unicode",
    "boomi2unicode",
    "dinakaran2unicode",
    "dinathanthy2unicode",
    "kavipriya2unicode",
    "murasoli2unicode",
    "mylai2unicode",
    "nakkeeran2unicode",
    "roman2unicode",
    "tab2unicode",
    "tam2unicode",
    "tscii2unicode",
    "indoweb2unicode",
    "koeln2unicode",
    "libi2unicode",
    "oldvikatan2unicode",
    "webulagam2unicode",
    "auto2unicode",
    "dinamani2unicode",
    "pallavar2unicode",
    "diacritic2unicode",
    "shreelipi2unicode",
    "softview2unicode",
    "tace2unicode",
    "vanavil2unicode",
]

_all_encodes_ = OrderedDict(
    [
        ("anjal2utf8", anjal2utf8),
        ("bamini2utf8", bamini2utf8),
        ("boomi2utf8", boomi2utf8),
        ("dinakaran2utf8", dinakaran2utf8),
        ("dinamani2utf8", dinamani2utf8),
        ("dinathanthy2utf8", dinathanthy2utf8),
        ("kavipriya2utf8", kavipriya2utf8),
        ("murasoli2utf8", murasoli2utf8),
        ("mylai2utf8", mylai2utf8),
        ("nakkeeran2utf8", nakkeeran2utf8),
        ("roman2utf8", roman2utf8),
        ("tab2utf8", tab2utf8),
        ("tam2utf8", tam2utf8),
        ("tscii2utf8", tscii2utf8),
        ("pallavar2utf8", pallavar2utf8),
        ("indoweb2utf8", indoweb2utf8),
        ("koeln2utf8", koeln2utf8),
        ("libi2utf8", libi2utf8),
        ("oldvikatan2utf8", oldvikatan2utf8),
        ("webulagam2utf8", webulagam2utf8),
        ("diacritic2utf8", diacritic2utf8),
        ("shreelipi2utf8", shreelipi2utf8),
        ("softview2utf8", softview2utf8),
        ("tace2utf8", tace2utf8),
        ("vanavil2utf8", vanavil2utf8),
    ]
)


# By enable this flage, it will write individual encodes unique & common
# characters in text file.
__WRITE_CHARS_TXT = False


def encode2unicode(text, charmap):
    """
    charmap : dictionary which has both encode as key, unicode as value
    """
    if isinstance(text, (list, tuple)):
        unitxt = ""
        for line in text:
            for key, val in charmap.items():
                if key in line:
                    line = line.replace(key, val)
            unitxt += line

        return unitxt
    elif isinstance(text, str):
        for key, val in charmap.items():
            if key in text:
                text = text.replace(key, val)
        return text


def _get_unique_ch(text, all_common_encodes):
    """
    text : encode sample strings

    returns unique word / characters from input text encode strings.
    """

    unique_chars = ""
    if isinstance(text, str):
        text = text.split("\n")
    elif isinstance(text, (list, tuple)):
        pass

    special_chars = [".", ",", ";", ":", "", " ", "\r", "\t", "=", "\n"]
    for line in text:
        for word in line.split(" "):
            for ch in all_common_encodes:
                if ch in word:
                    word = word.replace(ch, "")
            # end of for ch in _all_common_encodes_:

            # if len of word is zero, then go for another word
            if not word:
                continue

            for ch in word:
                if ch.isdigit() or ch in special_chars:
                    # remove special common chars
                    word = word.replace(ch, "")
                    continue
                # end of if ch.isdigit() or ...:
                # Whola, got unique chars from user passed text
                return word
            # end of for ch in word:
        # end of for word in line.split(' '):
    # end of for line in text:
    return ""


# end of def get_unique_ch(text):


def _get_unique_common_encodes():
    """
    This function will return both unique_encodes and common_encodes as tuple.

    unique_encodes : In dictionary with encodes name as key and its
       corresponding encode's unique characters among other available encodes.
    common_encodes : In set type which has all common encode compound
       characters from all available encodes.
       i.e. removed common encode single characters

    Author : Arulalan.T

    04.08.2014

    """

    _all_unique_encodes_ = []
    _all_unicode_encodes_ = {}
    _all_common_encodes_ = set([])
    _all_common_encodes_single_char_ = set([])

    for name, encode in _all_encodes_.items():
        encode_utf8 = set([ch for ch in encode.keys()])
        _all_unicode_encodes_[name] = encode_utf8
    # end of for name, encode in _all_encodes_.items():

    _all_unique_encodes_full_ = _all_unicode_encodes_.copy()

    for supname, super_encode in _all_unicode_encodes_.items():
        for subname, sub_encode in _all_unicode_encodes_.items():
            if supname == subname:
                continue
            # get unique of super_encode among other encodings
            super_encode = super_encode - sub_encode
        # end of for sub_encode in _all_unicode_encodes_.items():
        # get common for all over encodings
        common = _all_unique_encodes_full_[supname] - super_encode
        # merge common to all encodings common
        _all_common_encodes_ = _all_common_encodes_.union(common)
        # store super_encode's unique keys with its name
        _all_unique_encodes_.append((supname, super_encode))
    # end of for supname, super_encode in _all_unicode_encodes_.items():

    for ch in _all_common_encodes_:
        # collect single common chars
        if len(ch) == 1:
            _all_common_encodes_single_char_.add(ch)
    # end of for ch in _all_common_encodes_:

    # remove single common char from compound common chars
    _all_common_encodes_ -= _all_common_encodes_single_char_

    if __WRITE_CHARS_TXT:
        # write common compound characters of all encodes
        f = open("all.encodes.common.chars.txt", "w")
        for ch in _all_common_encodes_:
            ch = ch.encode("utf-8")
            for encode_keys in _all_encodes_.values():
                if ch in encode_keys:
                    uni = encode_keys[ch]
                    break
                # end of if ch in encode_keys:
            # end of for encode_keys in _all_encodes_.values():
            f.write(ch + "  =>  " + uni + "\n")
        # end of for ch in _all_common_encodes_:
        f.close()
        # write unique compound characters of all encodes
        for encode_name, encode_keys in _all_unique_encodes_:
            f = open(encode_name + ".unique.chars.txt", "w")
            for ch in encode_keys:
                ch = ch.encode("utf-8")
                uni = _all_encodes_[encode_name][ch]
                f.write(ch + "  =>  " + uni + "\n")
            # end of for ch in encode_keys:
            f.close()
        # end of for encode_name, encode_keys in _all_unique_encodes_:
    # end of if __WRITE_CHARS_TXT:

    return (_all_unique_encodes_, _all_common_encodes_)


# end of def _get_unique_common_encodes():


def auto2unicode(text):
    """
    This function tries to identify encode in available encodings.
    If it finds, then it will convert text into unicode string.

    Author : Arulalan.T

    04.08.2014

    """

    _all_unique_encodes_, _all_common_encodes_ = _get_unique_common_encodes()
    # get unique word which falls under any one of available encodes from
    # user passed text lines
    unique_chars = _get_unique_ch(text, _all_common_encodes_)
    # count common encode chars
    clen = len(_all_common_encodes_)
    msg = "Sorry, couldn't find encode :-(\n"
    msg += "Need more words to find unique encode out side of %d " % clen
    msg += "common compound characters"
    if not unique_chars:
        print(msg)
        return ""
    # end of if not unique_chars:

    for encode_name, encode_keys in _all_unique_encodes_:
        if not len(encode_keys):
            continue
        for ch in encode_keys:
            # check either encode char is presnent in word
            if ch in unique_chars:
                # found encode
                print("Whola! found encode : ", encode_name)
                encode = _all_encodes_[encode_name]
                return encode2unicode(text, encode)
            # end of if ch in unique_chars:
        # end of ifor ch in encode_keys:
    else:
        print(msg)
        return ""
    # end of for encode in _all_unique_encodes_:


# end of def auto2unicode(text):


def convert_legacy_to_unicode(legacy_text: str, encoding: str = None):
    """
    Converts legacy Tamil font-encoded text into Unicode.

    Args:
        legacy_text (str): The legacy font-encoded text.

    Returns:
        str: Converted Unicode text.
    """
    if encoding in _all_encodes_:
        print("encoding: ", encoding)
        encode = _all_encodes_[encoding]
        return encode2unicode(legacy_text, encode)
    else:
        print("No encoding specified. Trying to find automatically.")
        return auto2unicode(legacy_text)

def auto_detect_encoding(legacy_text: str):
    """
    Returns the encoding of the given legacy font-encoded text.

    Args:
        legacy_text (str): The legacy font-encoded text.

    Returns:
        str: The encoding of the given text.
    """
    _all_unique_encodes_, _all_common_encodes_ = _get_unique_common_encodes()
    unique_chars = _get_unique_ch(legacy_text, _all_common_encodes_)
    if not unique_chars:
        return "Unknown"
    for encode_name, encode_keys in _all_unique_encodes_:
        if not len(encode_keys):
            continue
        for ch in encode_keys:
            if ch in unique_chars:
                return encode_name
    return "Unknown"