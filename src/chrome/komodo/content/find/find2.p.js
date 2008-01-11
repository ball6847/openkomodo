/* ***** BEGIN LICENSE BLOCK *****
 * Version: MPL 1.1/GPL 2.0/LGPL 2.1
 * 
 * The contents of this file are subject to the Mozilla Public License
 * Version 1.1 (the "License"); you may not use this file except in
 * compliance with the License. You may obtain a copy of the License at
 * http://www.mozilla.org/MPL/
 * 
 * Software distributed under the License is distributed on an "AS IS"
 * basis, WITHOUT WARRANTY OF ANY KIND, either express or implied. See the
 * License for the specific language governing rights and limitations
 * under the License.
 * 
 * The Original Code is Komodo code.
 * 
 * The Initial Developer of the Original Code is ActiveState Software Inc.
 * Portions created by ActiveState Software Inc are Copyright (C) 2000-2007
 * ActiveState Software Inc. All Rights Reserved.
 * 
 * Contributor(s):
 *   ActiveState Software Inc
 * 
 * Alternatively, the contents of this file may be used under the terms of
 * either the GNU General Public License Version 2 or later (the "GPL"), or
 * the GNU Lesser General Public License Version 2.1 or later (the "LGPL"),
 * in which case the provisions of the GPL or the LGPL are applicable instead
 * of those above. If you wish to allow use of your version of this file only
 * under the terms of either the GPL or the LGPL, and not to allow others to
 * use your version of this file under the terms of the MPL, indicate your
 * decision by deleting the provisions above and replace them with the notice
 * and other provisions required by the GPL or the LGPL. If you do not delete
 * the provisions above, a recipient may use your version of this file under
 * the terms of any one of the MPL, the GPL or the LGPL.
 * 
 * ***** END LICENSE BLOCK ***** */

/* Komodo's Find and Replace dialog (rev 2).
 *
 * TODOs:
 * - whither "Display results in Find Results 2 tab" checkbox?
 * - whither "Show 'Replace All' Results" checkbox?
 */

//---- globals

var log = ko.logging.getLogger("find");
//log.setLevel(ko.logging.LOG_DEBUG);

var koIFindContext = Components.interfaces.koIFindContext;
var koIFindOptions = Components.interfaces.koIFindOptions;

var widgets = null; // object storing interesting XUL element references
var gFindSvc = null;
var _gFindContext; // the context in which to search

var _g_btns_enabled_for_pattern = true;    // cache for update("pattern")
var _g_curr_default_btn = null;         // cache for _update_mode_ui()



//---- public methods for the dialog

function on_load() {
    try {
        gFindSvc = Components.classes["@activestate.com/koFindService;1"].
                   getService(Components.interfaces.koIFindService);
        _init_widgets();
        window.focus(); //TODO: necessary?
        _init_ui();
    } catch (ex) {
        log.exception(ex);
    }    
}

function on_unload() {
}

function on_focus(event) {
    if (event.target != document) {
        return;
    }
    // This onfocus event was for the window -- as oppposed to being for
    // a subelement in the window.
    if (typeof opener.ko.launch.find2_dialog_args != "undefined") {
        // This window was re-launched.
        // Note: We will still be using the same "opener" so effectively
        //       we are presuming we were launched from the main Komodo
        //       window.
        _init_ui()
    }
}

/**
 * Update as appropriate for some change in the dialog.
 *
 * @param changed {string} The name of the thing that changed. If
 *      null or not specified *everything* is updated (used for dialog
 *      initialization).
 */
