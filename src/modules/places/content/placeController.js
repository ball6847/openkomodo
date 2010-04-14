
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
 * Portions created by ActiveState Software Inc are Copyright (C) 2000-2010
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

// The Places controller.

if (typeof(ko) == 'undefined') {
    var ko = {};
}
if (!('places' in ko)) {
    ko.places = {};
}

xtk.include("clipboard");

(function(){
function PlacesController() {
    this.log = getLoggingMgr().getLogger("PlacesController");
    this.log.setLevel(ko.logging.LOG_DEBUG);
}
// The following two lines ensure proper inheritance (see Flanagan, p. 144).
PlacesController.prototype = new xtk.Controller();
PlacesController.prototype.constructor = PlacesController;

PlacesController.prototype.destructor = function() {
}

PlacesController.prototype.is_cmd_setPlace_enabled = function() {
    //this.log.debug("PlacesController.prototype.is_cmd_setPlace_enabled\n");
    return true;
}

PlacesController.prototype.do_cmd_setPlace = function() {
    //this.log.debug("PlacesController.prototype.do_cmd_setPlace\n");
    ko.places.manager.doSetLocalPlace();
}

PlacesController.prototype.is_cmd_setRemotePlace_enabled = function() {
    //this.log.debug("PlacesController.prototype.is_cmd_setRemotePlace_enabled\n");
    return true;
}

PlacesController.prototype.do_cmd_setRemotePlace = function() {
    //this.log.debug("PlacesController.prototype.do_cmd_setRemotePlace\n");
    ko.places.manager.doSetRemotePlace();
}

PlacesController.prototype.is_cmd_clearPlace_enabled = function() {
    //dump("PlacesController.prototype.is_cmd_clearPlace_enabled\n");
    return ko.places.manager.currentPlace != null;
}

PlacesController.prototype.do_cmd_clearPlace = function() {
    if (!this.is_cmd_clearPlace_enabled()) {
        this.log("do_cmd_clearPlace: invoked, but not enabled")
        return;
    }
    ko.places.manager.doClearPlace();
}

// cmdset_place_contextMenu controller

// PlacesController.prototype.is_cmd_bufferClose_supported -- always.
PlacesController.prototype.is_cmd_cutPlaceItem_enabled = function() {
    return true;
}
PlacesController.prototype.do_cmd_cutPlaceItem = function() {
    ko.places.manager.doCutPlaceItem();
}

PlacesController.prototype.is_cmd_copyPlaceItem_enabled = function() {
    return true;
},

PlacesController.prototype.do_cmd_copyPlaceItem = function() {
    if (!this.is_cmd_copyPlaceItem_enabled()) {
        this.log("do_cmd_copyPlaceItem: invoked, but not enabled")
        return;
    }
    ko.places.manager.doCopyPlaceItem();
}

PlacesController.prototype.is_cmd_pastePlaceItem_enabled = function() {
    if (ko.places.manager.copying == null) {
        return false;
    } else if (!xtk.clipboard.containsFlavors(["text/unicode"])) {
        return false;
    }
    return true;
}

PlacesController.prototype.do_cmd_pastePlaceItem = function() {
    if (!this.is_cmd_pastePlaceItem_enabled()) {
        this.log.debug("do_cmd_pastePlaceItem: invoked, but not enabled");
        return;
    }
    ko.places.manager.doPastePlaceItem();
}

PlacesController.prototype.is_cmd_findInPlace_enabled = function() {
    return ko.places.manager.currentPlaceIsLocal;
}

PlacesController.prototype.do_cmd_findInPlace = function() {
    if (!this.is_cmd_findInPlace_enabled()) {
        this.log.debug("do_cmd_findInPlace: invoked, but not enabled");
        return;
    }
    ko.places.manager.doFindInPlace();
}

PlacesController.prototype.is_cmd_replaceInPlace_enabled = function() {
    return ko.places.manager.currentPlaceIsLocal;
}

PlacesController.prototype.do_cmd_replaceInPlace = function() {
    if (!this.is_cmd_replaceInPlace_enabled()) {
        this.log.debug("do_cmd_replaceInPlace: invoked, but not enabled");
        return;
    }
    ko.places.manager.doReplaceInPlace();
}

PlacesController.prototype.is_cmd_places_showInFinder_enabled = function() {
    return ko.places.manager.currentPlaceIsLocal;
}

PlacesController.prototype.do_cmd_places_showInFinder = function() {
    if (!this.is_cmd_places_showInFinder_enabled()) {
        return;
    }
    ko.places.manager.doShowInFinder();
}

PlacesController.prototype.is_cmd_deletePlaceItem_enabled = function() {
    return true;
}

PlacesController.prototype.do_cmd_deletePlaceItem = function() {
    if (!this.is_cmd_deletePlaceItem_enabled()) {
        this.log.debug("do_cmd_deletePlaceItem: invoked, but not enabled");
        return;
    }
    ko.places.manager.doDeletePlace();
}

PlacesController.prototype.is_cmd_placeView_defaultView_enabled = function() {
    return true;
}

PlacesController.prototype.do_cmd_placeView_defaultView = function() {
    if (!this.is_cmd_placeView_defaultView_enabled()) {
        this.log.debug("do_cmd_placeView_defaultView: invoked, but not enabled");
        return;
    }
    ko.places.viewMgr.placeView_defaultView();
}

PlacesController.prototype.is_cmd_placeView_viewAll_enabled = function() {
    return true;
}

PlacesController.prototype.do_cmd_placeView_viewAll = function() {
    if (!this.is_cmd_placeView_viewAll_enabled()) {
        this.log.debug("do_cmd_placeView_viewAll: invoked, but not enabled");
        return;
    }
    ko.places.viewMgr.placeView_viewAll();
}

PlacesController.prototype.is_cmd_placeView_customView_enabled = function() {
    return true;
}

PlacesController.prototype.do_cmd_placeView_customView = function() {
    if (!this.is_cmd_placeView_customView_enabled()) {
        this.log.debug("do_cmd_placeView_customView: invoked, but not enabled");
        return;
    }
    ko.places.viewMgr.placeView_customView();
}

PlacesController.prototype.is_cmd_goPreviousPlace_enabled = function() {
    return ko.places.manager.can_goPreviousPlace();
}

PlacesController.prototype.do_cmd_goPreviousPlace = function() {
    if (!this.is_cmd_goPreviousPlace_enabled()) {
        this.log.debug("do_cmd_goPreviousPlace: invoked, but not enabled");
        return;
    }
    ko.places.manager.goPreviousPlace();
}

PlacesController.prototype.is_cmd_goNextPlace_enabled = function() {
    return ko.places.manager.can_goNextPlace();
}

PlacesController.prototype.do_cmd_goNextPlace = function() {
    if (!this.is_cmd_goNextPlace_enabled()) {
        this.log.debug("do_cmd_goNextPlace: invoked, but not enabled");
        return;
    }
    ko.places.manager.goNextPlace();
}
          
this.PlacesController = PlacesController;  // expose thru this namespace.
}).apply(ko.places);
