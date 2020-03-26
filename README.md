
GELUTILS
========

Tools and utilities for working with scientific GEL files.
Makes it easy to convert and annotate .GEL or .TIFF image files from e.g. Typhoon scanners and GelDocs.

The primary use of this application/package is to add lane annotations to gel images.
The application can be installed and used as any other application,
e.g. by simply double-clicking a .GEL file and then selecting the annotate-gel application to annotate the gel.
It features a simple GUI where you can add the text you want to display above each lane and
configure how the final gel image appears.
Gels can be scaled, cropped, rotated, etc.
The application will export a SVG file with the cropped/rotated gel image, overlayed by the given annotations.
The SVG file can be automatically converted to a PNG, which is sometimes more convenient for presentation usage.



FAQ: What are GEL images and who cares?
---------------------------------------

Gels are widely used in molecular biology and biotechnology for analyzing the size of biological molecules, e.g. DNA or
proteins.
When analysing samples on gels via gelelectrophoresis, samples are loaded at the top of the gel in well/indentations at
the top of the gel. Charged molecules are then dragged through the gel by applying an electric field across the gel.
Larger molecules have more interaction with the gel matrix. This drag reduces the migration rate through the gel.
Smaller molecules travels faster through the gel.
This creates a pattern of bands on the gel.
Bands from the a sample in one well will form a vertical "lane" as they travel through the gel.



Features and basic usage:
-------------------------

Current features:
* Quickly annotate lanes on gel using sample names from a plain text file.
* Linearize GEL files stored in MD GEL squareroot format (e.g. gel files from Typhoon scanners).
* A simple GUI to control the program.

Basic usage:
* Open your gel image with the included AnnotateGel App.
* Type lane annotations in the text box to the left,
* Configure image processing by altering the YAML-formatted dict in the text box to the right.
* Click "Annotate Gel" to create an SVG file with your gel image and the annotations overlayed at the top of the gel.



Bugs, feature suggestions and pull requests:
--------------------------------------------

If you find any bugs, please let me know -- they are usually very easy and fast to fix.

Also feel free to write me with feature suggestions.
Or, even better: Fork this repository, fix the bugs and
implement the features as you want, then send me a pull request :)



Installation:
--------------

**Command-line installation using pip:**
* This may be the easiest way to get and install gelutils.
* First, if you are using environments, create a new environment for gelutils -- or activate an existing environment you want to install gelutils into.
    * If using Anaconda, create a conda environment that includes ```numpy, pyyaml, six, pillow=2.7, cffi```.
    * Example: ```conda create -n gelutils six numpy pillow=2.7 pyyaml cffi```
* Then install gelutils using ```pip install gelutils```.


**Install gelutils in editable mode:**
* Activate/create environment for gelutils.
* Go to the folder where you want to place the gelutils package source.
* Install gelutils using ```pip install -e git+https://github.com/scholer/gelutils```


**Manual installation from source:**
* Download / git clone, go to the root directory. If you type ```ls``` (or ```dir``` on Windows) you should see README.md and REQUIREMENTS.txt files.
* If you are using Python environments, activate the environment you want to use for gelutils.
    * To create new conda environment for gelutils, type: ```conda create -n gelutils --file REQUIREMENTS.txt```
    * If the packages are not all available from Anaconda, type:
    ```conda create -n gelutils six numpy pillow=2.7 pyyaml cffi```,
    and use pip to install the rest.
* Make sure you have all required dependencies, e.g. using ```pip install -r REQUIREMENTS.txt```.
* Install using ```pip install -e .``` (the period at the end means "the current directory").


**Upgrading Gelutils:**

To update gelutils to the newest version, activate the python environment where you installed gelutils (if any),
then run: 

```
pip install -U gelutils
```


**Python Installation:**

