# Types of elements in MCNP input file

Different meaning can have e.g. term 'cell' in MCNP input file. For this
reason, this file describes possible types of elements and their names to be
used in numjuggler.

'Cell' and its number can denote a cell name (that can appear in a cell card,
in a tally card, in a source card), or a cell card with this particular name,
that can appear in the MCNP input file only once in the cell cards block.
Similar, a 'surface' with particular number can refer to a surface number that
can appear in several places in the input file or it can refer to particular
surface that is described in the surface block of the input file only once.

This difference can be seen clearly when we consider two examples: in one we
want to rename cell 10 to 15, in the other example, we want to change material
of cell 10 to a new value. In the first example, we need to go through the
whole MCNP input file, find all references to cell 10 and replace them with 15.
Semantics of the whole input file does not change: changing a cell name does
not change the physical model this file describes. 

In the second example, we need to find only one place, particularly, the cell
card that describes cell 10. And change its second entry (material numder) to a
new material. In this case semantics of the input file changes: the physical
model is changed.

Set of elements in the input file that can be renamed without changing the
physical model:

- ``cell``

- ``surface``

- ``material``

- ``transformation``

- ``tally`` (tally names cannot be renamed arbitrarily: the last digit must be
  preserved)

- Distribution numbers

All these numbers can appear in the input file in several places.

Set of parameters that can be changed for particular element, depends on the
type of element.

- For a cell we can change the following parameters:

    + ``mat``

    + ``rho``

    + ``imp:n``, ``imp:p``, etc.

    + ``fill``

    + ``u``

    + ``tr`` (the transformation can appear only in ``LIKE BUT`` construction)

- For a surface we can change the following parameters independently on the
  surface type:

    + ``+*`` that defines surface reflection

    + ``tr`` transformation applied to surface

  All other parameters are surface-type dependent.

- For a material we can change:

    + ``nlib``

    + corresponding ``mt`` card.  Although the use of thermal data is specified
      in a separate data card, this is still a property of material.


