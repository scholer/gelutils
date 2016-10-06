


Changes since last release:
---------------------------

* Updated docstrings, updated .gitignore.
* Fixed: Sane ranking of configs. Config loaded from yaml file now takes precedence over everything incl command line switches. Use config_template if you want command line switches to take precedence.
* Fixed: Opening stdout/stderr redirection files in line-buffered mode (buffering=1) to eliminate issue with delayed printing of error messages.
* Fixed: Error where GAML file is being reset when browse-selecting GEL file even when _primary_file is yaml.
* New: primary_file can now be specified as a separate argument to GelAnnotatorApp. This better reflects the new mode of operation which is based on whether the primary file is a .gel or .gaml file.
* New: Regarding updateyaml and persisting final parameters: Previously, updateyaml=True meant overwriting the main yaml file with the final parameters. Now, I use config_save_final_params to save the final parameters and update_yaml is instead used to update the GUI widget config display.
* Updated Installation.md docs describing how to Create Automator application script on Mac/OSX.
* New feature: Gel images can now be rotated using rotate="auto". This uses the new auto_rotate module which is called in geltransformer.processimage(). This will find an optimal rotation such that bands and other features are aligned vertically and horizontally.  
* Removed official support for python 2. (You can probably still make it work with python 2 with relative ease, but that should be as separate branch/fork, instead of trying to support both with the same python files.)


Release 0.6.1:
--------------

* New keyword 'filename_sub_re', using regex to substitute filename substrings.
* Renamed 'filename_substitution' keyword to 'filename_sub'.
* filename_sub (and filename_sub_re) now support more than two elements, FIND1, REPLACE1, FIND2, REPLACE2, etc.
* removed lines_commentmidchar keyword, should just use lines_commentchar consistently.
* Parsing command line args before loading system config, passing config_app_defaults to parser instead.
* Properly removing load_system_config and stdout/stderr/etc from config.
* Updated command line args help and metavars
*


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


