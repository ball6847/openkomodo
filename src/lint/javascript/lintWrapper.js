/* Copyright (c) 2000-2011 ActiveState Software Inc.
   See the file LICENSE.txt for licensing information. */

// Populate with jslint defaults
var options = {
        rhino: true,
        forin: true,
        passfail: false
};
var includePath = "";
var includeBaseName = "fulljslint.js";
var i, arg, idx, argName, argValue, isJSHint = false;
var badArgs = false;
//print("arg len: " + arguments.length + "\n");
i = 0;
while (i < arguments.length) {
    arg = arguments[i];
    //print("arguments[" + i + "]: " + arg);
    if (arg[0] == '-') {
        if (arg == "-I") {
            includePath = arguments[i + 1];
            i += 1;
            //print("includePath(1: " + includePath + "\n");
        } else if (arg == "--jshint") {
            isJSHint = true;
            includeBaseName = "jshint.js";
            options.adsafe = false; // otherwise jshint gives weird "ADsafe" warnings
        } else if (arg.indexOf("--include") == 0) {
            idx = arg.indexOf("=");
            if (idx > -1) {
                includePath = arg.substr(idx + 1);
            } else {
                print("**** Unrecognized argument(1): " + arg);
                badArgs = true;
            }
        } else {
            print("**** Unrecognized argument(2): " + arg);
            badArgs = true;
        }
        if (includePath.length > 0
                && !/[\\\/]$/.test(includePath)) {
            includePath += "/";
        }
    } else {
        idx = arg.indexOf("=");
        if (idx == -1) {
            options[arg] = true;
            //print("Set options[" + arg + "] = true;\n");
        } else {
            var val = arg.substr(idx + 1);
            try {
                val = eval(val);
            } catch(ex) {
                //print("Failed to eval ('" + val + "'\n");
            }
            options[arg.substr(0, idx)] = val;
            //print("Set options[" + arg.substr(0, idx) + "] = " + val + "\n");
        }
    }
    i += 1;
}

if (!badArgs) {
    load(includePath + includeBaseName);
    const MAIN_OBJECT = isJSHint ? JSHINT : JSLINT;
    (function(options) {
        var input = "";
        var line, lines = [];
        while (true){
            line=readline();
            if (line === null) {
                break;
            }
            lines.push(line);
        }
        if (!lines.length) {
            return; // quit(1);
        }
        var input = lines.join("\n");
        var stoppingLineRE = /Stopping\.\s*\(\d+\%\s+scanned/;
        if (!MAIN_OBJECT(input, options)) {
            print("++++JSLINT OUTPUT:");  // Handler expects this line.
            for (var i = 0; i < MAIN_OBJECT.errors.length; i += 1) {
                var e = MAIN_OBJECT.errors[i];
                if (e) {
                    if (stoppingLineRE.test(e.reason)) {
                        // Do nothing
                    } else {
                        print('jslint error: at line ' + (e.line) + ' column ' + (e.character) + ': ' + e.reason);
                        print(e.evidence || "");
                    }
                }
            }
        }

    })(options);
}
