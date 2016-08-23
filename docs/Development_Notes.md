
General development notes:
--------------------------

Code and issue-tracking at github: https://github.com/scholer/gelutils


Extra python requirements for development:

* ```mkdocs``` for docs generation and deployment.
   MkDocs further requires ```Markdown```, ```Jinja```, ```Tornado```, ```Click```, ```Livereload```, and ```MarkupSafe```.
* ```mdx_linkify``` to auto-recognize links in Markdown files, using ```extensions=["linkify"]```.
   Requires ```html5lib```, and ```bleach```.
* ```pandoc``` to convert README.md to README.rst during PyPI deployment.
* ```pytest``` for testing.
* ```twine ``` for uploading files (only for old python versions).


Packages available from Anaconda (if you use conda for your package management,
install these with ```conda install``` before installing other packages with ```pip```):
```
conda install jinja2 tornado click markupsafe pandoc pytest numpy
```


Setting up for Gelutils development (see also README.md):

0. Make a dedicated python environment for gelutils, e.g.:
   ```conda create -n gelutils pip numpy Pillow==2.7 six pyyaml cffi pandoc pytest jinja```
1. cd to your dev folder and download repo: ```git clone https://github.com/scholer/gelutils.git```
2. Install gelutils into your python environment in editable mode: ```cd gelutils```, then ```pip install -e .```
3. Note: You can combine steps 1+2 into one: ```pip install -e git+https://github.com/scholer/gelutils```
4. Make sure all dev requirements are installed: ```pip install -r requirements_dev.txt```

* Note 1: If you want to make releases, you should additionally create two extra python environments,
  one for testing the sdist (```gelutils-sdist-test```)
  and another to verify the PyPI release (```gelutils-pypi-test```).
* Note 2: Consider deleting and re-creating the ```gelutils-pypi-test``` environment for every release/dist,
  using ```conda create -n gelutils pip numpy Pillow==2.7 six pyyaml cffi```,
  then ```pip install gelutils```.
  (You do not need to install "requirements_dev.txt" dependencies in pypi-test environment.)
  To delete a conda environment, just delete the ```gelutils-pypi-test``` directory inside the Anaconda3 directory.



Release build and distribution:
-------------------------------


Release protocol:

1. Make sure all tests passes.
   Verify that both annotategel_debug script and AnnotateGel gui entry points are functional and able to complete.
   Preferably verify that it works both when invoked from console and from Automator script.
2. Bump version number (version+download_url in setup.py and version in gelutils/__init__.py),
   then ```git commit```.
3. Change to separate python build/dist environment (e.g. ```gelutils-release-testing``` or ```gelutils-sdist-test``` -
   This is *NOT* the same as your ```gelutils``` development environment),
   build release with ```python setup.py sdist```,
   install build in sdist environment using ```pip install dist/gelutils-<version>.tar.gz```,
   and run tests.
4. Register release and upload source distribution to PyPI test site:
   ```python setup.py register -r pypitest```, then ```python setup.py sdist upload -r pypitest```,
   then check https://testpypi.python.org/pypi/gelutils/ and make sure it looks right.
5. Register release and upload production PyPI site and check https://pypi.python.org/pypi/gelutils/
   ```python setup.py register -r pypi```, then ```python setup.py sdist upload -r pypi```.
   Note: On old python distributions ```python setup.py upload``` will use unencrypted communication,
   consider using ```twine``` if you are distributing using a python version older than 3.4.
6. Tag this version in git with ```git tag <version> -m "message"```, then push it with
   ```git push --follow-tags``` (or ```git push --tags``` if you have already pushed the branch/commits)
   You can also create tags/releases using Github's interface, c.f. https://help.github.com/articles/creating-releases/.
7. Test the PYPI release using the ```gelutils-pypi-test``` environment,
   preferably also on a different platform/OS as well.
   Use ```pip install -U gelutils``` to update.

If you find an error at any point, go back to step 1.


setup.py example files and guides:

* https://github.com/pypa/sampleproject/blob/master/setup.py
* https://hynek.me/articles/sharing-your-labor-of-love-pypi-quick-and-dirty/

