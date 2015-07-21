"""
Functions to renumber cells, surfaces, etc. in MCNP input file.
"""
import warnings
from . names import eID


class LikeFunction(object):
    """
    Class of callables that take two arguments, a number (integer) and a type (char or string):

        > f = LikeFunction(d)
        > n_new = f(n_old, 'c')

    This callable is used as a mapping for cell, surface, material, etc numbers in an MCNP input file.

    The d argument of the constructor is a dictionary of the following form:

        > d = {}
        > d['c'] = [dn0, rl]

    where dn0 is an integer or callable, and rl is a list of tuples
    representing ranges and correspondent mappings:

        > rl = [(n1, m1, dn1), (n1, m2, dn2), ...]

    where n1 and m1 -- are the first and the last elements in the range of
    numbers mapped with respect to dn1. THe dn1 can be an integer or a
    calalble.

    Mapping dn0 appiled to numbers outside of all ranges in rl. For all dni, if
    it is an integer, the respective mapping is n -> n + dni. If dni is
    callable, the mapping n -> dni(n) is applied.

    """
    def __init__(self, pdict, cdict, log=False, debug=None):
        self.__p = pdict   # renaming rules
        self.__c = cdict   # changing rules
        self.__lf = log    # flag to log or not.
        self.__ld = {}     # here log is written, if log.
        self.__db = debug  # File to write debug info.
        return

    def print_debug(self, comment):
        d = self.__db
        if d:
            print >> d, 'Mapping:', comment

    def rename(self, n, t):
        # if type t is not in renaming dictionary, do nothing:
        if t not in self.__p.keys():
            nnew = n
        else:
            (dln, dinc), lst = self.__p[t]
            tname = eID(t)
            self.print_debug('Apply mapping to  {} {}'.format(tname, repr(n)))
            for ln, rng, inc in lst:
                try:
                    in_range = rng[0] <= n <= rng[1] 
                except:
                    in_range = n == rng
                if in_range:
                    nnew = n + inc
                    self.print_debug(' {} {} in range {} -> {}'.format(tname, n, rng, nnew))
                    break
                self.print_debug(' {} {} not in range {}'.format(tname, n, rng))
            else:
                # apply the rest range rule
                nnew = n + dinc
                self.print_debug(' {} {} in rest range -> {}'.format(tname, n, nnew))

        # remember pair (t, nnew) if log is necessary.
        if self.__lf:
            ld = self.__ld
            if not ld.has_key(t):
                ld[t] = {}
            d = ld[t]
            if d.has_key(nnew):
                if d[nnew] != n:
                    warnings.warn('Non-injective mapping: {} {} and {} are both mapped to {}'.format(eID(t), d[nnew], n, nnew))
            else:
                d[nnew] = n


        # check that void material not changed:
        if t == eID.mat:
            if n == 0 and nnew != 0:
                print 'WARNING: material {} replaced with {}. Add cell density to the resulting input file.'.format(n, nnew)
            if n != 0 and nnew == 0:
                print 'WARNING: material {} replaced with {}. Remove cell density from the resulting input file.'.format(n, nnew)
        return nnew

    def change(self, card):
        """
        Change parameters of card, according to cdict.
        """
        # find changing rule
        if card.original_name is None or card.etype not in self.__c.keys():
            # nothing to change
            pass
            self.print_debug(' No change for {}'.format(card.etype, card.original_name))
        else:
            (dnl, drule), lst = self.__c[card.etype]
            card.print_debug('Before change', 'v')
            for ln, rng, rule in lst + [(dnl, card.original_name, drule)]:
                self.print_debug(' Change check {} {} {}'.format(ln, rng, rule))
                try:
                    in_range = rng[0] <= card.original_name <= rng[1]
                except:
                    in_range = rng == card.original_name
                if in_range:
                    newvals = []
                    for v, t in card.values:
                        newv = rule.pop(t, None)
                        self.print_debug('{} {} {} -> {}'.format(eID(t), rule, v, newv))
                        if newv is not None:
                            newvals.append((newv, t))
                            self.print_debug(' Change {} {} -> {}'.format(eID(t), v, newv))
                        else:
                            newvals.append((v, t))
                    card.values = newvals
                    break
            card.print_debug('After change', 'v')





    def write_log_as_map(self, fname):
        """
        Writes log to fname in format of map file.
        """
        d = {}
        for t in 'csmu':
            d[t] = {}
        for (t, nnew), n in self.__ld.items():
            d[t[0]][n] = nnew

        with open(fname, 'w') as f:
            for t, d in self.__ld.items():
                print >> f, '-' * 80
                for nnew in sorted(d.keys()):
                    n = d[nnew]
                    if n != nnew:
                        print >> f, '   {} {:>6d}: {:>6d}'.format(eID(t), nnew, n)
                 

def get_numbers(scards):
    """
    Return dictionary with keys -- number types and values -- list of numbers used in the input file.
    """
    r = {}
    for c in scards:
        for v, t in c.values:
            if not r.has_key(t):
                r[t] = []
            r[t].append(v)
    return r


def get_indices(scards):
    """
    Return a dictionary that can be used as an argument for the LikeFunction
    class.

    This dictionary describes mapping that maps cell, surface, material and
    universe numbers to their indices -- as they appear in the MCNP input file
    orig.
    """
    # get list of numbers as they appear in input
    d = get_numbers(scards)

    res = {} # resulting dictionaries of the form number: index
    for t, vl in d.items():
        di = {}
        cin = 1 # all indices start from 1
        for v in vl:
            if not v in di.keys():
                if v != 0:           # v == 0 excluded to skip renumbering of u=0 and m=0
                    di[v] = cin
                    cin += 1
                else:
                    di[v] = 0
        res[t] = di
    return res


