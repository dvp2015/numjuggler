# numjuggler
Tool to rename cells, surfaces, materials and universes in MCNP input files.

## Install

You must have Python 2.7 installed on your machine (Python 3 was not tested but
might work). Unzip the  most recent archive from `dist` folder and run

    > python setup.py install --user

from the folder containing file `setup.py`. This installs the package, that can
be used from the command line in the following way:

    > python -m numjuggler ...

where ... -- are command line options specifying the input file and the rules
how cells, surfaces, etc. are renamed.

Alternatively, you can use [pip](https://pip.pypa.io/en/stable/) -- a tool for installing Python packages
(for some Python distributions it is included, otherwise must be installed separately). Unzipping the
archive in this case is not needed, and installation is done with the command

    > pip install numjuggler-X.X.X.tar.gz --user

When the package is installed with pip, a script called `numjuggler` is added to
`~/.local/bin` (or to `C:\Python27\Scripts`), so that invocation of the tool is
more simple. In this case, both two commands are identical:

    > numjuggler ...
    > python -m numjuggler ...

where .. -- are command line options.

## Help

After installing the package, run the following command to get some help and
instructions:

    > python -m numjuggler -h

There is also a github repo, [numjuggler.docs](https://github.com/inr-kit/numjuggler.docs), related to numjuggler documentation.

## Recently added features

### Version 2.8a
Keyword ``--find`` is added. It helps to find cells with particular properties, for
example filled with particular material. this keyword must be followed by a string that
specifies the search criterion. Currently, it has the following syntax:

    --find " type: expr"

where ``type`` defines the type of elements to be searched (currently only ``cell``is implemented) and
``expr``  is a logical expression.  

#### Examples:

---------------------------

In input ``inp_`` find cells with material 10:

    numjuggler --find "cell: mat == 10" inp_

Double apostrophes are used to prevent shell evaluation. The expression after
``:`` must be a valid Python logical expression, where ``mat``, ``u`` or
``rho`` are replaced by cell's correspondent property and evaluated.

----------------------------

Find all non-void cells

    numjuggler --find "cell: mat > 0" inp_ 

-----------------------------

Find cells with density between 10 and 20 gcc:

    numjuggler --find "cell: -20 < rho < -10" inp_

Note that numjuggler is not aware about conversion between concentration and
density and checks simply the value as specified in the input file. Thus, this
example has sense only when densities in ``inp_`` are desined in gcc, and all
cells with density specified as concentration, even if cerrespondent density
lies within 10 and 20 gcc, will be skipped.

-------------------------------------

Find cells where surface 10 is used:

    numjuggler --find "cell: sur == 10" inp_





