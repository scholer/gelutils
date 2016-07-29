


Changes since last release:
---------------------------

* New keyword 'filename_sub_re', using regex to substitute filename substrings.
* Renamed 'filename_substitution' keyword to 'filename_sub'.
* filename_sub (and filename_sub_re) now support more than two elements, FIND1, REPLACE1, FIND2, REPLACE2, etc.
* removed lines_commentmidchar keyword, should just use lines_commentchar consistently.
* Parsing command line args before loading system config, passing config_app_defaults to parser instead.
* Properly removing load_system_config and stdout/stderr/etc from config.


Release 0.6.0:
--------------

New and changed config keywords:

* For GUI program, openwebbrowser is now default behaviour.
* Renamed remember_gelfile to gelfile_remember, added lines_ prefix to annotation input keywords incl commentchar and commentmidchar. lines_commentchar and lines_commentmidchar now also documented in auto-generated docs.
* Command line options --stdout and --stderr to redirect stdout and stderr to file(s) given by these options. Useful when console is not available.


Other: 

* Changed how annotationfile is found
* Only use codecs.open for python2, not 3+. Fixed unicode issue (MacOS Automator scripts runs with ASCII as preferred encoding), better finding of annotationfile in "yaml-is-primary" mode.
* New 'config' module containing global variables/constants (will alter/configure app behaviour).
* setup: changed AnnotateGel_console script to annotategel_debug (all lower case) to prevent issues when uninstalling..
* print statements now use flush=True. This keyword is only for python 3.3+, so for python <3.3 we overwrite the builtin with a module-level print function.

Docs:

* Created/improved docs


