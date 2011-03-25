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

from xpcom import components, ServerException

import sciutils

from koLanguageServiceBase import *
sci_constants = components.interfaces.ISciMoz

def registerLanguage(registery):
    registery.registerLanguage(koCSSLanguage())
    
class koCSSLanguage(KoLanguageBase):
    name = "CSS"
    _reg_desc_ = "%s Language" % name
    _reg_contractid_ = "@activestate.com/koLanguage?language=%s;1" \
                       % (name)
    _reg_clsid_ = "52594294-AF26-414A-9D66-C2B47EF9F015"

    supportsSmartIndent = "brace"
    primary = 1
    defaultExtension = ".css"
    commentDelimiterInfo = {
        "block": [ ("/*", "*/") ],
        "markup": "*",
    }

    searchURL = "http://www.google.com/search?q=site%3Ahttp%3A%2F%2Fwww.w3schools.com%2Fcss+%W"

    sample = """
h1 { color: white; background-color: orange !important; }
h2 { color: rgb(255, 255, 255); background-color: #00FF00; }

body {
    text-decoration: none;
    color: navy;
    font-family: "arial";
    font-size: 12pt;
    font-weight: medium;
}

.bold { text-decoration: bold; }
"""

    def __init__(self):
        KoLanguageBase.__init__(self)
        self._style_info.update(
            _indent_styles = [sci_constants.SCE_CSS_OPERATOR],
            _indent_open_styles = [sci_constants.SCE_CSS_OPERATOR],
            _indent_close_styles = [sci_constants.SCE_CSS_OPERATOR],
            _lineup_styles = [sci_constants.SCE_CSS_OPERATOR, sci_constants.SCE_CSS_TAG],
            _lineup_close_styles = [sci_constants.SCE_CSS_OPERATOR],
            _block_comment_styles = [sci_constants.SCE_CSS_COMMENT]
            )

    def get_lexer(self):
        if self._lexer is None:
            self._lexer = KoLexerLanguageService()
            self._lexer.setLexer(components.interfaces.ISciMoz.SCLEX_CSS)
            from lang_css import raw_word_lists
            for i in range(len(raw_word_lists)):
                self._lexer.setKeywords(i, raw_word_lists[i].split())
            self._lexer.supportsFolding = 1
        return self._lexer

    def test_scimoz(self, scimoz):
        # Test the auto-indenter
        CSSAutoIndentTestCase.cssObj = self
        testCases = [CSSAutoIndentTestCase]
        sciutils.runSciMozTests(testCases, scimoz)
        
class CSSAutoIndentTestCase(sciutils.SciMozTestCase):
    """Test suite for koCSSLanguage."""

    cssObj = None

    def test_WeLive(self):
        self.assertEqual(1, 1)

    def _do_test_buffer_indent(self, buffer, exp_ind):
        self._setupSciMoz(buffer, "CSS")
        new_ind = self.cssObj.computeIndent(self.scimoz, 'smart', True, self._style_info)
        if not new_ind and exp_ind == '': new_ind = ''
        self.assertEqual(exp_ind, new_ind)

    # Test boundary-conditions on comments at end of buffer

    def test_ai_1(self):
        self._do_test_buffer_indent("/*\n *\n *", " *")
        self._do_test_buffer_indent("/*\n *\n **", " **")

    def test_ai_2(self):
        self._do_test_buffer_indent("/*\n *\n */", "")

    def test_ai_3(self):
        # Put a space after the /, so we aren't at the end anymore
        self._do_test_buffer_indent("/*\n *\n */ ", "")

    def test_ai_4(self):
        # Put a newline after the indent
        self._do_test_buffer_indent("/*\n *\n */\n", "")

    def test_ai_5(self):
        # Verify open-brace indents
        self._do_test_buffer_indent("{", ' ' * self.scimoz.indent)
