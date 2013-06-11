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

/* -*- Mode: C++; tab-width: 4; indent-tabs-mode: nil; c-basic-offset: 4 -*- */

#ifndef __nsSciMoz_h__
#define __nsSciMoz_h__

#include <stdio.h> 
#include <string.h> 

//#define SCIMOZ_DEBUG
//#define SCIMOZ_COCOA_DEBUG
//#define SCIDEBUG_REFS

#ifdef _WINDOWS
// with optimizations on, we crash "somewhere" in this file in a release build
// when we drag from scintilla into mozilla, over an tree
// komodo bugzilla bug 19186
// #pragma optimize("", off)
#else
#ifndef XP_MACOSX
#include <gdk/gdkx.h>
#include <gdk/gdkprivate.h> 
#include <gtk/gtk.h> 
#include <gdk/gdkkeysyms.h>
#include <gtk/gtksignal.h>

#include <gtk/gtkplug.h>

/* Xlib/Xt stuff */
#ifdef MOZ_X11
#include <X11/Xlib.h>
#include <X11/Intrinsic.h>
#include <X11/cursorfont.h>
#endif
#endif
#endif 

/**
 * {3849EF46-AE99-45f7-BF8A-CC4B053A946B}
 */
#define SCI_MOZ_CID { 0x3849ef46, 0xae99, 0x45f7, { 0xbf, 0x8a, 0xcc, 0x4b, 0x5, 0x3a, 0x94, 0x6b } }
#define SCI_MOZ_PROGID "@mozilla.org/inline-plugin/application/x-scimoz-plugin"

#include "nscore.h"
#include "nsObserverList.h"
#include "nsObserverService.h"
#include <nsIConsoleService.h>

#include "nsCOMPtr.h"
#include "nsIServiceManager.h"
#include "nsISupports.h"
#include "nsStringGlue.h"
#include "nsIAllocator.h"
#include "nsIDOMWindow.h"
#include "nsWeakReference.h"
#include "nsIObserverService.h"
#include "nsILocalFile.h"
#include "nsIProgrammingLanguage.h"

#include "ISciMoz.h"
#include "ISciMozEvents.h"
#include "nsIClassInfo.h"

#include "npapi_utils.h"

#ifdef _WINDOWS
#include <windows.h>
#include <shellapi.h>
#include <richedit.h>
#undef FindText // conflicts with our definition of that name!
#endif

#ifdef XP_MACOSX
#import <Cocoa/Cocoa.h>
#endif

#include <Scintilla.h>
#include "sendscintilla.h"
#include <SciLexer.h>

#ifdef XP_MACOSX
#include <Platform.h>
#include <ScintillaCocoa.h>
#endif

#define SCIMAX(a, b) (a > b ? a : b)
#define SCIMIN(a, b) (a < b ? a : b)
#define LONGFROMTWOSHORTS(a, b) ((a) | ((b) << 16))

// XXX also defined in ScintillaWin.cxx
#ifndef WM_UNICHAR
#define WM_UNICHAR                      0x0109
#endif


/* Thread checks are default in dev builds, off in release */

#if BUILD_FLAVOUR == dev

#include "nsThreadUtils.h"
#define IS_MAIN_THREAD() NS_IsMainThread()

#define SCIMOZ_CHECK_THREAD(method, result) \
    if (!IS_MAIN_THREAD()) { \
	fprintf(stderr, "SciMoz::" method " was called on a thread\n"); \
	return result; \
    }

#else
#define SCIMOZ_CHECK_THREAD(method, result)
#endif // # if BUILD_FLAVOUR

// Ensure that SciMoz has not been closed. Bug 82032.
#define SCIMOZ_CHECK_ALIVE(method, result) \
    if (isClosed) { \
	fprintf(stderr, "SciMoz::" method " used when closed!\n"); \
	return result; \
    }

#define SCIMOZ_CHECK_VALID(method) \
    SCIMOZ_CHECK_THREAD(method, NS_ERROR_FAILURE) \
    SCIMOZ_CHECK_ALIVE(method, NS_ERROR_FAILURE)


#include "SciMozEvents.h"

class SciMozPluginInstance;

// We must implement nsIClassInfo because it signals the
// Mozilla Security Manager to allow calls from JavaScript.

