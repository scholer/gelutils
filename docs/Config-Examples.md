
Config example (with comments)
==============================

```

convertgelto: png        # Convert Gel image to PNG format
crop: 55%, 2%, 10%, 5%   # Crop 55% from the left side, 10% from the left, etc.
cropfromedges: true      # true, so  cropping from the right edge, not absolute coordinates.
dynamicrange: 100, 20000 # Pixels with value < 100 are white, pixels > 20000 are black, graytones in between.
embed: true              # Embed image data into the SVG file (rather than link to a file).
fn_substitution:         # Substitute "-[SYBR Gold]" with nothing when generating new file names.
- -[SYBR Gold]
- ''
flip_h: true            # Flip/mirror the gel horizontally
flip_v: true            # Flip the gel 
fontfamily: Arial       # Use Arial font for lane annotations.
fontsize: 15            # Set lane annotations font size to 15 pt.
fontweight: bold        # Make lane annotations bold.
gelfile: null           # Set to null to find gelfile automatically.
invert: true            # Invert gel image so bands appear black on white background.
laneidxstart: 3         # Start lane indexing at 3, rather than 1.
linearize: null         # Linearize gel data when creating PNG. (Default for .GEL files but not tiff.)
lineinputstyle: wikilist # My annotation lines begins with "*" because they were copy/pasted from a wiki list.
lines_includeempty: true # Include empty lines
openwebbrowser: true    # Open annotated files in webbrowser (or whatever is your application for SVG files)
overwrite: true         # Overwrite old files without warning.
pngfile: null           # Determine automatically.
pngfnfmt: '{yamlfnroot}_{dr_rng}{N_existing}{ext}'   # Name PNG file like this. Curly brackets are replaced with values.
pngmode: L              # Use 8-bit PNG mode.
remember_gelfile: null
reusepng: null
rotate: -6              # Rotate the gel image minus 6 degree counter-clockwise (= 6 degrees clockwise).
rotateexpands: false    # Do not make the gel file larger to accomodate the rotation.
saveyamlto: null
scale: 50%              # Scale the gel image to 50 % of its original size.
svgfnfmt: '{pngfnroot}_annotated{ext}'  # The SVG file is named based on pngfnfmt (above) plus "_annotated.svg".
svgtopng: true          # Convert the annotated SVG file to PNG. 
textfmt: "lane {idx}: {name}" # Each lane annotation from the left panel is prefixed by "lane 3:" (for the rightmost lane)
textrotation: 60        # Rotate lane annotations by 60 degrees from horizontal.
updateyaml: null
verbose: null
xmargin: 5%, 10%        # Add a 5% margin from the left-most lane to the left edge of the gel, and 10% on the right side.
xspacing: null
xtraspaceright: 50      # Add 50 extra pixels to the right to make a little more room for the annotation for the right-most lane.
yoffset: 200            # Add vertical space from the top of the SVG canvas to the top of the gel image.
ypadding: 10            # Add 10 pixel vertical space between gel image and lane annotations.


```