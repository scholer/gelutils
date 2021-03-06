
Gelutils - Installation:
=========================


### Command-line installation using pip: ###

* This may be the easiest way to get and install gelutils.
* First, if you are using environments, create a new environment for gelutils -- or activate an existing environment you want to install gelutils into.
    * If using Anaconda, create a conda environment that includes ```numpy, pyyaml, six, pillow=2.7, cffi```.
    * Example: ```conda create -n gelutils python=3 pillow=2.7 six numpy pyyaml cffi```
* Then install gelutils using ```pip install gelutils```.


### Install gelutils in editable mode: ###

1. Activate/create environment for gelutils.
2. Go to the folder where you want to place the gelutils package source.
3. Install gelutils using ```pip install -e git+https://github.com/scholer/gelutils```


### Manual installation from source: ###

1. Download / git clone, go to the root directory. If you type ```ls``` (or ```dir``` on Windows) you should see README.md and REQUIREMENTS.txt files.
2. If you are using Python environments, activate the environment you want to use for gelutils.
    * To create new conda environment for gelutils, type: ```conda create -n gelutils --file REQUIREMENTS.txt```
    * If the packages are not all available from Anaconda, type:
    ```conda create -n gelutils six numpy pillow=2.7 pyyaml cffi```,
    and use pip to install the rest.
3. Make sure you have all required dependencies, e.g. using ```pip install -r REQUIREMENTS.txt```.
4. Install using ```pip install -e .``` (the period at the end means "the current directory").


### Upgrading Gelutils: ###

To update gelutils to the newest version, activate the python environment where you installed gelutils (if any),
then run: 

```
pip install -U gelutils
```




Installing dependencies:
------------------------

To run the program, you need Python. Python is very widely used and may already be
present on your system. (Open a terminal and type 'python' to check.)

    * GelUtils have been developed for python 2.7
    * It might work on python 3+, but it is a pain to ensure that it runs on both python 2 and 3.

If it is not present, use your package manager to install it.
If you are on Windows, you can either download the default python distribution
or one of the "fully featured" distributions:
    * python.org/download       - The "official" distribution.
    * continuum.io/downloads    - Anaconda, my favorite distribution.
    * enthought.com/downloads   - Enthought Canopy, another good distribution.
    * winpython.sourceforge.net - WinPython is another, slightly older distribution.


The primary dependencies are:
    * yaml (pyyaml)
    * Python Image Library, PIL - or Pillow.
    * numpy  (to linearize GEL data)
    * svgwrite (to create svg file with annotations)
    * cairo, cairosvg and cairocffi  -- or alternatively just imagemagick  (to generate the last, annotated PNG image)
    * six (for python 2 & 3 compatability)

You should be able to generate most of these through your distribution's package manager.
If it is not available through the package manager, use pip:
    >>> pip search <package>        - to search for packages.
    >>> pip install <package>       - to install a package.

For generating the last PNG image with annotations, the best results are produced
with cairosvg+cairocffi, and the Cairo toolkit.
However, these can be a bit tricky to install, especially on windows.



### Installing Cairo graphics dependency

Here are some useful links to get Cairo installed on Windows:
* https://pythonhosted.org/cairocffi/overview.html
* https://cairographics.org/download/
* http://www.gtk.org/download/win64.php - The official GTK+ installer.
* http://gtk-win.sourceforge.net/home/index.php/Main/Downloads - Alexander Shaduri's GTK+ installer.
* https://groups.google.com/forum/#!topic/wxpython-dev/xi5NJY3xE_8
* https://github.com/tschoonj/GTK-for-Windows-Runtime-Environment-Installer/releases
* http://win32builder.gnome.org/, e.g. http://win32builder.gnome.org/gtk+-bundle_3.6.4-20131201_win64.zip 



Steps:
1. Download and install one the GTK+ installers mentioned above. 
    Make sure to let the installer set PATH variable.
    If you don't want to actually install GTK+, you can also just extract the files and add the 
    `<GTK DIR>/bin` directory to your `$PATH` environment variable.
2. Install with `pip install cairocffi cairosvg`.
3. Verify your installation by running the following command in a new terminal:
    `python -c "import cairocffi; print('ALL OK')"`
    If you see "ALL OK" printed, then cairocffi has been properly configured.
    Otherwise, try to download and install a different version of GTK+/Cairo - or 
    follow the troubleshooting guide below.



#### Cairo - troubleshooting