function update(changed /* =null */) {
    var mode_changed = false;
    var opts = gFindSvc.options;
    
    // "Replace" checkbox state changed.
    if (changed == null || changed == "replace") {
        var repl = widgets.opt_repl.checked;
        _collapse_widget(widgets.repl_lbl, !repl);
        _collapse_widget(widgets.repl, !repl);
        (repl ? widgets.repl : widgets.pattern).focus();
        mode_changed = true;
    }

    // "Search in" menulist selection changed.
    if (changed == null || changed == "search-in") {
        var search_in = widgets.search_in_menu.value;
        switch (search_in) {
        case "files":
            _collapse_widget(widgets.dirs_row, false);
            _collapse_widget(widgets.subdirs_row, false);
            _collapse_widget(widgets.includes_row, false);
            _collapse_widget(widgets.excludes_row, false);
            break;
        default:
            _collapse_widget(widgets.dirs_row, true);
            _collapse_widget(widgets.subdirs_row, true);
            _collapse_widget(widgets.includes_row, true);
            _collapse_widget(widgets.excludes_row, true);

            // Persist the context type in some cases. This is used
            // to tell cmd_findNext and cmd_findPrevious whether to
            // cycle through the current doc or all open docs.
            if (search_in == "document" || search_in == "selection") {
                gFindSvc.options.preferredContextType = koIFindContext.FCT_CURRENT_DOC;
            } else if (search_in == "open-files") {
                gFindSvc.options.preferredContextType = koIFindContext.FCT_ALL_OPEN_DOCS;
            }
        }
        mode_changed = true;
    }
    
    // The pattern value changed.
    if (changed == null || changed == "pattern") {
        if (widgets.pattern.value && !_g_btns_enabled_for_pattern) {
            // We changed from no pattern string to some pattern string.
            // Enable the relevant buttons.
            _enable_widget(widgets.find_prev_btn);
            _enable_widget(widgets.find_next_btn);
            _enable_widget(widgets.replace_btn);
            _enable_widget(widgets.find_all_btn);
            _enable_widget(widgets.replace_all_btn);
            _g_btns_enabled_for_pattern = true;
        } else if (!widgets.pattern.value && _g_btns_enabled_for_pattern) {
            // We changed from a pattern string to no pattern string.
            // Disable the relevant buttons.
            _disable_widget(widgets.find_prev_btn);
            _disable_widget(widgets.find_next_btn);
            _disable_widget(widgets.replace_btn);
            _disable_widget(widgets.find_all_btn);
            _disable_widget(widgets.replace_all_btn);
            _g_btns_enabled_for_pattern = false;
        }
    }
    
    if (changed == null || changed == "regex") {
        opts.patternType = (widgets.opt_regex.checked ?
            koIFindOptions.FOT_REGEX_PYTHON : koIFindOptions.FOT_SIMPLE);
    }
    if (changed == null || changed == "case") {
        opts.caseSensitivity = (widgets.opt_case.checked ?
            koIFindOptions.FOC_INSENSITIVE : koIFindOptions.FOC_SENSITIVE);
    }
    if (changed == null || changed == "word") {
        opts.matchWord = widgets.opt_word.checked;
    }
    //if (changed == null || changed == "multiline") {
    //    //...
    //}
    if (changed == null || changed == "dirs") {
        opts.encodedFolders = widgets.dirs.value;
    }
    if (changed == null || changed == "search-in-subdirs") {
        opts.searchInSubfolders = widgets.search_in_subdirs.checked;
    }
    if (changed == null || changed == "includes") {
        opts.encodedIncludeFiletypes = widgets.includes.value;
    }
    if (changed == null || changed == "excludes") {
        opts.encodedExcludeFiletypes = widgets.excludes.value;
    }

    if (mode_changed) {
        _update_mode_ui();
        window.sizeToContent();
    }
}


function toggle_error() {
    if (widgets.pattern_error_box.hasAttribute("collapsed")) {
        widgets.pattern_error_box.removeAttribute("collapsed");
    } else {
        widgets.pattern_error_box.setAttribute("collapsed", "true");
    }
}


//---- internal support stuff

// Load the global 'widgets' object, which contains references to
// interesting elements in the dialog.
function _init_widgets()
{
    widgets = new Object();

    widgets.pattern = document.getElementById('pattern');
    widgets.repl_lbl = document.getElementById('repl-lbl');
    widgets.repl = document.getElementById('repl');

    widgets.opt_regex = document.getElementById('opt-regex');
    widgets.opt_case = document.getElementById('opt-case');
    widgets.opt_word = document.getElementById('opt-word');
    //widgets.opt_multiline = document.getElementById('opt-multiline');
    widgets.opt_repl = document.getElementById('opt-repl');

    widgets.pattern_error_box = document.getElementById('pattern-error-box');
    
    widgets.search_in_menu = document.getElementById('search-in-menu');

    widgets.dirs_row = document.getElementById('dirs-row');
    widgets.dirs = document.getElementById('dirs');
    widgets.subdirs_row = document.getElementById('subdirs-row');
    widgets.search_in_subdirs = document.getElementById('search-in-subdirs');
    widgets.includes_row = document.getElementById('includes-row');
    widgets.includes = document.getElementById('includes');
    widgets.excludes_row = document.getElementById('excludes-row');
    widgets.excludes = document.getElementById('excludes');

    widgets.find_prev_btn = document.getElementById('find-prev-btn');
    widgets.find_next_btn = document.getElementById('find-next-btn');
    widgets.replace_btn = document.getElementById('replace-btn');
    widgets.find_all_btn = document.getElementById('find-all-btn');
    widgets.replace_all_btn = document.getElementById('replace-all-btn');
    //widgets.mark_all_btn = document.getElementById('mark-all-btn');
    //widgets.close_btn = document.getElementById('close-btn');
    widgets.help_btn = document.getElementById('help-btn');
}