def _get_ranges_from_set(nn):
    """
    Yields ranges that cover all elements in nn.

    nn is a set of integers. Yielded range can be of length 1 or more.

    For example, for nn = {1, 3, 4, 5, 7}, the following ranges will be
    yielded:

        (1, 1)    # single-element range, since there is no element 2 in nn
        (3, 5)    # this range covers elements 3, 4 and 5 in nn
        (7, 7)    # another single-element range.
    """
    nnl = sorted(nn)
    if nnl:                         # nnl can be empty
        if filter(lambda e: not isinstance(e, int), nn):
            # for float elements of nn only one range, (min, max), is returned
            yield (nnl[0], nnl[-1])
        else:
            n1 = nnl.pop(0) # start of 1-st range
            np = n1         # previous item
            while nnl:
                n = nnl.pop(0)
                if np in [n-1, n]:
                    # range is continued
                    np = n
                else:
                    yield (n1, np)
                    n1 = n
                    np = n
            yield (n1, np)

def read_map_file(fname):
    """
    Read map file and return functions to be used for mapping.

    Map file format:

        c100--140: +20    # add 20 to all cell numbers from 100 to 140
        c150: 151         # replace cell 150 with 151
        c200--300: 400    # add 200 to all cell numbers in the range from 200 to 300 (400 without prefix sign means where the new range starts.
        c: 50            # default cell offset. If not specified, it is 0.
    """
    # dictionary with renaming rules. It can have only a subset of names from eID
    drename = {}
    for k in eID.values:
        drename[k] = [('-', 0), []]

    # dictionary with changing rules
    dchange = {}
    for k in eID.values:
        dchange[k] = [('-', {}), []]

    # map file line number, for debug info
    ln = 0 
    with open(fname, 'r') as f:
        for l in f:
            ln += 1
            ll = l.lower().lstrip()
            t, rng, rule = _read_map_line(ll)
            if t == 0:
                # t = 0 means that line ll is a commnet. Skip it.
                continue

            # analyse rng and rule and add to rename or change dictionaries.
            # Renaming rule can be applied to explicit range or to default one.
            # Changing rule cannot be applied to default range, only explicit
            # range can be followed by a changing rule.
            #
            # rng is None -- this means default rule
            # rule is a dictionary. If only one key and in '+-', this is a
            # rename rule.  (rule[0]=''also meets this condition). Note that rule is a non-empty dictionary, it is checked in _read_map_line()
            k0, v0 = rule.items()[0]
            if k0 in '+-':
                # this is a rename rule
                if rng is None or k0 == '+':
                    inc = v0
                else:
                    n1 = rng if isinstance(rng, int) else rng[0]
                    inc = v0 - n1
                if rng is None:
                    drename[t][0] = (ln, inc)
                else:
                    drename[t][1].append((ln, rng, inc))
            else:
                # this is a changing rule
                if rng is None:
                    dchange[t][0] = (ln, rule)
                else:
                    dchange[t][1].append((ln, rng, rule))
    return drename, dchange

def _read_map_line(ll):
    """
    Read one line of the map file.

    THis function contains algorithm to parse map file lines, the read_map_file()
    functin is just wrapper.
    """

    # meaningful line is a line that starts one or more characters that
    # are starting characters of one of the keys in names._eTypes,
    # and that has ``:`` inside.

    l = ll.lower().lstrip()  # map file is case-insensitive.
    if ':' not in l:
        return 0, None, None  # 0 at the 1-st place means that ll is a commnet.

    lp, rp = l.split(':', 1)  # only 1-st : has sense
    # extract from left part element type and range, if any
    lpt = lp.split()
    et = eID(lpt.pop(0), 0)
    if et == 0:
        # first token on left part does not correspond to any known element
        # type
        return et, None, None 
    # find range
    rng = _read_range(' '.join(lpt))

    # right part rp has only one integer entry, or pairs of (name, val).
    rpl = rp.replace('=', ' ').split()
    try:
        i = int(rpl[0])
        # if no errors, right part represents renaming rule.
        rule = _read_rename_rule(rpl[0])
    except ValueError:
        # assume this is a change rule
        rule = _read_change_rule(rpl)
    # Analysis of rng and rule is made in the parent routine, which has access
    # to the rule-defining dictionaries from all lines.

    # rule can be empty, treat as a comment.
    if rule:
        return et, rng, rule
    else:
        return 0, None, None

def _read_range(s):
    """
    Read range from the line part s

    Returns:
        None,
        (n1, n2),
        n1
    """
    if s.strip() == '':
        # no entries
        return None 
    elif '--' in s:
        # two entries are given:
        return map(int, s.split('--'))
    else:
        # assume that only one integer is given
        return int(s)

def _read_rename_rule(s):
    """
    s is a string representing a signed integer.
    """
    if s[0] in '+-':
        sign = s[0]
    else:
        sign = ''
    val = int(s)
    return {sign: val} 

def _read_change_rule(tl):
    """
    tl is a list of tokens that represent pairs (param, value).
    """
    res = {} 
    while tl:
        t = tl.pop(0)
        pt = eID(t, 0)
        if pt != 0:
            # this is a valid parameter name
            try:
                v = tl.pop(0)
                res[pt] = v
            except IndexError:
                # there are no more tokens in tl. Consider the last one as a
                # comment.
                break
        else:
            # token is not a valid parameter name. Consider as a comment.
            break
    return res










if __name__ == '__main__':
    pass
