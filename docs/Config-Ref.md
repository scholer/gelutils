argv: ['docs/docgen.py']
<table>
<tr><th>Keyword</th>  <th>Type and default</th>  <th>Help</th></tr>
<tr>  <td><pre>gelfile</pre></td> <td>gelfile</td> <td>Explicitly specify the gelfile to use. Often used in "yaml-mode" where the primary file is a YAML config file ("yaml-mode"). Specifying gelfile with this keyword will save it it the .gaml config file. Useful for having multiple .gaml config files all using the same .GEL file, e.g. with different crop regions if the GEL file contains multiple gels. </td>  </tr>
<tr>  <td><pre>loglevel</pre></td> <td>loglevel</td> <td>Logging level, e.g. 10, 30, or 'DEBUG', 'INFO. </td>  </tr>
<tr>  <td><pre>logtofile</pre></td> <td>logtofile</td> <td>Write log output to file rather than console. </td>  </tr>
<tr>  <td><pre>stdout</pre></td> <td>filename</td> <td>Write stdout stream to file rather than console. </td>  </tr>
<tr>  <td><pre>stderr</pre></td> <td>filename</td> <td>Write stderr stream to file rather than console. Defaults to same value as stdout. </td>  </tr>
<tr>  <td><pre>stdout_mode</pre></td> <td>file mode</td> <td>File open mode for stdout stream, if stdout is given. Default: 'w'. (default: w)</td>  </tr>
<tr>  <td><pre>stderr_mode</pre></td> <td>file mode</td> <td>File open mode for stderr stream, if stderr is given. Default: 'w'. (default: w)</td>  </tr>
<tr>  <td><pre>disable_logging</pre></td> <td>true/false</td> <td>Disable logging system. </td>  </tr>
<tr>  <td><pre>linearize</pre></td> <td>true/false</td> <td>Linearize gel input data stored in Square-Root Encoded Data (if Typhoon). </td>  </tr>
<tr>  <td><pre>dynamicrange</pre></td> <td>MIN, MAX</td> <td>Specify dynamic range (contrast). Valid argumets are 'MIN MAX', 'MAX' and 'auto', e.g. '1000, 20000' to set range from 1000 to 20000, '20000' to set range from zero to 20000, and 'auto' to determine range automatically. MIN and MAX are usually provided as absolute values e.g. '300 5000', but can also be specified as percentage values, e.g. '0.1% 99%'. If percentage or decimal values are given, the dynamic range is set such that MIN % of the pixels are below the lower range and (1.0 - MAX) of the pixels are above the dynamic range. If only one integer argument is given if is assumed to be the max, and min is set to 0. If specifying 'auto', the software will try to determine a suitable contrast range automatically. </td>  </tr>
<tr>  <td><pre>gelfile_remember</pre></td> <td>true/false</td> <td>Save gelfile in config for later use. </td>  </tr>
<tr>  <td><pre>invert</pre></td> <td>true/false</td> <td>Invert gel data, so zero is white, high intensity black. </td>  </tr>
<tr>  <td><pre>convertgelto</pre></td> <td>png/jpg/etc</td> <td>Convert gel to this format. (default: png)</td>  </tr>
<tr>  <td><pre>overwrite</pre></td> <td>true/false</td> <td>"Overwrite existing png file. If set to false, the program will re-use the any old PNG it finds instead of re-generating the PNG from the .GEL file. If you are playing around with e.g. the annotations, this can save a bit of computation. (default: True)</td>  </tr>
<tr>  <td><pre>pngfnfmt</pre></td> <td>format_string</td> <td>Customize the png filename using python string formatting. (default: {yamlfnroot}_{dr_rng}{N_existing}{ext})</td>  </tr>
<tr>  <td><pre>pngmode</pre></td> <td>pngmode</td> <td>PNG output format (bits per pixel). L = 8 bit integer, I = 16/32 bit. (default: L)</td>  </tr>
<tr>  <td><pre>filename_sub</pre></td> <td>FIND, REPLACE</td> <td>Substitute FIND with REPLACE in output filename. </td>  </tr>
<tr>  <td><pre>filename_sub_re</pre></td> <td>FIND, REPLACE</td> <td>Substitute all substrings matching the regex FIND with REPLACE in output filename. </td>  </tr>
<tr>  <td><pre>crop</pre></td> <td>LEFT, UPPER, RIGHT, LOWER</td> <td>Crop image to this box (left upper right lower) aka (x1 y1 x2 y2), Values can be either pixel values [500, 100, 1200, 400], or fractional/percentage values [5%, 3%, 95%, 0.9]. Note: Yes, 0.9 is 90%. If gel image is 1000 pixels wide, 0.9 or 90% are equivalent to 900 pixels. OBS! Note that by default the values are interpreted as &lt;strong&gt;ABSOLUTE COORDINATE VALUES&lt;/strong&gt; from the top, left pixel. If you want to change this behaviour such that the RIGHT and LOWER values are interpreted as the amount to crop away, e.g. 'crop 12% from the right edge', set ```cropfromedges``` to true. </td>  </tr>
<tr>  <td><pre>cropfromedges</pre></td> <td>true/false</td> <td>If true, the crop values RIGHT and LOWER defined above specifies pixels from their respective edges instead of absolute coordinates from the upper left corner. Default: false. </td>  </tr>
<tr>  <td><pre>scale</pre></td> <td>scalefactor</td> <td>"Scale the gel by this amount. Can be a single value for uniform scaling, or two values for different scaling in x vs y. Can be given as float (0.1, 2.5) or percentage (10%, 250%). </td>  </tr>
<tr>  <td><pre>rotate</pre></td> <td>angle</td> <td>Rotate gel image by this angle (counter-clockwise). Default: 0. </td>  </tr>
<tr>  <td><pre>rotateexpands</pre></td> <td>true/false</td> <td>When rotating, the image size expands to make room. False (default) means that the gel will keep its original size. </td>  </tr>
<tr>  <td><pre>flip_h</pre></td> <td>true/false</td> <td>Flip image horizontally left-to-right. </td>  </tr>
<tr>  <td><pre>flip_v</pre></td> <td>true/false</td> <td>Flip image vertically top-to-bottom. </td>  </tr>
<tr>  <td><pre>svgfnfmt</pre></td> <td>format_string</td> <td>How to format the png filename (if created). (default: {pngfnroot}_annotated{ext})</td>  </tr>
<tr>  <td><pre>pngfile</pre></td> <td>filename</td> <td>Use this pngfile instead of the specified gelfile. </td>  </tr>
<tr>  <td><pre>reusepng</pre></td> <td>true/false</td> <td>Prefer png file over the specified gelfile. </td>  </tr>
<tr>  <td><pre>yoffset</pre></td> <td>int-or-fraction</td> <td>Y offset (how far down the gel image should be). </td>  </tr>
<tr>  <td><pre>ypadding</pre></td> <td>int-or-fraction</td> <td>Vertical space between gel image and annotations. </td>  </tr>
<tr>  <td><pre>xmargin</pre></td> <td>left, right</td> <td>Margin to the right and left of lane annotations to the outer edge of GEL image. </td>  </tr>
<tr>  <td><pre>xspacing</pre></td> <td>int-or-fraction</td> <td>Force a certain x spacing between lanes. </td>  </tr>
<tr>  <td><pre>xtraspaceright</pre></td> <td>int-or-fraction</td> <td>Add additional padding/whitespace to the right side of the gel image. This is sometimes needed if the gel is not wide enough for the last lane annotation. </td>  </tr>
<tr>  <td><pre>textrotation</pre></td> <td>angle</td> <td>Rotate lane annotations by this angle (counter-clockwise). Default: 70. </td>  </tr>
<tr>  <td><pre>fontsize</pre></td> <td>size (int)</td> <td>Specify default font size, e.g. 12 or 16. </td>  </tr>
<tr>  <td><pre>fontfamily</pre></td> <td>fontfamily</td> <td>Specify default font family, e.g. arial or MyriadPro. </td>  </tr>
<tr>  <td><pre>fontweight</pre></td> <td>fontweight</td> <td>Font weight: normal | bold | bolder | lighter | 100 | 200 | 300 | 400 | 500 | 600 | 700 | 800 | 900 | inherit. </td>  </tr>
<tr>  <td><pre>textfmt</pre></td> <td>format_string</td> <td>How to format the lane annotations, e.g. '{idx} {name}'. Format keys include: idx, name. Default: '{name}'. </td>  </tr>
<tr>  <td><pre>laneidxstart</pre></td> <td>int</td> <td>Change the start number of the {idx} format parameter of lane annotations. </td>  </tr>
<tr>  <td><pre>yamlfile</pre></td> <td>filename</td> <td>Load options from YAML file, update and save. </td>  </tr>
<tr>  <td><pre>saveyamlto</pre></td> <td>filename</td> <td>Force saving yaml to this file when complete. </td>  </tr>
<tr>  <td><pre>updateyaml</pre></td> <td>true/false</td> <td>Update yaml settings after run to reflect the settings used. (default: False)</td>  </tr>
<tr>  <td><pre>embed</pre></td> <td>true/false</td> <td>Embed image data in svg file. (default) (default: True)</td>  </tr>
<tr>  <td><pre>annotationsfile</pre></td> <td>filename</td> <td>Load lane annotations from this file. If not specified, will try to guess the right file. </td>  </tr>
<tr>  <td><pre>lines_inputstyle</pre></td> <td>string-spec</td> <td>This can be used to change how lines in the sample annotation file are interpreted. Default is to use all non-empty lines that does not begin with '#'. Set this to 'wikilist' to only include lines that starts with either of #, *, -, +. </td>  </tr>
<tr>  <td><pre>lines_includeempty</pre></td> <td>true/false</td> <td>Whether to include empty lines. Not applicable to 'wikilist' lines_inputstyle (use blank lines starting with '#' in this case). (default: False)</td>  </tr>
<tr>  <td><pre>lines_listchar</pre></td> <td>string-spec</td> <td>If annotations are copy-pasted from a wiki/markdown list and you want to strip the list charaacter (e.g. '*' or '#'), specify the character here. Default: auto-detect. </td>  </tr>
<tr>  <td><pre>lines_commentchar</pre></td> <td>string-spec</td> <td>Lines starting with this character are ignored (comments). Default: auto-detect. </td>  </tr>
<tr>  <td><pre>openwebbrowser</pre></td> <td>true/false</td> <td>Open annotated svg file in default webbrowser. Default: Do not open files. (default: True)</td>  </tr>
<tr>  <td><pre>svgtopng</pre></td> <td>true/false</td> <td>Save svg as png (requires cairo package). </td>  </tr>
</table>