Regarding versioning:
* I *am* trying to adhere to [semantic versioning](http://semver.org).
* I do *not* prefix version names/tags with ```v```, although this is customary and allowed by semver.
* Refs:
* * https://help.github.com/articles/creating-releases/
* * https://git-scm.com/book/en/v2/Git-Basics-Tagging
* * http://stackoverflow.com/questions/18216991/create-a-tag-in-github-repository




Docs generation and deployment:
--------------------------------


Currently using **MkDocs** for doc generation and **GitHub Pages** for hosting, c.f. [www.mkdocs.org/user-guide/deploying-your-docs/](www.mkdocs.org/user-guide/deploying-your-docs/)


To see the current docs locally at [127.0.0.1:8000/](http://127.0.0.1:8000/):

```
$ source activate gelutils-sdist-test # or source activate gelutils-release-testing
$ cd ~/dev/gelutils
$ mkdocs serve

```


Deploying to GitHub pages: (this is what I'm currently using)

* Push docs to ```gh-pages``` branch, docs available at [scholer.github.io/gelutils](https://scholer.github.io/gelutils)

```
mkdocs gh-deploy --clean
```


Deploying to pythonhosted (PyPI):

* Use setuptools in your setup.py, docs available at [pythonhosted.org/gelutils/](http://pythonhosted.org/gelutils/)

```
# (I'm NOT using this at the moment -- using gh-deploy above instead.)
mkdocs build --clean
python setup.py upload_docs --upload-dir=site
```


Documentation - alternatives:
-----------------------------

Doc generation

* Sphinx
* MkDocs - Generates static docs in your project dir


Doc hosting:

* Readthedocs - using Sphinx
* Github project pages - using e.g. MkDocs
* Pythonhosted.org - build docs locally and upload using PyPI/setuptools.



**Solution #1: Sphinx + ReadTheDocs**

* The "traditional" approach, widely supported.
* Sphinx has Markdown support (although was originally reST only).
* Docs can be auto-generated from source. Although auto-generated docs are somewhat frowned upon.
* Requires a bit more configuration than MkDocs.



**Soution #2: MkDocs + GitHub project pages (selected)**

* Build static docs with MkDocs
* Push branch to your github repository.



Documentation Refs:

* http://www.mkdocs.org/
* http://www.mkdocs.org/user-guide/configuration
* http://www.mkdocs.org/user-guide/deploying-your-docs/
* http://www.mkdocs.org/user-guide/writing-your-docs/
* http://docs.python-guide.org/en/latest/writing/documentation/
* https://help.github.com/articles/creating-project-pages-manually/
* https://python.libhunt.com/project/mkdocs/vs/sphinx
* https://wiki.python.org/moin/DocumentationTools




README/Documentation format: Markdown or reST?
------------------------------------------------

Markdown and reStructured Text are somewhat compatible.

One major difference is reST's pervasive use of *directives*, lines starting with two periods ```..```.

reST links are created using a trailing underscore ```mylink_```. The URI can either be embedded in the text using angle brackets, or it can be defined using a directive:

```
External hyperlink with embedded URI, like `Python <http://www.python.org/>`_.

External hyperlinks, like Python_.

.. _Python: http://www.python.org/

```

Markdown: Differences between GitHub and standard Markdown:

* GitHub support automatic link recognition, i.e. https://scholer.github.io/gelutils is a link when parsed by GitHub e.g. README.md, but not when parsed by standard Markdown.
* GitHub understands lists even without an empty line above them. Which I use all the time.


Unfortunately, neither Markdown nor reStructuredText supports automatic link recognition in their default configuration.

* GitHub does support link recognition and generation, but MkDocs does not.
* [linkify](https://github.com/daGrevis/mdx_linkify)   - Recognises links/urls using Bleach, with or without http:// scheme in url. Nice.
* [urlize](https://github.com/r0wb0t/markdown-urlize)  - parsed using regexes.
* https://github.com/markdown-it/linkify-it  (JavaScript library)


Markdown vs re-structured text (rst) for README vs description_long in setup.py:

* https://bitbucket.org/pypa/pypi/issues/148/support-markdown-for-readmes - PyPI feature request.
* http://stackoverflow.com/questions/26737222/pypi-description-markdown-doesnt-work/26737672#26737672 - how to convert Markdown to reST for use in setup.py using pypandoc with automatic fallback.
* https://gist.github.com/dupuy/1855764 -- commonalities between md and .rst
* http://docutils.sourceforge.net/docs/user/rst/demo.html, http://docutils.sourceforge.net/docs/user/rst/demo.txt -- reST demo


reStructured Text refs:

* http://www.sphinx-doc.org/en/stable/rest.html
* http://docutils.sourceforge.net/docs/user/rst/quickref.html



About configuring setup.py
---------------------------

General refs:

* https://setuptools.readthedocs.io/en/latest/setuptools.html
* https://packaging.python.org/distributing/
* https://docs.python.org/3/distutils/setupscript.html
* http://www.ianbicking.org/docs/setuptools-presentation/
* http://matthew-brett.github.io/pydagogue/installing_scripts.html


Entry points vs scripts keywords:

* http://stackoverflow.com/questions/18787036/difference-between-entry-points-console-scripts-and-scripts-in-setup-py

Requirements:

* https://packaging.python.org/requirements/


setup.py examples:

* https://github.com/pypa/sampleproject/blob/master/setup.py

pip install:

* https://pip.pypa.io/en/stable/reference/pip_install/#editable-installs


