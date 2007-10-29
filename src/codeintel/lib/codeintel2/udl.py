#!python
# ***** BEGIN LICENSE BLOCK *****
# Version: MPL 1.1/GPL 2.0/LGPL 2.1
# 
# The contents of this file are subject to the Mozilla Public License
# Version 1.1 (the "License"); you may not use this file except in
# compliance with the License. You may obtain a copy of the License at
# http://www.mozilla.org/MPL/
# 
# Software distributed under the License is distributed on an "AS IS"
# basis, WITHOUT WARRANTY OF ANY KIND, either express or implied. See the
# License for the specific language governing rights and limitations
# under the License.
# 
# The Original Code is Komodo code.
# 
# The Initial Developer of the Original Code is ActiveState Software Inc.
# Portions created by ActiveState Software Inc are Copyright (C) 2000-2007
# ActiveState Software Inc. All Rights Reserved.
# 
# Contributor(s):
#   ActiveState Software Inc
# 
# Alternatively, the contents of this file may be used under the terms of
# either the GNU General Public License Version 2 or later (the "GPL"), or
# the GNU Lesser General Public License Version 2.1 or later (the "LGPL"),
# in which case the provisions of the GPL or the LGPL are applicable instead
# of those above. If you wish to allow use of your version of this file only
# under the terms of either the GPL or the LGPL, and not to allow others to
# use your version of this file under the terms of the MPL, indicate your
# decision by deleting the provisions above and replace them with the notice
# and other provisions required by the GPL or the LGPL. If you do not delete
# the provisions above, a recipient may use your version of this file under
# the terms of any one of the MPL, the GPL or the LGPL.
# 
# ***** END LICENSE BLOCK *****

"""UDL (User-Defined Language) support for codeintel."""

import os
from os.path import dirname, join, abspath, normpath, basename
import sys
import re
import logging
import traceback

import SilverCity
from SilverCity import ScintillaConstants
from SilverCity.ScintillaConstants import * #XXX import only what we need
from SilverCity.Lexer import Lexer

from codeintel2.common import *
from codeintel2.citadel import CitadelBuffer
#from codeintel2.javascript_common import trg_from_pos as javascript_trg_from_pos

try:
    from xpcom import components
    from xpcom.server import UnwrapObject
    import directoryServiceUtils
    _xpcom_ = True
except ImportError:
    _xpcom_ = False

log = logging.getLogger("codeintel.udl")
#log.setLevel(logging.DEBUG)

#XXX We need to have a better mechanism for rationalizing and sharing
#    common lexer style classes. For now we'll just HACKily grab from
#    Komodo's styles.py. Some of this is duplicating logic in
#    KoLanguageServiceBase.py.
_ko_src_dir = normpath(join(dirname(__file__), *([os.pardir]*3)))
sys.path.insert(0, join(_ko_src_dir, "schemes"))
try:
    import styles
finally:
    del sys.path[0]
    del _ko_src_dir




#---- module interface

# Test 'udl/general/is_udl_x_style' tests these.
def is_udl_m_style(style):
    return (ScintillaConstants.SCE_UDL_M_DEFAULT <= style
            <= ScintillaConstants.SCE_UDL_M_COMMENT)
def is_udl_css_style(style):
    return (ScintillaConstants.SCE_UDL_CSS_DEFAULT <= style
            <= ScintillaConstants.SCE_UDL_CSS_OPERATOR)
def is_udl_csl_style(style):
    return (ScintillaConstants.SCE_UDL_CSL_DEFAULT <= style
            <= ScintillaConstants.SCE_UDL_CSL_REGEX)
def is_udl_ssl_style(style):
    return (ScintillaConstants.SCE_UDL_SSL_DEFAULT <= style
            <= ScintillaConstants.SCE_UDL_SSL_VARIABLE)
def is_udl_tpl_style(style):
    return (ScintillaConstants.SCE_UDL_TPL_DEFAULT <= style
            <= ScintillaConstants.SCE_UDL_TPL_VARIABLE)