First, open a new terminal, and print the `PATH` environment variable, 
and make sure the Cairo/GTK `bin\` directory has been added to the search PATH:
* On Windows: `echo %PATH%`
* On OSX/Linux: `echo $PATH`


Then, see if python can find your cairo library (binary .dll or .so file):

    python -c "import ctypes.util; path = ctypes.util.find_library('libcairo-2'); print(path)"
    python -c "import ctypes.util; path = ctypes.util.find_library('cairo-2'); print(path)"

If both of these commands prints `None`, then Python is unable to find your cairo binary.
Please make sure that you have properly configured the PATH environment variable.
In particular, make sure the GTK path you've added ended with `\bin`, i.e. not just the root GTK folder.

Otherwise, try to see if you can manually load the .DLL/.SO binary library:

    python -c "import cffi; ffi = cffi.FFI(); ffi.dlopen('libcairo-2')"


If you get "OSError: cannot load library libcairo.so.2: error 0x7e":

* This can happen if your Cairo library is either not properly installed, 
    or if you have the wrong version installed,
    for instance if your python is 64-bit and the Cairo/GTK library is 32-bit.
    Try to install a different version of GTK/Cairo.
* Update: The official GTK installer is no longer available from the official website, 
    but there are other Windows installers out there, see links above.
    Again, just extract and add the `bin\` directory to your `PATH` environment variable.
* For Windows, try downloading a GTK installer from http://win32builder.gnome.org:
    * The following worked for me last time: 
        http://win32builder.gnome.org/gtk+-bundle_3.6.4-20131201_win64.zip - extract 
        and add the `bin\` folder to your path.



### Alternatives to Cairo

**ImageMagick:**
If you already have ImageMagick installed you might want to just use ImageMagick as a fallback in lieu of Cairo.
(ImageMagick  is one of the best and ubiquitous tools for converting and transforming images - highly recommended.)


**Inkscape:**
You can also use Inkscape to convert SVG files to PNG. 
You will have to do this from the command line as a separate step.


**Matplotlib:**
Matplotlib can also be used to annotate images and create SVG and PNG output.
This, however, has not yet been implemented in `Gelutils`.





Installation - Troubleshooting:
-------------------------------

Generally, one cause of troubles during installation is the Cairo dependencies.
Cairo is used to convert SVG files to PNG, but is not strictly needed if you only need the SVG files.
It is also possible to use other methods to convert SVG files to PNG, e.g. ImageMagick, Illustrator, Preview, etc.
If you find that you cannot resolve Cairo-related issues during installation, you can install Gelutils without it using
```pip install --no-deps gelutils svgwrite pyyaml six Pillow==2.7 numpy```, then


The cairocffi dependency uses the C Foreign Function Interface (c ffi) to interact with Cairo C code.
In order to compile cairocffi, you must have ```libffi-dev``` installed.
* On Linux: ```sudo apt-get install libffi-dev``` (sometimes called _libffi-devel_)


If you get a "compiler" error, make sure you have a compiler installed.
* On Linux/Ubuntu, install with ```sudo apt-get install gcc```.
* On OS X, simply typing gcc should allow you to install the Mac developer tools.
* On Windows, hopefully pip can find a binary wheel for you because building on Windows is still a PITA.
    * The ```cffi``` library is generally available as a binary wheel for Anaconda.
    If ```cffi``` install is your problem and you are using Anaconda, try installing ```cffi``` using: ```conda install cffi```.





Appendix I: Python Installation:
--------------------------------

In general, I recommend using either Anaconda or a package manager to install Python and pip.
Anaconda is available from [here](https://www.continuum.io/downloads).
If you are already using a package manager (e.g. [chocolatey](https://chocolatey.org/) on Windows),
you may want to use your package manager to install Python.

I also recommend using dedicated *Python environments*, 
inside your Python distribution,
and creating a dedicated python environment for this gelutils app.

* *Q: What is the advantage of using python "environments"?*
*  A: Some Python applications may require a very specific set of dependencies, which can sometimes be incompatible.
    For example, Gelutils requires a specific version of Pillow, an image processing library.
    Using the current version of Pillow, or a very old version, will give an error.
    However, what if you have another Python package or application which requires the newest version of Pillow?
    How do you make these work together, using the same Python installation?
    The answer is to have separate Python environments, one for each application.

Environments can be created and managed in a couple of different ways:
 * If you are using the Anaconda Python distribution, use ```conda``` command line tool
   to create environments and install packages (using ```pip``` when a conda package is not yet available).



Appendix II: Standard environments and entry points:
----------------------------------------------------



Conda ENVIRONMENTS:
* gelutils = dev version at /Dev/Gelutils, installed using ```pip install -e```
* gelutils-release-testing = sdist release test env, installed using ```python setup.py sdist && pip install pip install dist/gelutils-<version>.tar.gz```
* gelutils-pypi-test = PyPI release test env, installed using ```pip install gelutils```.

Entry points:
* AnnotateGel = Main GUI app, intended for regular users.
* AnnotateGel_debug = GUI app, launched from terminal to get stdout/stderr directly in console. (Does not work when launched as Automator App).
* * AnnotateGel_debug entry point was previously named AnnotateGel_console.




Appendix III: Create Automator App (OS X / MacOS)
-------------------------------------------------


Notes:
* Use "$@" to refer to "all arguments given to the Automator App/script".
* Use > to redirect stdout to file, use &> to redirect both stderr and stdout to file.
* Use & at the end to start as background process.
* Redirecting stdout/stderr may alter the default behaviour of e.g. builtin open() so it uses ascii instead of utf-8.
  This is because it may alter the default/preferred encoding.
* If, for some reason, it is not possible to redirect stdout/stderr using standard methods (```&>```),
  then you can use ```--stdout``` and ```--stderr``` arguments to ask the App to redirect the streams.
  (The redirect is only done AFTER loading config files. But that means you can use ```stdout``` and ```stderr```
  keywords to configure redirection in the system-level config.)
* Caveat: When redirecting stdout/stderr to a file object, the stream may not be written immediately unless you flush,
  e.g. using the ```flush``` keyword: ```print("Flushing!", flush=True)```.
* The same caveat about delayed printing is true if App is invoked through Automator.
* However, if using --stdout/--stderr to redirect, then annotategel will make sure to open the file in line-buffered
  mode, which eliminates this issue.

Example Automator script:

    # Using dev version: *ACTIVE*
    /Users/rasmus/anaconda3/envs/gelutils/bin/AnnotateGel "$@" --stdout /Users/rasmus/appdata/gelutils/AnnotateGel.stdout

    # Testing release version:
    # /Users/rasmus/anaconda3/envs/gelutils-release-testing/bin/AnnotateGel "$@" --stdout /Users/rasmus/appdata/gelutils/AnnotateGel.stdout

    # Testing PyPI version:
    # /Users/rasmus/anaconda3/envs/gelutils-pypi-test/bin/AnnotateGel "$@" &> /Users/rasmus/appdata/gelutils/AnnotateGel.out

    # If you get errors, just open AnnotateGel_console from within a terminal using:
    # /Users/rasmus/anaconda3/envs/gelutils/bin/AnnotateGel_debug [args, ...]



#### Q: I really want to have a console/terminal displaying print messages. Isn't that possible?


A1: I tried to get an online terminal using
```open -a Terminal /path/to/bin/AnnotateGel_console "$@"```
But that doesn't forward $@ to the script, but instead opens two terminals one for each input.


A2: Could just forward to empty file if you want.
This will launch an external terminal which ```tail```s a file to which you are redirecting stdout/stderr.
Obviously, this is pretty complex and weird, and only works when print messages are being ```flush```ed to file.

    # In Automator "Run Shell Script" (bash) action:
    # Note: $$ is process id (pid); & at the end of a command starts it in the background and continues script
    echo "Automator App script: Starting AnnotateGel_console script..."
    echo " - pwd is: `pwd`\n"
    echo " - saving stdout to file: $$.tmp"
    /Users/rasmus/anaconda3/envs/gelutils/bin/AnnotateGel_console "$@" > $$.tmp &

    # Then: (1) create a script that tails your log file, (2) make it executable and (3) you execute it:
    # c.f. http://stackoverflow.com/questions/22520948/how-to-view-stdout-of-script-run-within-automator

    echo "tail -f $$.tmp" > x.command
    chmod +x x.command
    open x.command

    read -p "Press [Enter] to continue... "



#### Q: How can I get the proper AnnotateGel icon for my Automator Application script?

Method 1: If you already have another application with the icon you want for your App script:
* Find the source app with the icon you want
* Get Info of the source app (cmd-i)
* Click on the icon inside the source app's info window (Not the one in the big Preview section at the bottom, if you have one of those; the little one in the top-left corner.)
* Copy it (cmd-c)
* Get Info of the automator script (i.e., the destination app) (cmd-i)
* Click on the icon inside the destination app's info window
* Paste the icon from the clipboard (cmd-v)

Method 2: If you want to use an arbitrary icon for your App script:
* (Create your icns icon file - however you want)
* Open Applications Folder, right-click on automator script and select "view package contents"
* Add your icon to resources folder and rename it to AutomatorApplet.icns

Refs:
* http://apple.stackexchange.com/questions/369/can-i-change-the-application-icon-of-an-automator-script


Note: The above is only the icon for the Automator script as displayed inside
the Applications folder (or when you select a default app for GEL/GAML files).
However, since the Automator script launches AnnotateGel as an external process,
it will not automatically use the same icon.
The actual window icon, displayed in the application drawer or when you ALT+TAB (or CMD+TAB)
through open apps, is specified by tkinter using ```tkroot.iconbitmap(<path-to-icon>)```,
just like how the app title is specified using ```tkroot.title("AnnotateGel (Gelutils)")```.


Refs:
* http://stackoverflow.com/questions/18537918/set-window-icon
* http://forums.fedoraforum.org/showthread.php?t=297279
* http://stackoverflow.com/questions/29973246/python-tkinter-command-iconbitmap
* https://www.daniweb.com/programming/software-development/threads/249857/changing-the-tkinter-icon
* https://www.tcl.tk/man/tcl/TkCmd/tk_mac.htm#M22
* https://iconverticons.com/online/
* http://stackoverflow.com/questions/20860325/python-3-tkinter-iconbitmap-error-in-ubuntu
* http://stackoverflow.com/questions/11176638/python-setting-application-icon/11180300#11180300
* https://groups.google.com/forum/#!topic/comp.lang.python/xaobxaJwQrs
* http://www.jamesstroud.com/jamess-miscellaneous-how-tos/icons/tkinter-title-bar-icon