In general, I recommend using either Anaconda or a package manager to install Python and pip.
Anaconda is available from [here](https://www.continuum.io/downloads).
If you are already using a package manager (e.g. [chocolatey](https://chocolatey.org/) on Windows),
you may want to use your package manager to install Python.

Inside your Python distribution you may want to have separate Python **environments**.
*Why do you need "environments"?*
 *  A: Some Python applications may require a very specific set of dependencies, which can sometimes be incompatible.
    For example, Gelutils requires a specific version of Pillow, an image processing library.
    Using the current version of Pillow, or a very old version, will give an error.
    However, what if you have another Python package or application which requires the newest version of Pillow?
    How do you make these work together, using the same Python installation?
    The answer is to have separate Python environments, one for each application.

Environments can be created and managed in a couple of different ways:
 * If you are using the Anaconda Python distribution, use ```conda``` command line tool
   to create environments and install packages (using ```pip``` when a conda package is not yet available).


**Cairo installation:**

Cairo is used for converting the annotated SVG files to PNG.

Cairo is an external graphics library, used by e.g. the GTK+ graphics toolkit used by many apps.

If you have GTK+ installed, you may already have the required Cairo dependency.

Otherwise, you will have to obtain the needed DLL.

The easiest way to intall the required DLL is to use [Alexander Shaduri’s GTK+ installer](https://gtk-win.sourceforge.io/home/index.php/Main/Downloads).

If you do not want to install GTK+, you can also just extract the GTK+ installer to a temporary directory (using e.g. 7zip), and copy the file `libcairo-2.dll` to `<PYTHON INSTALL DIR>\Library\bin`.

To check if Cairo has been installed, you can invoke one of the following commands from the terminal:

    $ python -c "import ctypes.util; print(ctypes.util.find_library('libcairo-2'))"
    $ python -c "import cairosvg"




Alternatives and prior art:
---------------------------

Here is a quick list of alternative tools for annotating Gel Images:

* Gel Annotator (this project).
* gelImage
    * A single-file Python GUI program to annotate TIFF gel images using wxPython and Cairo. 
    * Last updated 2015.
    * https://github.com/openpaul/gelImage
* GelScape
    * A wep-app for annotating gel images. Requires Java-enabled browser.
    * Also available as an offline Java app, which I haven't tried.
    * Last updated 2003.
    * Code not available on website or GitHub.
* General vector-graphics apps:
    * Adobe Illustrator.
    * InkScape.
    * PowerPoint.
* Generic image apps:
    * ImageJ.
* Python, Pillow, and Matplotlib to annotate the image.
* 



Troubleshooting:
----------------

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



Tips and Tricks:
----------------


### View/Open images after annotation: ###

* If you set ```open_webbrowser=true``` in the AnnotateGel app, it will use the webbrowser module to view the annotated SVG images.
* This works really well if e.g. Google Chrome is your default app for viewing SVG files.
* If, however, you have Adobe Illustrator (or similar) installed, this might be the default App for SVG files.
* This is not always optimal, since you will automatically see the latest version of the SVG file.
* To change the default app for viewing SVG files:
    * OSX: Right-click an SVG file, select ```Get Info``` in the context menu, then under ```Open with``` select the proper app, then ''make sure you click the "Change All..." button to make the change apply for all SVG files (otherwise it will only apply to that one file).
    * Windows: Shift + right-click an SVG file, select ```Open with```, then "Select file / other...", then select the proper app. This will generally apply to all files of the same filetype.


### Making AnnotateGel the default app for GEL and GAML files: ###

Using AnnotateGel as the default app for opening GEL or GAML files is fairly easy on Windows. However, on OS X, it requires a little bit of work.
* Before you proceed, determine where AnnotateGel was installed when you did ```pip install``` as the final installation step above. See the section below to determine where AnnotateGel is located.

On Windows, to use AnnotateGel as default application:
* Shift + right-click a .gel file, select "Open with...", then "Browse...", then locate AnnotateGel and select OK.

On OS X, using AnnotateGel as a default app is a little more involved. I suggest taking a look at these references:
[mborgerson](https://mborgerson.com/creating-an-executable-from-a-python-script), [stackexchange](http://apple.stackexchange.com/questions/153818/make-a-python-program-an-application/153828#153828).
But in short, the process looks like this:
* Open Automator (cmd+space, then type Automator).
* Create a new "Application" document.
* Add a "shell script" action to your workflow.
* Under ```Shell:``` select ```/bin/bash```, and under ```Pass input:``` select ```as arguments```.
* In the text box type: ```/path/to/bin/AnnotateGel "$@"``` (where ```/path/to/bin/AnnotateGel``` is the file location where AnnotateGel was installed, see below).
* Save this workflow as "AnnotateGel.app" (Menu "File -> Save" or Cmd+s). You can save it in whatever location you want, e.g. under "Applications", where you have your other applications.
* Now right-click a .gel file, select "Get Info", then under "Open with" select "Other...", then browse to select the "AnnotateGel.app" workflow/file you just saved with Automator. Check "Always Open With", and press "Add".
* Still in the "Get Info" window, press the "Change All..." button to use AnnotateGel.app to open all files.
* If you want to use AnnotateGel.app to also open .gaml files (gel annotation config files), simply right-click a .gaml file and repeat the previous two steps.



### Where is AnnotateGel and other gelutils apps installed? ###

The location where ```pip install``` installs the AnnotateGel executable files (aka binaries/scripts/apps) depends on (1) your platform, (2) your python distribution, and (3) whether you are using a python environment.

The easiest way to find AnnotateGel is to just search for it:
* OS X: Open Spotlight (Cmd + space), then type ```AnnotateGel```.
* Windows: Use Windows Search/Explorer (WindowsKey + F) or your preferred file-finder to find the AnnotateGel file. Note that Windows search sometimes doesn't find new files right away, and may need considerable time to "re-index" the file before it can be found. Blame Microsoft.
* Linux: Open terminal and type: ```find -name AnnotateGel ~/```. If it doesn't find anything in your home folder, try ```find -name AnnotateGel /```.

Lets go though some examples of where AnnotateGel is typically found after installation:
* Example 1: On OS X (platform) using Anaconda python distribution and installing in a python environment called "gelutils", the path to the installed AnnotateGel executable is ```/Users/rasmus/anaconda3/envs/gelutils/bin/AnnotateGel```.
* Example 2: On OS X (platform) using Anaconda python distribution and not using environments (aka "the default environment"), the path to the installed AnnotateGel executable is ```/Users/rasmus/anaconda3/bin/AnnotateGel```.
* Example 3: On OS X (platform) using the official python distribution from python.org and not using environments (aka "the default environment"), the path to the installed AnnotateGel executable is ```/Library/Frameworks/Python.framework/Versions/3.4/bin/AnnotateGel```.



TODO:
-----

Better icons:
* A better App icon.
* An icon for yaml/gaml files.
* An icon for gel files.


Documentation:
--------------

Please refer to the files in the 'doc/' directory for help and documentation.
And, of course, the source if you are so inclined.