#XXX Redundant code from koUDLLanguageBase.py::KoUDLLanguage
# Necessary because SilverCity.WordList splits input on white-space

_re_bad_filename_char = re.compile(r'([% 	\x80-\xff])')
def _lexudl_path_escape(m):
    return '%%%02X' % ord(m.group(1))
def _urlescape(s):
    return _re_bad_filename_char.sub(_lexudl_path_escape, s)

class UDLLexer(Lexer):
    """LexUDL wants the path to the .lexres file as the first element of
    the first keywords list.
    """

    def __init__(self):
        self._properties = SilverCity.PropertySet()
        self._lexer = SilverCity.find_lexer_module_by_id(ScintillaConstants.SCLEX_UDL)
        lexres_path = _urlescape(self._get_lexres_path())
        log.debug("escaped lexres_path: %r", lexres_path)
        self._keyword_lists = [
            SilverCity.WordList(lexres_path),
        ]

    if _xpcom_:
        # Presume we are running under Komodo. Look in the available
        # lexres dirs from extensions.

        def _gen_lexer_dirs(self):
            """Return all possible lexer resource directories (i.e. those ones
            that can include compiled UDL .lexres files).
    
            It yields directories that should "win" first.
    
            This doesn't filter out non-existant directories.
            """
            koDirs = components.classes["@activestate.com/koDirs;1"] \
                .getService(components.interfaces.koIDirs)
    
            yield join(koDirs.userDataDir, "lexers")    # user
            for extensionDir in directoryServiceUtils.getExtensionDirectories():
                yield join(extensionDir, "lexers")      # user-install extensions
            yield join(koDirs.commonDataDir, "lexers")  # site/common
            yield join(koDirs.supportDir, "lexers")     # factory

        def _get_lexres_path(self):
            for lexer_dir in self._gen_lexer_dirs():
                if not exists(lexer_dir):
                    continue
                candidate = join(lexer_dir, self.lang+".lexres")
                if exists(candidate):
                    return candidate
            else:
                raise CodeIntelError("could not find lexres file for %s: "
                                     "`%s.lexres' does not exist in any "
                                     "of the lexer dirs"
                                     % (self.lang, self.lang))
    else:
        def _get_lexres_path(self):
            candidate = join(dirname(__file__), "lexers", self.lang+".lexres")
            if not exists(candidate):
                raise CodeIntelError("could not find lexres file for %s: "
                                     "`%s' does not exist"
                                     % (self.lang, candidate))
            return candidate



