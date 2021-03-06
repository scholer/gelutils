
TYPICAL USAGE AND SETUP
========================

The easiest way to invoke the Gel Annotator GUI is to create a shortcut
on your desktop to one of the shell scripts in the bin/ folder,
and then drag your gel files onto this shortcut.

For windows you should use the .bat file in bin/, while
on OS X and Linux you use the file ending with '.sh'.

Gel files can be either GEL/TIF files, or PNG/JPG.
The software will linearize GEL files by default.

You write the lanes in the text input area to the left.

The text area to the right shows a long list of options.

But, before we go through these, it might be informative to go through
the program's workflow:

 1. First, if you have a GEL or TIF file, or if you have asked
    the program to perform transformations (crop, rotate, scale, etc),
    then the program will create a PNG file that it can use for annotation.
    (If you are starting from a PNG file, this is simply used as-is.)

 2. Second, the program create a SVG file with the PNG file and the
    annotations from the left text area.

 3. Third, the program can use the SVG file to create a
    PNG image with annotations.

The third step is optional; the generated SVG file with annotations
is perfectly fine for most purposes, except the file size is a little large.



 PROGRAM OPTIONS
====================

Image related options:

    * crop: <left>, <top>, <right>, <bottom> to crop the gel.
        if you set cropfromedges to true, right and bottom are from the edge,
        otherwise they are absolute coordinates.
    * rotate: <angle> will rotate the gel.
        if you set rotateexpands to true, the image is expanded to accomodate
        the full image after rotation.
    * dynamicrange: <min>, <max> will set the minimum and maximum values
        of the dynamic range. Also known as adjusting the contrast ;-)

    * invert: If you set invert to true, the image is inverted. This is the default for GEL files.
    * linearize: perform linearization of GEL data. This is also default for GEL files.

Text annotation options:

    * fontfamily, fontsize, fontweight: used to change the font (duh)

    * textrotation: <angle> controls the angle of the lane annotations.

    * textfmt: can be used to format the lane annotation string.
        Default is "{name}", which just adds the annotation.
        Changing this to e.g. "{idx:02} - {name}" would add the lane
        number to the annotation: "01 - 10 bp marker".
        You can use laneidxstart to change the idx start number (default: 0)

    * yoffset and ypadding are used to control the vertical position of the
        lane annotations: Increasing yoffset will add more whitespace above the
        gel, making more room for the annotations. ypadding controls the
        vertical space between the top of the gel and the annotations.

    * xmargin, xspacing, extraspaceright are used to control the horizontal
        position of the annotations.
    * xmargin: <left>, <right> controls the horizontal position of the first
        and last annotation.
    * extraspacingright can be used to add a bit of extra space to the right,
        to avoid the rightmost annotations to be cropped.
    * xspacing can be used to manually override the horizontal distance
        between annotations.



Files and workflow options:

    * openwebbrowser : open the generated files when complete.

    * pngfile : use this png file for annotations (instead of the GEL file).

    * reusepng : if set to true, the program re-uses the previously generated PNG file
        if available, thus skipping the (somewhat slow) conversion of GEL data.

    * svgtopng : convert the annotated SVG file as PNG image.

    * annotationsfile : the file to read and write annotations to/from.

    * yamlfile : the file to read and write yaml settings to.



