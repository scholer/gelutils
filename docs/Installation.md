
Gelutils - Installation:
=========================


### Command-line installation using pip: ###

* This may be the easiest way to get and install gelutils.
* First, if you are using environments, create a new environment for gelutils -- or activate an existing environment you want to install gelutils into.
    * If using Anaconda, create a conda environment that includes ```numpy, pyyaml, six, pillow=2.7, cffi```.
    * Example: ```conda create -n gelutils six numpy pillow=2.7 pyyaml cffi```
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


Python Installation:
--------------------

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

