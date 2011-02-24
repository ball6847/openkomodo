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


from xpcom import components, ServerException
from xpcom._xpcom import PROXY_SYNC, PROXY_ALWAYS, PROXY_ASYNC
from koLintResult import KoLintResult
from koLintResults import koLintResults
from xpcom.server.enumerator import *
import os, sys, re
import cStringIO
import eollib
import html5lib
from html5lib.constants import E as html5libErrorDict
import process

import logging
log = logging.getLogger("KoHTMLLinter")
#log.setLevel(logging.DEBUG)

#---- component implementation

class KoHTMLCompileLinter:
    _com_interfaces_ = [components.interfaces.koILinter]
    _reg_desc_ = "Komodo HTML Tidy Linter"
    _reg_clsid_ = "{DBF1E5E0-91C7-43da-870B-DB1859017102}"
    _reg_contractid_ = "@activestate.com/koLinter?language=HTML;1"
    _reg_categories_ = [
         ("category-komodo-linter", 'HTML'),
         ]

    def __init__(self):
        self.koDirs = components.classes["@activestate.com/koDirs;1"].\
                      getService(components.interfaces.koIDirs)
        self.infoSvc = components.classes["@activestate.com/koInfoService;1"].\
                       getService()
        
        self._proxyMgr = components.classes["@mozilla.org/xpcomproxy;1"].\
            getService(components.interfaces.nsIProxyObjectManager)
        self._prefSvc = components.classes["@activestate.com/koPrefService;1"].\
            getService(components.interfaces.koIPrefService)
        self._prefProxy = self._proxyMgr.getProxyForObject(None,
            components.interfaces.koIPrefService, self._prefSvc,
            PROXY_ALWAYS | PROXY_SYNC)

    def filterLines(self, lines):
        return lines

    def lint(self, request, argv_additions=None):
        text = request.content.encode(request.encoding.python_encoding_name)
        cwd = request.cwd

        text = eollib.convertToEOLFormat(text, eollib.EOL_LF)
        datalines = text.split('\n')

        # get the tidy config file
        configFile = self._prefProxy.prefs.getStringPref('tidy_configpath')
        if configFile and not os.path.exists(configFile):
            log.debug("The Tidy configuration file does not exist, please "
                     "correct your settings in the preferences for HTML.")
            configFile = None
            
        errorLevel = self._prefProxy.prefs.getStringPref('tidy_errorlevel')
        accessibility = self._prefProxy.prefs.getStringPref('tidy_accessibility')
        
        #Character encodings
        #-------------------
        #  -raw              to output values above 127 without conversion to entities
        #  -ascii            to use US-ASCII for output, ISO-8859-1 for input
        #  -latin1           to use ISO-8859-1 for both input and output
        #  -iso2022          to use ISO-2022 for both input and output
        #  -utf8             to use UTF-8 for both input and output
        #  -mac              to use MacRoman for input, US-ASCII for output
        #  -win1252          to use Windows-1252 for input, US-ASCII for output
        enc = '-raw'
        if request.encoding.python_encoding_name == 'utf-8':
            enc = '-utf8'
        elif request.encoding.python_encoding_name == 'latin-1' or \
             request.encoding.python_encoding_name.startswith('iso8859'):
            enc = '-latin1'
        elif request.encoding.python_encoding_name == 'cp1252':
            enc = '-win1252'
            
        argv = [os.path.join(self.koDirs.supportDir, "html", "tidy"),
                '-errors', '-quiet', enc]
        if argv_additions:
            argv += argv_additions

        if accessibility != '0':
            argv += ['-access', accessibility]
        if configFile:
            argv += ['-config', configFile]
        
        cwd = cwd or None
        # Ignore stdout, as tidy dumps a cleaned up version of the input
        # file on it, which we don't care about.
        log.debug("Running tidy argv: %r", argv)
        #print ("Running tidy argv: %s" % (" ".join(argv)))
        p = process.ProcessOpen(argv, cwd=cwd)
        stdout, stderr = p.communicate(text)
        lines = stderr.splitlines(1)

        # Tidy stderr output looks like this:
        #    Tidy (vers 4th August 2000) Parsing console input (stdin)
        #    line 12 column 1 - Error: <body> missing '>' for end of tag
        #    line 14 column 2 - Warning: <tr> isn't allowed in <body> elements
        # <snip>
        #    line 674 column 5 - Warning: <img> lacks "alt" attribute
        #    
        #    stdin: Doctype given is "-//W3C//DTD HTML 4.0 Transitional//EN"
        #    stdin: Document content looks like HTML 4.01 Transitional
        #    41 warnings/errors were found!
        #    
        #    This document has errors that must be fixed before
        #    using HTML Tidy to generate a tidied up version.
        #    
        #    The table summary attribute should be used to describe
        # <snip ...useful suggestion paragraph that we should consider using>
        # Quickly strip out uninteresting lines.
        lines = [l for l in lines if l.startswith('line ')]
        lines = self.filterLines(lines)
        results = koLintResults()
        resultRe = re.compile("""^
            line\s(?P<line>\d+)
            \scolumn\s(?P<column>\d+)
            \s-\s(?P<desc>.*)$""", re.VERBOSE)
        for line in lines:
            if enc == '-utf8':
                line = unicode(line,'utf-8')
            resultMatch = resultRe.search(line)
            if not resultMatch:
                log.warn("Could not parse tidy output line: %r", line)
                continue

            #print "KoHTMLLinter: %r -> %r" % (line, resultMatch.groupdict())
            result = KoLintResult()
            try:
                result.lineStart = int(resultMatch.group("line"))
                result.columnStart = int(resultMatch.group("column"))
            except ValueError:
                # Tidy sometimes spits out an invalid line (don't know why).
                # This catches those lines, and ignores them.
                continue
            result.description = resultMatch.group("desc")
            # We keep the "Error:"/"Warning:" on the description because
            # currently we do not get green squigglies for warnings.
            if result.description.startswith("Error:"):
                result.severity = result.SEV_ERROR
            elif result.description.startswith("Warning:") or \
                 result.description.startswith("Access:"):
                if errorLevel == 'errors':
                    # ignore warnings
                    continue
                result.severity = result.SEV_WARNING
            else:
                result.severity = result.SEV_ERROR

            # Set the end of the lint result to the '>' closing the tag.
            result.columnEnd = -1
            i = result.lineStart
            while i < len(datalines):
                # first pass -- go to first >, even if in attribute name
                if i == result.lineStart:
                    curLine = datalines[i-1][result.columnStart:]
                    offset = result.columnStart
                else:
                    curLine = datalines[i-1]
                    offset = 0
                end = curLine.find('>')
                if end != -1:
                    result.columnEnd = end + offset + 2
                    break
                i = i + 1
            if result.columnEnd == -1:
                result.columnEnd=len(datalines[i-1]) + 1
            result.lineEnd = i
            
            # Move back to the first non-blank line for errors
            # that appear on blank lines.  In empty and
            # near-empty buffers this result will end up at
            # the first line (which is 1-based in the lint system)
            if result.lineStart == result.lineEnd and \
               result.columnEnd <= result.columnStart:
                while result.lineStart > 0 and len(datalines[result.lineStart - 1]) == 0:
                    result.lineStart -= 1
                if result.lineStart == 0:
                    result.lineStart = 1
                result.lineEnd = result.lineStart
                result.columnStart = 1
                result.columnEnd = len(datalines[result.lineStart-1]) + 1

            results.addResult(result)
        return results