/**
 * Initialize the dialog UI from `opener.ko.launch.find2_dialog_args` data.
 */
function _init_ui() {
    var args = opener.ko.launch.find2_dialog_args || {};
    opener.ko.launch.find2_dialog_args = null;

    // If there is selected text then preload the find pattern with it.
    // Unless it spans a line, then set the search context to the
    // selection.
    var scimoz = null;
    var selection = null;
    var use_selection_as_pattern = false;
    var use_selection_as_context = false;
    try {
        scimoz = opener.ko.views.manager.currentView.scintilla.scimoz;
        selection = scimoz.selText;
    } catch(ex) {
        /* pass: just don't have a current editor view */
    }
    if (selection) {
        // If the selected text has newline characters in it or *is* an entire
        // line (without the end-of-line) then "search within selection".
        // Warning: ISciMoz.getCurLine() returns the whole line minus the
        // last char. If the EOL is two chars then you only get last part.
        // I.e. 'foo\r\n' -> 'foo\r'.
        var curr_line_obj = new Object;
        scimoz.getCurLine(curr_line_obj);
        var curr_line = curr_line_obj.value;
        if (selection.search(/\n/) != -1
            || selection == curr_line.substring(0, curr_line.length-1))
        {
            use_selection_as_context = true;
            // If a user does a search within a selection then the
            // "preferred" context is the current document (rather than
            // across multiple docs).
            gFindSvc.options.preferredContextType = koIFindContext.FCT_CURRENT_DOC;
        } else {
            // Otherwise, use the current selection as the first search
            // pattern completion.
            use_selection_as_pattern = true;
        }
    }

    // Determine the default pattern.
    var default_pattern = "";
    if (typeof args.pattern != "undefined") {
        default_pattern = args.pattern;
    } else if (use_selection_as_pattern) {
        default_pattern = selection;
    } else if (scimoz) {
        default_pattern = ko.interpolate.getWordUnderCursor(scimoz);
    }

    // Preload with input buffer contents if any and then give focus to
    // the pattern textbox.
    // Notes:
    // - The pattern textbox will automatically select all its contents
    //   on focus. If there are input buffer contents then we do *not*
    //   want this to happen, because this will defeat the purpose of
    //   the input buffer if the user is part way through typing in
    //   characters.
    // - Have to set focus in a timer because this could be called within
    //   an onfocus handler, in which Mozilla does not like .focus()
    //   calls.
    var input_buf = opener.ko.inputBuffer.finish();
    widgets.pattern.value = "";
    if (input_buf) {
        widgets.pattern.value = input_buf;
        window.setTimeout('_set_pattern_sel_focus();', 0);
    } else {
        widgets.pattern.value = default_pattern;
        widgets.pattern.focus();
    }

    // Set other dialog data (from the given args and from the
    // koIFindService.options).
    var opts = gFindSvc.options;
    widgets.repl.value = args.repl || "";
    widgets.opt_regex.checked
        = opts.patternType == koIFindOptions.FOT_REGEX_PYTHON;
    widgets.opt_case.checked
        = opts.caseSensitivity == koIFindOptions.FOC_INSENSITIVE;
    widgets.opt_word.checked = opts.matchWord;
    //widgets.opt_multiline.checked = ...
    widgets.dirs.value = opts.encodedFolders;
    widgets.search_in_subdirs.checked = opts.searchInSubfolders;
    widgets.includes.value = opts.encodedIncludeFiletypes;
    widgets.excludes.value = opts.encodedExcludeFiletypes;
    
    // Setup the UI for the mode, as appropriate.
    var mode = args.mode || "find";
    switch (mode) {
    case "find":
        widgets.opt_repl.checked = false;
        widgets.search_in_menu.value
            = (use_selection_as_context ? "selection" : "document");
        break;
    case "replace":
        widgets.opt_repl.checked = true;
        widgets.search_in_menu.value
            = (use_selection_as_context ? "selection" : "document");
        break;
    case "findinfiles":
        widgets.opt_repl.checked = false;
        widgets.search_in_menu.value = "files";
        break;
    case "replaceinfiles":
        widgets.opt_repl.checked = true;
        widgets.search_in_menu.value = "files";
        break;
    }
    update();

    //TODO
    //// The act of opening the find dialog should reset the find session.
    //// This is the behaviour of least surprise.
    //gFindSession.Reset();
}