class nsClassInfoMixin : public nsIClassInfo
{
  // These flags are used by the DOM and security systems to signal that 
  // JavaScript callers are allowed to call this object's scritable methods.
  NS_IMETHOD GetFlags(PRUint32 *aFlags)
    {*aFlags = nsIClassInfo::PLUGIN_OBJECT | nsIClassInfo::DOM_OBJECT;
     return NS_OK;}
  NS_IMETHOD GetImplementationLanguage(PRUint32 *aImplementationLanguage)
    {*aImplementationLanguage = nsIProgrammingLanguage::CPLUSPLUS;
     return NS_OK;}
  // The rest of the methods can safely return error codes...
  NS_IMETHOD GetInterfaces(PRUint32 * aCount, nsIID * ** aArray)
    {
      /* Return the list of interfaces that nsSciMoz supports. */
      const uint32_t count = 5;
      *aCount = count;
      nsIID **array;
      *aArray = array = static_cast<nsIID**>(nsMemory::Alloc(count * sizeof(nsIID*)));
      if (!array)
        return NS_ERROR_OUT_OF_MEMORY;

      uint32_t index = 0;
      nsIID* clone;
#define PUSH_IID(id)                                                          \
      clone = static_cast<nsIID *>(nsMemory::Clone(&NS_GET_IID( id ),           \
                                                   sizeof(nsIID)));             \
      if (!clone)                                                               \
          goto oom;                                                             \
      array[index++] = clone;

      PUSH_IID(ISciMoz)
      PUSH_IID(ISciMoz_Part0)
      PUSH_IID(ISciMoz_Part1)
      PUSH_IID(ISciMoz_Part2)
      PUSH_IID(ISciMoz_Part3)
#undef PUSH_IID

      return NS_OK;
oom:
      while (index)
        nsMemory::Free(array[--index]);
      nsMemory::Free(array);
      *aArray = nullptr;
      return NS_ERROR_OUT_OF_MEMORY;
    }
  NS_IMETHOD GetHelperForLanguage(PRUint32 /*language*/, nsISupports ** /*_retval*/)
    {return NS_ERROR_NOT_IMPLEMENTED;}
  NS_IMETHOD GetContractID(char * * /*aContractID*/)
    {return NS_ERROR_NOT_IMPLEMENTED;}
  NS_IMETHOD GetClassDescription(char * * /*aClassDescription*/)
    {return NS_ERROR_NOT_IMPLEMENTED;}
  NS_IMETHOD GetClassID(nsCID * * /*aClassID*/)
    {return NS_ERROR_NOT_IMPLEMENTED;}
  NS_IMETHOD GetClassIDNoAlloc(nsCID * /*aClassIDNoAlloc*/)
    {return NS_ERROR_NOT_IMPLEMENTED;}
};

#if defined(HEADLESS_SCIMOZ)
// Dummy platform holder.
typedef struct _PlatformInstance {
	void *foo;
}
PlatformInstance;

#else

#ifdef XP_PC
static const char* gInstanceLookupString = "instance->pdata";

typedef struct _PlatformInstance {
	WNDPROC	fDefaultWindowProc;
	WNDPROC fDefaultChildWindowProc;
}
PlatformInstance;
#endif 

#if defined(XP_UNIX) && !defined(XP_MACOSX)
typedef struct _PlatformInstance {
	NPSetWindowCallbackStruct *ws_info;
	GtkWidget *moz_box;
}
PlatformInstance;
#define PLAT_GTK 1
#include "ScintillaWidget.h"
#endif 

#if defined(XP_MACOSX)
#include <Cocoa/Cocoa.h>
typedef struct _PlatformInstance {
    bool       firstVisibilityRequest;
#ifdef SCIMOZ_COCOA_DEBUG
    NPWindow   lastWindow;
#endif
}
PlatformInstance;
#endif

#endif  // else not HEADLESS_SCIMOZ

class SciMoz : public ISciMoz,
               public ISciMoz_Part0,
               public ISciMoz_Part1,
               public ISciMoz_Part2,
               public ISciMoz_Part3,
               public nsClassInfoMixin,
               public nsSupportsWeakReference
               