class KoHTML5CompileLinter(KoHTMLCompileLinter):
    _com_interfaces_ = [components.interfaces.koILinter]
    _reg_desc_ = "Komodo HTML 5 Tidy Linter"
    _reg_clsid_ = "{06b2f705-849d-462f-aafb-bb2e4dfd6d37}"
    _reg_contractid_ = "@activestate.com/koLinter?language=HTML5;1"
    _reg_categories_ = [
         ("category-komodo-linter", 'HTML5'),
         ]

    problem_word_ptn = re.compile(r'([ &<]?\w+\W*)$')
    leading_ws_ptn = re.compile(r'(\s+)')
    dictType = type({})
    def lint(self, request):
        encoding_name = request.encoding.python_encoding_name
        text = request.content.encode(encoding_name)
        if not text.strip():
            return koLintResults()
        textLines = text.splitlines()
        try:
            inputStream = cStringIO.StringIO(text)
            parser = html5lib.HTMLParser()
            try:
                doc = parser.parse(inputStream)
            finally:
                inputStream.close()
            errors = parser.errors
            #log.debug("**** Errors: \n%s\n", errors)
            results = koLintResults()
            groupedErrors = {}
            # Gather the grouped results by line/col/errorName, favoring dicts
            for posnTuple, errorName, params in parser.errors:
                lineNo = int(posnTuple[0]) - 1
                endColNo = int(posnTuple[1]) + 1
                key = "%d:%d:%s" % (lineNo, endColNo, errorName)
                if key not in groupedErrors:
                    groupedErrors[key] = [lineNo, endColNo, errorName, params]
                elif type(params) == self.dictType:
                    groupedErrors[key][3] = params
                else:
                    #log.debug("Ignoring additional params: %s", params)
                    pass
            for lineNo, endColNo, errorName, params in groupedErrors.values():
                #print "KoHTMLLinter: %r -> %r" % (line, resultMatch.groupdict())
                if lineNo >= len(textLines):
                    lineNo = len(textLines) - 1
                    while lineNo >= 0 and len(textLines[lineNo]) == 0:
                        lineNo -= 1
                    if lineNo < 0:
                        log.warn("No text to display for bug %s", errorName)
                        continue
                    endColNo = len(textLines[lineNo]) + 1
                probText = textLines[lineNo]
                probTextToHere = probText[:endColNo]
                #log.debug("Line %d, probText:%s, probTextToHere:%s",
                #          lineNo, probText, probTextToHere)
                m = self.problem_word_ptn.search(probTextToHere)
                if m:
                    startColNo = m.span(1)[0] + 1
                else:
                    m = self.leading_ws_ptn.match(probText)
                    if m:
                        startColNo = m.span(1)[1] + 1
                    else:
                        startColNo = 1
                result = KoLintResult()
                result.lineStart = result.lineEnd = lineNo + 1
                result.columnEnd = endColNo
                result.columnStart = startColNo
                result.description = self._buildErrorMessage(errorName, params)
                #TODO: Distinguish errors from warnings...
                result.severity = result.SEV_ERROR
                
                results.addResult(result)
        except ServerException:
            log.exception("ServerException")
            raise
        except:
            # non-ServerException's are unexpected internal errors
            log.exception("unexpected internal error")
            raise
        return results
    
    def _buildErrorMessage(self, errorName, params):
        if type(params) != self.dictType:
            if errorName in html5libErrorDict:
                return "%s: %s" % (html5libErrorDict[errorName], params)
            return "%s: %s" % (errorName, params)
        if errorName in html5libErrorDict:
            return html5libErrorDict[errorName] % params
        if len(items) == 0:
            if errorName[-1] == ":":
                return errorName[:-1]
            else:
                return errorName
        if len(items) == 1:
            k, v = items[0]
            if k == 'name':
                return "%s: %s" % (errorName, v)
            else:
                return "%s: for %s:%s" % (errorName, k, v)
        elif len(items) == 2:
            k1, v1 = items[0]
            k2, v2 = items[1]
            if k1 == "expectedName" and k2 == "gotName":
                return "%s: expected %s, got %s" % (errorName, v1, v2)
        return "%s: %s" % (errorName, " ;".join(["%s:%s" for k,v in items]))