function _set_pattern_sel_focus()
{
    widgets.pattern.focus();
    window.setTimeout('_set_pattern_sel_range();', 0);
}

function _set_pattern_sel_range()
{
    widgets.pattern.setSelectionRange(widgets.pattern.textLength,
                                      widgets.pattern.textLength);
}

/**
 * Update the UI as appropriate for the current mode.
 */
function _update_mode_ui() {
    var default_btn = null;
    
    if (widgets.opt_repl.checked) {
        switch (widgets.search_in_menu.value) {
        case "project":
        case "files":
            // Replace in Files: Replace All, Close, Help
            _collapse_widget(widgets.find_prev_btn, true);
            _collapse_widget(widgets.find_next_btn, true);
            _collapse_widget(widgets.replace_btn, true);
            _collapse_widget(widgets.find_all_btn, true);
            _collapse_widget(widgets.replace_all_btn, false);
            //_collapse_widget(widgets.mark_all_btn, true);
            default_btn = widgets.replace_all_btn;
            break
        default:
            // Replace: Find Next, Replace*, Replace All, Close, Help
            _collapse_widget(widgets.find_prev_btn, true);
            _collapse_widget(widgets.find_next_btn, false);
            _collapse_widget(widgets.replace_btn, false);
            _collapse_widget(widgets.find_all_btn, true);
            _collapse_widget(widgets.replace_all_btn, false);
            //_collapse_widget(widgets.mark_all_btn, true);
            default_btn = widgets.replace_btn;
        }
    } else {
        switch (widgets.search_in_menu.value) {
        case "project":
        case "files":
            // Find in Files: Find All*, Close, Help
            _collapse_widget(widgets.find_prev_btn, true);
            _collapse_widget(widgets.find_next_btn, true);
            _collapse_widget(widgets.replace_btn, true);
            _collapse_widget(widgets.find_all_btn, false);
            _collapse_widget(widgets.replace_all_btn, true);
            //_collapse_widget(widgets.mark_all_btn, true);
            default_btn = widgets.find_all_btn;
            break
        default:
            // Find: Find Previous, Find Next*, Find All, Mark All, Close, Help
            _collapse_widget(widgets.find_prev_btn, false);
            _collapse_widget(widgets.find_next_btn, false);
            _collapse_widget(widgets.replace_btn, true);
            _collapse_widget(widgets.find_all_btn, false);
            _collapse_widget(widgets.replace_all_btn, true);
            //_collapse_widget(widgets.mark_all_btn, false);
            default_btn = widgets.find_next_btn;
        }
    }
    
    // Set the default button.
    if (_g_curr_default_btn == default_btn) {
        /* do nothing */
    } else {
        if (_g_curr_default_btn) {
            _g_curr_default_btn.removeAttribute("default");
        }
        default_btn.setAttribute("default", "true");
    }
    _g_curr_default_btn = default_btn;
    
    // Setup re-used accesskeys.
    // Because of mode changes and limited letters, we are re-using some
    // accesskeys. The working set is defined by elements that have a
    // uses-accesskey="true" attribute. The data is in that element's
    // _accesskey attribute.
    var elem;
    var working_set = document.getElementsByAttribute(
            "uses-accesskey", "true");
    for (var j = 0; j < working_set.length; ++j) {
        elem = working_set[j];
        if (elem.getAttribute("collapsed")) {
            elem.removeAttribute("accesskey");
        } else {
            elem.setAttribute("accesskey",
                              elem.getAttribute("_accesskey"));
        }
    }
}


function _toggle_collapse(widget) {
    if (widget.hasAttribute("collapsed")) {
        widget.removeAttribute("collapsed");
    } else {
        widget.setAttribute("collapsed", "true");
    }
}

function _collapse_widget(widget, collapse) {
    if (collapse) {
        widget.setAttribute("collapsed", "true");
    } else {
        widget.removeAttribute("collapsed");
    }
}

function _disable_widget(widget) {
    widget.setAttribute("disabled", "true");
}
function _enable_widget(widget) {
    if (widget.hasAttribute("disabled")) {
        widget.removeAttribute("disabled");
    }
}