class UDLBuffer(CitadelBuffer):
    """A CodeIntel Buffer for a UDL-lexer-based language."""
    sce_prefixes = ["SCE_UDL_"]
    #XXX Not sure that this indirection will be useful, but we'll see.

    # Sub-classes must set the following of these that are appropriate:
    m_lang = None
    css_lang = None
    csl_lang = None
    ssl_lang = None
    tpl_lang = None

    def lang_from_style(self, style):
        if (ScintillaConstants.SCE_UDL_M_DEFAULT <= style
              <= ScintillaConstants.SCE_UDL_M_COMMENT):
            return self.m_lang
        elif (ScintillaConstants.SCE_UDL_CSS_DEFAULT <= style
              <= ScintillaConstants.SCE_UDL_CSS_OPERATOR):
            return self.css_lang
        elif (ScintillaConstants.SCE_UDL_CSL_DEFAULT <= style
              <= ScintillaConstants.SCE_UDL_CSL_REGEX):
            return self.csl_lang
        elif (ScintillaConstants.SCE_UDL_SSL_DEFAULT <= style
              <= ScintillaConstants.SCE_UDL_SSL_VARIABLE):
            return self.ssl_lang
        elif (ScintillaConstants.SCE_UDL_TPL_DEFAULT <= style
              <= ScintillaConstants.SCE_UDL_TPL_VARIABLE):
            return self.tpl_lang
        else:
            raise ValueError("unknown UDL style: %r" % style)

    def lang_from_pos(self, pos):
        style = self.accessor.style_at_pos(pos)
        return self.lang_from_style(style)

    def scoperef_from_pos(self, pos):
        """Return the scoperef for the given position in this buffer.

        A "scoperef" is a 2-tuple:
            (<blob>, <lpath>)
        where <blob> is the ciElementTree blob for the buffer content
        and <lpath> is an ordered list of names into the blob
        identifying the scope.
        
        If no relevant scope is found (e.g. for example, in markup
        content in PHP) then None is returned.

        See Buffer.scoperef_from_pos() docstring for more details.
        """
        lang = self.lang_from_pos(pos)
        try:
            blob = self.blob_from_lang[lang]
        except KeyError:
            return None
        line = self.accessor.line_from_pos(pos) + 1 # convert to 1-based
        return self.scoperef_from_blob_and_line(blob, line)

    def trg_from_pos(self, pos, implicit=True):
        if pos == 0:
            return None
        lang = self.lang_from_pos(pos-1)
        if lang is None:
            style = self.accessor.style_at_pos(pos)
            style_names = self.style_names_from_style_num(style)
            raise CodeIntelError("got unexpected style in `%s': %s %s"
                                 % (basename(self.path), style, style_names))
        try:
            langintel = self.mgr.langintel_from_lang(lang)
        except KeyError:
            return None
        return langintel.trg_from_pos(self, pos, implicit=implicit)

    def preceding_trg_from_pos(self, pos, curr_pos):
        if curr_pos == 0:
            return None
        lang = self.lang_from_pos(curr_pos-1)
        try:
            langintel = self.mgr.langintel_from_lang(lang)
        except KeyError:
            return None
        return langintel.preceding_trg_from_pos(self, pos, curr_pos)

    def curr_calltip_arg_range(self, trg_pos, calltip, curr_pos):
        if curr_pos == 0:
            return None
        lang = self.lang_from_pos(curr_pos-1)
        try:
            langintel = self.mgr.langintel_from_lang(lang)
        except KeyError:
            return (-1, -1)
        try:
            return langintel.curr_calltip_arg_range(self, trg_pos, calltip,
                                                    curr_pos)
        except AttributeError:
            # This can happen if we accidentally move into a non-programming
            # language during a calltip. E.g. bug 69529. Cancel the calltip
            # in this case.
            return (-1, -1)

    def async_eval_at_trg(self, trg, ctlr):
        try:
            langintel = self.mgr.langintel_from_lang(trg.lang)
        except KeyError:
            return None
        return langintel.async_eval_at_trg(self, trg, ctlr)

    # Override Citadel.defn_trg_from_pos()
    def defn_trg_from_pos(self, pos, lang=None):
        # Work out the language from the position, as the citadel buffer will
        # use the buffer language, we want a language specific to this pos.
        return CitadelBuffer.defn_trg_from_pos(self, pos,
                                               lang=self.lang_from_pos(pos))

    def libs(self):
        """A simple `.libs' property does not work for multi-lang buffers.
        Use `.libs_from_lang(lang)' instead.
        """
        raise RuntimeError("`.libs' invalid for multi-lang buffers: use "
                           "`mgr.langintel_from_lang(lang).libs_from_buf(buf)' "
                           "directly")

    def style_names_from_style_num(self, style_num):
        #XXX Would like to have python-foo instead of p_foo or SCE_P_FOO, but
        #    that requires a more comprehensive solution for all langs and
        #    multi-langs.
        style_names = []

        # Get the constant name from ScintillaConstants.
        if "UDL" not in self._style_name_from_style_num_from_lang:
            name_from_num \
                = self._style_name_from_style_num_from_lang["UDL"] = {}
            if self.sce_prefixes is None:
                raise Error("'sce_prefixes' not set on class %s: cannot "
                            "determine style constant names"
                            % self.__class__.__name__)
            for attr in dir(ScintillaConstants):
                for sce_prefix in self.sce_prefixes:
                    if attr.startswith(sce_prefix):
                        name_from_num[getattr(ScintillaConstants, attr)] = attr
        else:
            name_from_num \
                = self._style_name_from_style_num_from_lang["UDL"]
        const_name = self._style_name_from_style_num_from_lang["UDL"][style_num]
        style_names.append(const_name)
        
        # Get a style group from styles.py.
        if "UDL" in styles.StateMap:
            for style_group, const_names in styles.StateMap["UDL"].items():
                if const_name in const_names:
                    style_names.append(style_group)
                    break
        else:
            log.warn("lang '%s' not in styles.StateMap: won't have "
                     "common style groups in HTML output" % "UDL")
        
        return style_names

    __string_styles = None
    def string_styles(self):
        if self.__string_styles is None:
            state_map = styles.StateMap["UDL"]
            self.__string_styles = [
                getattr(ScintillaConstants, style_name)
                for style_class in ("strings", "stringeol")
                for style_name in state_map.get(style_class, [])
            ]
        return self.__string_styles

    __comment_styles = None
    def comment_styles(self):
        if self.__comment_styles is None:
            state_map = styles.StateMap["UDL"]
            self.__comment_styles = [
                getattr(ScintillaConstants, style_name)
                for style_class in ("comments", "here documents",
                                    "data sections")
                for style_name in state_map.get(style_class, [])
            ]
        return self.__comment_styles

    __number_styles = None
    def number_styles(self):
        if self.__number_styles is None:
            state_map = styles.StateMap["UDL"]
            self.__number_styles = [
                getattr(ScintillaConstants, style_name)
                for style_class in ("numbers",)
                for style_name in state_map.get(style_class, [])
            ]
        return self.__number_styles


