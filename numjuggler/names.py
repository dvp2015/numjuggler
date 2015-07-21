"""
Names for card types, elements and element parameters.
"""

# Types of cards in MCNP input file. Data card types are described elsewhere.
_cTypes = {
    # no-information cards
    'comment': -1,
    'blankline': -2,
    # card types as they appear in input file
    'message': 1,
    'title': 2,
    'cell': 3,
    'surface': 4,
    'data': 5,
    # for internal use:
    '_': 'card type'}

# Names of element types and parameter keywords that are used in MCNP input file
_eTypes = {
    # element names. Those that can be renamed in MCNP input file without
    # chaning physical model.
    'cell': 1,
    'sur': 2,
    'mat': 3,
    'tr': 4,
    'tal': 5,
    'u': 6,
    'fill': 7,
    # parameter names. negative IDs , to distinguish from element names.
    'den': -1,
    'imp:n': -2,
    'imp:p': -3,
    'tmp': -4,
    'nlib': -5,
    'mt': -6,
    # for internal use:
    '_': 'element type'}


# Names of data card types.
_dcTypes = {
    # data card names. All data cards listed here are parsed.
    'm': 1,
    'mt': 2, 
    'mpn': 3, 
    'f': 4,
    'tr': 5, 
    # for internal use:
    '_': 'data card type'}



class _TypeName(object):
    def __init__(self, data):
        self.__data = data
        self.__emsg = 'Unknown {} or index: '.format(data.pop('_'))
        self.__dict__.update(data)

        # names and values of positive IDs:
        self.__names = []
        self.__vals = []
        for k, v in sorted(self.__data.items()):
            if v > 0:
                self.__names.append(k)
                self.__vals.append(v)
        return

    @property
    def names(self):
        return self.__names

    @property
    def values(self):
        return self.__vals

    def __call__(self, V, default=None):
        """
        Convert type name to its ID and back.

        If V is an integer, return name as a string.
        If V is a string, return its ID as an integer.
        """

        for k, v in self.__data.items():
            if V == v:
                return k
            elif str(V) == k[:len(str(V))]:
                return v
        if default is None:
            raise ValueError(self.__emsg, repr(V))
        else:
            return default


# Input file card type IDs:
cID = _TypeName(_cTypes)
# Input file element type IDs:
eID = _TypeName(_eTypes)
# Data card type IDs:
dID = _TypeName(_dcTypes)

# Allowable parameter names for different types of elements. Names consistent
# with _eTypes above.
_paramNames = {
    'cell': ('mat', 'den', 'imp:n', 'imp:p', 'fill', 'u', 'tr', 'tmp'),
    'sur': ('tr',),
    'mat': ('nlib', 'mt')
}


if __name__ == '__main__':
    print cID.message, cID('message'), cID(cID.message)
    print eID.cell, eID('cell'), eID(eID.cell)

