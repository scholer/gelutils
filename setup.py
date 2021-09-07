from distutils.core import setup


long_description = """

Tools and utilities to convert and annotate .GEL or .TIFF image files from e.g. Typhoon scanners and GelDocs.

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

"""


setup(
    name='gelutils',
    description=("Annotate and convert GEL images (PAGE, agarose gels, etc.) "
                 "acquired from e.g. Typhoon scanners, GelDocs or similar."),
    long_description=long_description,
    # long_description=open('README.txt').read(),
    version='0.6.3dev',  # update: version and download_url, also gelutils.__init__.__version__.
    packages=['gelutils', 'gelutils.tkui'],  # List all packages (directories) to include in the source dist.
    url="https://github.com/scholer/gelutils",
    download_url='https://github.com/scholer/gelutils/tarball/0.6.2',
    author="Rasmus S. Sorensen",
    author_email="rasmusscholer@gmail.com",
    license='GNU General Public License v3 (GPLv3)',
    keywords=["GEL", "Image", "Annotation", "PAGE", "Agarose", "DNA", "Protein",
              "SDS", "Gel electrophoresis", "Typhoon", "GelDoc",
              "Molecular biology", "Biotechnology"],

    # scripts or entry points..
    # scripts=['bin/annotate_gel.py'],

    # Automatic script creation using entry points has largely super-seeded the "scripts" keyword.
    # you specify: name-of-executable-script: module[.submodule]:function
    # When the package is installed with pip, a script is automatically created (.exe for Windows).
    # Note: The entry points are stored in ./gelutils.egg-info/entry_points.txt, which is used by pkg_resources.
    entry_points={
        'console_scripts': [
            # These should all be lower-case, else you may get an error when uninstalling:
            'gelannotator=gelutils.gelannotator:main',
            'annotategel_debug=gelutils.gelannotator_gui:main',  # Run as console script for debugging.
            'annotategel_gui=gelutils.gelannotator_gui:main',  # This may just be the official entry point.
            'svg2png=gelutils.imageconverter:svg2png_cli',  # edit: maybe just use cairosvg?
        ],
        'gui_scripts': [
            'AnnotateGel=gelutils.gelannotator_gui:main',
            # NOTE: GUI scripts does not work for Conda environments on Windows!
            # I'm having nothing but trouble with the GUI script entry point on Windows;
            # I get ImportError in the AnnotateGel-script.pyw bootstrapping script:
            # "The 'gelutils' distribution was not found and is required by the application".
            # I suspect it is an issue with conda environments for GUI, but I'm not sure.
            # When running the .pyw script, the default pythonw.exe is used, not the environment-specific one.
            # In any case, running the console script works just fine, only "problem" is that the console is open.
            # Many of the posted issues are Mac-specific, but I think there is a similar issue for Windows.
            # https://github.com/ContinuumIO/anaconda-issues/issues/446
            # https://github.com/ContinuumIO/anaconda-issues/issues/199#issuecomment-226976038
            # https://github.com/conda-forge/python-feedstock/issues/23


        ]
    },

    install_requires=[
        'pyyaml',       # YAML files
        'svgwrite',     # Composing svg files.
        'six',          # Python2.7 compatability
        'pillow==8.3.2',  # Image reading and manipulation.
        'numpy',        # Adjusting contrast, mostly.
        'cffi',         # Cairo - used to convert SVG files to PNG
        'cairocffi',
        'cairosvg',
    ],
    classifiers=[
        # How mature is this project? Common values are
        #   3 - Alpha
        #   4 - Beta
        #   5 - Production/Stable
        'Development Status :: 4 - Beta',

        # Indicate who your project is intended for
        # 'Intended Audience :: Developers',
        'Intended Audience :: Science/Research',
        'Intended Audience :: Education',
        'Intended Audience :: End Users/Desktop',
        'Intended Audience :: Healthcare Industry',

        # 'Topic :: Software Development :: Build Tools',
        'Topic :: Education',
        'Topic :: Scientific/Engineering',
        'Topic :: Scientific/Engineering :: Bio-Informatics',
        'Topic :: Scientific/Engineering :: Medical Science Apps.',

        # Pick your license as you wish (should match "license" above)
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',

        # Specify the Python versions you support here. In particular, ensure
        # that you indicate whether you support Python 2, Python 3 or both.
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',

        'Operating System :: MacOS',
        'Operating System :: Microsoft',
        'Operating System :: POSIX :: Linux',
    ],
)