class XMLParsingBufferMixin(object):
    """A mixin for UDLBuffer-based buffers of XML-y/HTML-y languages to
    support the following:

    - An "xml_tree" attribute that is a XML parse tree of the document
      (lazily done from koXMLTreeService)
    - An "xml_parse()" method to force a re-parse of the document.

    TODO: locking?
    """
    _xml_tree_cache = None
    @property
    def xml_tree(self):
        if self._xml_tree_cache is None:
            self.xml_parse()
        return self._xml_tree_cache

    def xml_parse(self):
        from koXMLTreeService import getService
        self._xml_tree_cache = getService().getTreeForURI(
                self.path, self.accessor.text)


class _NotYetSet(object):
    # Used below to distinguish from None.
    pass

class UDLCILEDriver(CILEDriver):
    ssl_lang = None   # Sub-classes must set one or both of these for
    csl_lang = None   #    citadel-scanning support.

    _master_cile_driver = None
    slave_csl_cile_driver = _NotYetSet # to distinguish from None

    @property
    def master_cile_driver(self):
        """The primary CILE driver for this multi-lang lang.

        This is the CILE driver for the SSL lang, if there is one, otherwise
        for the csl_lang.

        Side effect: `self.slave_csl_cile_driver' is determined the
        first time this is called. A little gross, I know, but it
        avoids having a separate property.
        """
        if self._master_cile_driver is None:
            if self.ssl_lang is not None:
                self._master_cile_driver \
                    = self.mgr.citadel.cile_driver_from_lang(self.ssl_lang)
                self.slave_csl_cile_driver \
                    = self.mgr.citadel.cile_driver_from_lang(self.csl_lang)
            else:
                self._master_cile_driver \
                    = self.mgr.citadel.cile_driver_from_lang(self.csl_lang)
                self.slave_csl_cile_driver = None
        return self._master_cile_driver

    def scan_purelang(self, buf):
        return self.master_cile_driver.scan_multilang(
                        buf, self.slave_csl_cile_driver)