{
private:
    // Used to cache the "text" property - resets when the buffer changes.
    nsString _cachedText;
    
    // brace match support
    long bracesStyle;
    long bracesCheck;
    bool bracesSloppy;
    
    bool FindMatchingBracePosition(int &braceAtCaret, int &braceOpposite, bool sloppy);
    void BraceMatch();
    
public:
#if defined(HEADLESS_SCIMOZ)
  SciMoz();
#endif
  SciMoz(SciMozPluginInstance* plugin);
  ~SciMoz();

protected: 
    NPWindow* fWindow;
//    nsPluginMode fMode;
    PlatformInstance fPlatform;

    void *portMain;	// Native window in portable type
    WinID wMain;	// portMain cast into a native type
    WinID wEditor;
    WinID wParkingLot;  // temporary parent window while not visible.

#ifdef USE_SCIN_DIRECT	
    SciFnDirect fnEditor;
    long ptrEditor;
#endif

    bool initialised;
    bool isClosed;      // If the plugin was removed... Scintilla was destroyed.
    bool parked;
    int width;
    int height;
    EventListeners listeners;
    bool bCouldUndoLastTime;
    bool bCouldRedoLastTime;

    long SendEditor(unsigned int Msg, unsigned long wParam = 0, long lParam = 0);
    NS_IMETHODIMP ConvertUTF16StringSendMessage(int message, PRInt32 length, const PRUnichar *text, PRInt32  *_retval);

    void SciMozInit();  // Shared initialization code.
    void Create(WinID hWnd);
    void PlatformCreate(WinID hWnd);
    void Notify(long lParam);
    void Resize();
    NS_IMETHOD _DoButtonUpDown(bool up, PRInt32 x, PRInt32 y, PRUint16 button, bool bShift, bool bCtrl, bool bAlt);

#ifdef XP_MACOSX
	void HideScintillaView(bool disabled);
	static void NotifySignal(intptr_t windowid, unsigned int iMessage, uintptr_t wParam, uintptr_t lParam);
	Scintilla::ScintillaCocoa *scintilla;
#endif
#ifdef XP_PC
    void LoadScintillaLibrary();
#endif

public:
  nsString name;
  // native methods callable from JavaScript
  NS_DECL_ISUPPORTS
  NS_DECL_ISCIMOZLITE
  NS_DECL_ISCIMOZ
  NS_DECL_ISCIMOZ_PART0
  NS_DECL_ISCIMOZ_PART1
  NS_DECL_ISCIMOZ_PART2
  NS_DECL_ISCIMOZ_PART3

    void PlatformNew(void);

    // Destroy is always called as we destruct.
    nsresult PlatformDestroy(void);

    // SetWindow is called as Mozilla gives us a window object.
    // If we are doing "window parking", we can attach
    // our existing Scintilla to the new Moz window.
    nsresult PlatformSetWindow(NPWindow* window);

    // ResetWindow is called as the Mozilla window dies.
    // If we are doing "window parking", this is when we park.
    // Will also be called if Moz ever hands us a new window
    // while we already have one.
    nsresult PlatformResetWindow();

    PRInt16 PlatformHandleEvent(void* event);

    // Notify that scimoz was closed.
    void PlatformMarkClosed(void);

#ifdef XP_MACOSX_USE_CORE_ANIMATION
    void *GetCoreAnimationLayer();
#endif

//    void SetMode(nsPluginMode mode) { fMode = mode; }

#ifdef XP_PC
    static LRESULT CALLBACK WndProc(HWND hWnd, UINT Msg, WPARAM wParam, LPARAM lParam);
    static LRESULT CALLBACK ParkingLotWndProc(HWND hWnd, UINT Msg, WPARAM wParam, LPARAM lParam);
    static LRESULT CALLBACK ChildWndProc(HWND hWnd, UINT Msg, WPARAM wParam, LPARAM lParam);
#endif 

#if defined(XP_UNIX) && !defined(XP_MACOSX)
    int sInGrab;
    static void NotifySignal(GtkWidget *, gint wParam, gpointer lParam, SciMoz *scimoz);
#endif 

    // NPRuntime support
    static void SciMozInitNPIdentifiers();
    bool HasProperty(NPIdentifier name);
    bool GetProperty(NPIdentifier name, NPVariant *result);
    bool SetProperty(NPIdentifier name, const NPVariant *value);
    bool HasMethod(NPIdentifier name);
    bool Invoke(NPP instance, NPIdentifier name, const NPVariant *args, uint32_t argCount, NPVariant *result);

    // NPRuntime custom methods
    bool DoBraceMatch(const NPVariant *args, uint32_t argCount, NPVariant *result);
    bool MarkClosed(const NPVariant *args, uint32_t argCount, NPVariant *result);
    bool HookEvents(const NPVariant *args, uint32_t argCount, NPVariant *result);
    bool UnhookEvents(const NPVariant *args, uint32_t argCount, NPVariant *result);
    bool GetStyledText(const NPVariant *args, uint32_t argCount, NPVariant *result);
    bool GetCurLine(const NPVariant *args, uint32_t argCount, NPVariant *result);
    bool GetLine(const NPVariant *args, uint32_t argCount, NPVariant *result);
    bool AssignCmdKey(const NPVariant *args, uint32_t argCount, NPVariant *result);
    bool ClearCmdKey(const NPVariant *args, uint32_t argCount, NPVariant *result);
    bool GetTextRange(const NPVariant *args, uint32_t argCount, NPVariant *result);
    bool CharPosAtPosition(const NPVariant *args, uint32_t argCount, NPVariant *result);
    bool SendUpdateCommands(const NPVariant *args, uint32_t argCount, NPVariant *result);
    bool GetWCharAt(const NPVariant *args, uint32_t argCount, NPVariant *result);
    bool ReplaceTarget(const NPVariant *args, uint32_t argCount, NPVariant *result);
    bool ReplaceTargetRE(const NPVariant *args, uint32_t argCount, NPVariant *result);
    bool SearchInTarget(const NPVariant *args, uint32_t argCount, NPVariant *result);

    bool AddChar(const NPVariant *args, uint32_t argCount, NPVariant *result);
    bool ButtonDown(const NPVariant *args, uint32_t argCount, NPVariant *result);
    bool ButtonUp(const NPVariant *args, uint32_t argCount, NPVariant *result);
    bool ButtonMove(const NPVariant *args, uint32_t argCount, NPVariant *result);
    bool EndDrop(const NPVariant *args, uint32_t argCount, NPVariant *result);

protected:
  SciMozPluginInstance* mPlugin;
};

#endif

