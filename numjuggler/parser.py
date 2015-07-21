"""
Functions for parsing MCNP input files.
"""
import re
import warnings

from . names import cID, eID, dID, _paramNames

# regular expressions
re_int = re.compile('\D{0,1}\d+')  # integer with one prefix character
re_ind = re.compile('\[.+\]')      # inside [] for tally in lattices
re_rpt = re.compile('\d+[rRiI]')   # repitition syntax of MCNP input file
re_prm = re.compile('[it]mp:*[npe]*[=\s]+\S+')  # imp or tmp params of a cell
re_cmt = re.compile('(^\s{0,5}[cC](\s+.*|\s*)$)')  # pattern for commented line.
re_end = re.compile('\s[$&]|\n')  # pattern for line delimiter character
re_f_card = re.compile('^\s*[fF]\d')       # tally data card
re_fc_card = re.compile('^\s*[fF][cC]\d')  # tally comment card
re_fmt = re.compile('{.*?}')  # Placeholder in format string


def fmt_d(s):
    return '{{:<{}d}}'.format(len(s))


def fmt_g(s):
    return '{{:<{}g}}'.format(len(s))


def fmt_s(s):
    return '{}'
    # return '{{:<{}s}}'.format(len(s))


class Card(object):
    """
    Representation of a card.
    """
    def __init__(self, lines, ctype, pos, debug=None):

        # Original lines, as read from the input file
        self.lines = lines

        # card type by its position in the input. See cID imported from names.
        self.ctype = ctype
        self.ctypeName = cID(ctype)

        # Element type that card describes (cell, surface, material, tr, tally, etc.)
        # See _get_etype() method.
        self.etype = None

        # data card type. Defined from the get_values() method.
        # has sence only to data cards (see ctype). For other card types
        # is None.
        self.dtype = None

        # Input file line number, where the card was found.
        self.pos = pos

        # File-like object to write debug info (if not None)
        self.debug = debug

        # template string. Represents the general structure of the card. It is
        # a copy of lines, but meaningful parts are replaced by format
        # specifiers, {}
        self.template = ''

        # List of strings represenging meaningful parts of the card. The
        # original multi-line string card is obtained as
        # template.format(*input)
        self.input = []

        # Dictionary of parts that are removed from input before processing it.
        # For example, repitition syntax (e.g. 5r or 7i) is replaced with '!'
        # to prevent its modification.
        self.hidden = {}

        # List of (v, t) tuples, where v -- value and t -- its type.
        self.values = []

        # Original name
        self.original_name = None

        # Split card to template and meaningful part is always needed. Other
        # operations are optional.
        self.get_input()

        return

    def print_debug(self, comment, key='tihv'):
        d = self.debug
        if d:
            print >> d, 'Line {}, {} card. {}'.format(self.pos,
                                                      self.ctypeName,
                                                      comment)
            if 't' in key:
                print >> d, '    template:', repr(self.template)
            if 'i' in key:
                print >> d, '    input:   ', self.input
            if 'h' in key:
                print >> d, '    hidden:  ', self.hidden
            if 'v' in key:
                print >> d, '    values:  ', map(lambda e: (e[0], eID(e[1])), self.values)

    def get_input(self):
        """
        Recompute template, input and hidden attributes from lines
        """

        mline = ''.join(self.lines)

        if self.ctype in (cID.comment, cID.blankline):
            # nothing to do for comments or blanklines:
            self.input = ''
            self.template = mline

        else:
            # TODO: protect { and } in comment parts of the card.
            tmpl = []  # part of template
            inpt = []  # input, meaningful parts of the card.
            if re_fc_card.search(mline):
                # this is tally comment, fc card. It always in one line and is
                # not delimited by & or $
                i = mline[:80]
                t = mline.replace(i, '{}', 1)
                inpt = [i]
                tmpl = [t]
            else:
                for l in self.lines:
                    if is_commented(l):
                        tmpl.append(l)
                    else:
                        # Check if there is comment after $ or &:
                        d = re_end.search(l).start()
                        i = l[:d]
                        t = l[d:]
                        inpt.append(i)
                        tmpl.append(fmt_s(i) + t)
            self.input = inpt
            self.template = ''.join(tmpl)
        self.print_debug('get_input', 'ti')
        return

    def _protect_nums(self):
        """
        In the meaningful part of the card replace numbers that do not represent
        cell, surface or a cell parameter with some unused char.
        """

        inpt = '\n'.join(self.input)

        d = {}

        # in cell card:
        if self.ctype == cID.cell and 'like' not in inpt:
            d['~'] = []  # float values in cells

        # replace repitition syntax in junks:
        sbl = re_rpt.findall(inpt)
        if sbl:
            for s in sbl:
                inpt = inpt.replace(s, '!', 1)
            d['!'] = sbl

        if self.ctype == cID.data and re_f_card.search(inpt):
            # this is tally card. Hide indexes in square brackets
            sbl = re_ind.findall(inpt)
            if sbl:
                for s in sbl:
                    inpt = inpt.replace(s, '|', 1)
                d['|'] = sbl

        self.input = inpt.split('\n')
        self.hidden = d

        self.print_debug('_protect_nums', 'ih')
        return

    def get_values(self):
        """
        Replace integers in the meaningfull part with format specifiers, and
        populate the `values` attribute.
        """
        self._protect_nums()
        if self.ctype == cID.cell:
            inpt, vt = _split_cell(self.input)
            self.original_name = vt[0][0]
        elif self.ctype == cID.surface:
            inpt, vt = _split_surface(self.input)
            self.original_name = vt[0][0]
        elif self.ctype == cID.data:
            inpt, vt, dtype = _split_data(self.input)
            self.dtype = dtype
        else:
            inpt = self.input
            vt = []
        self.input = inpt
        self.values = vt
        self._get_etype()
        self._get_params()
        self.print_debug('get_values', 'iv')
        return

    def _get_etype(self):
        # assumes that self.values is populated, i.e. call self.get_values() before this method.
        if self.ctype == cID.cell:
            self.etype = eID.cell
        elif self.ctype == cID.surface:
            self.etype = eID.sur
        elif self.ctype == cID.data:
            if self.dtype == dID.m:
                self.etype = eID.mat
            elif self.dtype == dID.f:
                self.etype = eID.tal
            elif self.dtype == dID.tr:
                self.etype = eID.tr
        self.print_debug('_get_etype: {} {}'.format(self.etype, eID(self.etype, 0)), '')
        return

    def _get_params(self):
        """
        Look over self.values and set attributes according to specified parameters.
        """
        self.params = {}
        self.print_debug('_get_params', 'v')
        if self.etype != None:
            for pname in _paramNames.get(eID(self.etype, 0), ()):
                self.print_debug('_get_params pname: {}'.format(pname), 'v')
                for v, t in self.values:
                    if eID(pname) == t:
                        self.params[pname] = v


    def card(self, wrap=False):
        """
        Return multi-line string representing the card.
        """

        # if self.input is empty, template represents the whole card
        if not self.input:
            return self.template

        # put values back to meaningful parts:
        inpt = '\n'.join(self.input)
        inpt = inpt.format(*map(lambda t: t[0], self.values))

        # put back hidden parts:
        for k, vl in self.hidden.items():
            for v in vl:
                inpt = inpt.replace(k, v, 1)
        inpt = inpt.split('\n')

        # TODO: maybe put this code into separate method.
        if wrap:
            tparts = re_fmt.split(self.template)[1:]
            newt = ['']  # new template parts
            newi = []    # new input parts
            self.print_debug('card wrap=True', '')
            for i, t in zip(inpt, tparts):
                self.print_debug('    ' + repr(i) + repr(t), '')
                il = []
                tl = [t]

                while len(i.rstrip()) > 79:
                    # first try to shift to left
                    if i[:5] == ' '*5:
                        i = ' '*5 + i.lstrip()
                    if len(i.rstrip()) > 79:
                        # input i must be wrapped. Find proper place:
                        for dc in ' :':
                            k = i.rstrip().rfind(dc, 0, 75)
                            if k > 6:
                                il.append(i[:k])
                                tl.append('\n')
                                i = '     ' + i[k:]
                                self.print_debug('card wrap=True' + repr(il[-1]) + repr(i), '')
                                break
                        else:
                            # there is no proper place to wrap.
                            self.print_debug('card wrap=True cannot wrap line ' + repr(i), '')
                            # raise ValueError('Cannot wrap card on line', self.pos)
                            warnings.warn('Cannot wrap card on line {}'.format(self.pos))
                            break
                    else:
                        # input i fits to one line. Do nothing.
                        pass

                newt += tl
                newi += il + [i]
            tmpl = '{}'.join(newt)
            inpt = newi
        else:
            tmpl = self.template

        card = tmpl.format(*inpt)
        return card

    def remove_spaces(self):
        """
        Remove extra spaces from meaningful parts.
        """
        self.print_debug('before remove_spaces', 'i')
        if self.ctype in (cID.cell, cID.surface, cID.data):
            inpt = []
            for i in self.input:
                indented = i[:5] == ' '*5
                # leave only one sep. space
                i = ' '.join(i.split())
                i = i.strip()
                # spaces before/after some characters are not needed:
                for c in '):':
                    i = i.replace(' ' + c, c)
                for c in '(:':
                    i = i.replace(c + ' ', c)
                if indented:
                    i = ' '*5 + i
                inpt.append(i)
                self.print_debug(i, '')
            self.input = inpt
            self.print_debug('after remove_spaces', 'i')
        return

    def apply_renumbering(self, f):
        """
        Replace Ni in self.values by Mi = f(Ni, Ti).
        """
        self.print_debug('before apply_renumbering', 'v')

        # Apply renumbering 
        # u and fill should be renumberd in the same way, but types
        # must remain different, since u and fill are two different
        # properties of a cell.
        # self.values = map(lambda t: (f(t[0], t[1]), t[1]), self.values)
        newvals = []
        for t in self.values:
            if t[1] == eID.fill:
                t1 = eID.u
            else:
                t1 = t[1]
            newvals.append((f(t[0], t1), t[1]))
        self.values = newvals
        self.print_debug('after apply_renumbering', 'v')
        return



def _split_cell(input_):
    """
    Replace integers in the meaningful parts of a cell card with format specifiers,
    and return a list of replaced values together with their types.

    """

    # meaningful parts together. Originally, they cannot have \n chars, since
    # all of them should land to the card template, therefore, after all
    # entries are replaced with format specifiers, it can be split back to a
    # list easily at \n positions.
    inpt = '\n'.join(input_)

    vals = [] # list of values
    fmts = [] # value format. It contains digits, thus will be inserted into inpt later.
    tp = '_'  # temporary placeholder for format specifiers
    if 'like ' in inpt.lower():
        # raise NotImplementedError()
        warnings.warn('Parser for "like but" card, found on line {}, is not implemented'.format(self.pos))
    else:
        # cell card has usual format.
        t = inpt.split()

        # Get cell name
        js = t.pop(0)
        inpt = inpt.replace(js, tp, 1)
        vals.append((int(js), eID.cell))
        fmts.append(fmt_d(js))

        # get material
        ms = t.pop(0)
        inpt = inpt.replace(ms, tp, 1)
        vals.append((int(ms), eID.mat))
        fmts.append(fmt_d(ms))

        # get density, if any
        if vals[-1][0] != 0:
            ds = t.pop(0)
            inpt = inpt.replace(ds, tp, 1)
            vals.append((ds, eID.den))
            fmts.append(fmt_s(ds))

        # Get geometry and parameters blocks. I assume that geom and param
        # blocks are separated by at least one space, so there will be an
        # element in t starting with alpha char -- This will be the first token
        # from the param block.
        geom = []
        parm = []
        while t:
            e = t.pop(0)
            if e[0].isalpha():
                parm = [e] + t
                break
            else:
                geom.append(e)

        # replace integer entries in geom block:
        for s in re_int.findall(' '.join(geom)):
            # s is a surface or a cell (later only if prefixed by #)
            t = 'cell' if s[0] == '#' else 'sur'
            s = s if s[0].isdigit() else s[1:]
            f = fmt_d(s)
            inpt = inpt.replace(s, tp, 1)
            vals.append((int(s), eID(t)))
            fmts.append(f)

        # replace values in parameters block. Values are prefixed with = or
        # space(s).
        ### Note that tmp and imp values must be hidden
        t = ' '.join(parm).replace('=', ' ').split()  # get rid of =.
        while t:
            s = t.pop(0)
            parsed = False
            vt = None    # to check if parsed or not.
            if 'fill' in s.lower():
                # universe number follows the fill keyword.
                # TODO: Optionally, it can be followed by an array of universes
                vt = 'fill'     # value type. Distinguish from u!
                vs = t.pop(0)   # string representation of value
                if 'lat' in ''.join(parm).lower():
                    print 'WARNING: FILL keyword followed by an array cannot be parsed'
                    print '         Check cell cards with FILL and LAT keywords'

            else:
                # assume that parameter values are always in pairs (name,
                # value), thus the s token must be a parameter name,
                # i.e. start with alpha char.
                vt = s
                vs = t.pop(0)    # param value

            # some paramter values are integers, so convert them:
            if vt in ('fill', 'u'):
                vv = int(vs)
                vf = fmt_d(vs)
            else:
                vv = vs
                vf = fmt_s(vs)  # format for value string repr.

            if vt is not None:
                inpt = inpt.replace(vs, tp, 1)
                vals.append((vv, eID(vt))) 
                fmts.append(vf)


        # replace tp  with actual fmts, in order:
        for f in fmts:
            inpt = inpt.replace(tp, f, 1)

        return inpt.split('\n'), vals


def _split_surface(input_):
    """
    Similar to _split_cell(), but for surface cards.
    """
    inpt = '\n'.join(input_)
    t = inpt.split()

    vals = [] # like in split_cell()
    fmts = []
    tp = '_'

    # get surface name:
    js = t.pop(0)
    if not js[0].isdigit():
        js = js[1:]
    inpt = inpt.replace(js, tp, 1)
    vals.append((int(js), eID.sur))
    fmts.append(fmt_d(js))

    # get TR or periodic surface:
    ns = t.pop(0)
    if ns[0].isdigit():
        # TR is given
        inpt = inpt.replace(ns, tp, 1)
        vals.append((int(ns), eID.tr))
        fmts.append(fmt_d(ns))
    elif ns[0] == '-':
        # periodic surface
        ns = ns[1:]
        inpt = inpt.replace(ns, tp, 1)
        vals.append((int(ns), eID.sur))
        fmts.append(fmt_d(ns))
    elif ns[0].isalpha():
        # ns is the surface type
        pass
    else:
        raise ValueError(input_, inpt, ns)

    for f in fmts:
        inpt = inpt.replace(tp, f, 1)

    return inpt.split('\n'), vals

def _get_int(s):
    r = ''
    for c in s:
        if r and c.isalpha():
            break
        elif c.isdigit():
            r += c
    return r

def _split_data(input_):
    inpt = '\n'.join(input_)
    t = inpt.split()

    vals = []
    fmts = []
    tp = '_'

    if 'tr' in t[0][:3].lower():
        # TRn card
        dtype = dID.tr
        ns = _get_int(t[0])
        inpt = inpt.replace(ns, tp, 1)
        vals.append((int(ns), eID.tr))
        fmts.append(fmt_d(ns))
    elif t[0][0].lower() == 'm' and 'mode' not in t[0].lower():
        # Mn, MTn or MPNn card
        ms = _get_int(t[0])
        inpt = inpt.replace(ms, tp, 1)
        vals.append((int(ms), eID.mat))
        fmts.append(fmt_d(ms))
        # additional tests to define data card type:
        if t[0][1].isdigit():
            dtype = dID.m
        elif t[0][1].lower() == 't':
            dtype = dID.mt
        elif t[0][1].lower() == 'p':
            dtype = dID.mpn
    elif t[0][0].lower() == 'f' and t[0][1].isdigit():
        # FN card
        dtype = dID.f
        ns = _get_int(t[0]) # tally number
        inpt = inpt.replace(ns, tp, 1)
        vals.append((int(ns), eID.tal))
        fmts.append(fmt_d(ns))

        # define type of integers by tally type:
        nv = int(ns[-1])
        if nv in [1, 2]:
            typ = eID.sur
        elif nv in [4, 6, 7, 8]:
            typ = eID.cell
        else:
            typ = 0

        if typ != 0:
            # Lattice indices, surrounded by square brakets must allready be hidden

            # Special treatment, if tally has 'u=' syntax.
            hasu = 'u' in inpt.lower() and '=' in inpt.lower()
            # find all integers -- they are cells or surfaces
            for s in re_int.findall(inpt):
                ss = s[1:]
                tpe = typ
                if hasu:
                    # ss can be universe. To distinguish this, one needs to look
                    # back in previous cheracters in c.
                    i1 = inpt.rfind(tp)
                    i2 = inpt.find(ss)
                    part = inpt[i1:i2]
                    while ' ' in part:
                        part = part.replace(' ', '')
                    if part[-2:].lower() == 'u=':
                        tpe = eID.u
                inpt = inpt.replace(ss, tp, 1)
                vals.append((int(ss), tpe))
                fmts.append(fmt_d(ss))
    else:
        dtype = 0

    for f in fmts:
        inpt = inpt.replace(tp, f, 1)

    return inpt.split('\n'), vals, dtype



def is_commented(l):
    """
    Return True if l is a commented line.
    """
    # res = False
    # # remove newline chars at the end of l:
    # l = l.splitlines()[0]
    # if 'c ' in l[0:6].lstrip().lower():
    #     res = True
    #     #print 'is_com "c "',
    # elif 'c' == l.lower():
    #     res = True
    #     #print 'is_com "c"',
    # #print 'is_com', res
    # return res

    return bool(re_cmt.findall(l))


def is_fc_card(l):
    """
    Return true, if line l is tally comment cards, fcN
    """
    return l.lstrip().lower()[:2] == 'fc'

def is_blankline(l):
    """
    Return True, if l is the delimiter blank line.
    """
    return l.strip() == ''


def _check_bad_chars(f):
    lbc = '\t' # list of bad characters
    f.seek(0)
    cln = 0 # line number
    for l in f:
        cln += 1
        for bc in lbc:
            if bc in l:
                print 'Warning: bad character {} on line {}'.format(repr(bc), cln)
    f.seek(0)
    return


def get_cards(inp, debug=None):
    """
    Iterable, return (str, Itype), where str is a list of lines representing a
    card, and Itype is the type of the card (i.e. message, cell, surface or  data)

    inp -- is the filename.
    """

    def _yield(card, ct, ln):
        return Card(card, ct, ln, debug)

    cln = 0 # current line number. Used only for debug
    with open(inp, 'r') as f:
        # check for bad characters
        _check_bad_chars(f)

        # define the first block:
        # -----------------------

        # Next block ID
        ncid = 0 # 0 is not used in card ID dictionary CID.

        # Parse the 1-st line. It can be message, cell or data block.
        l = f.next()
        cln += 1
        kw = l.lower().split()[0]
        if 'message:' == kw:
            # read message block right here
            res = [l]
            while not is_blankline(l):
                l = f.next()
                cln += 1
                res.append(l)
            yield _yield(res, cID.message, cln-1)  # message card
            yield _yield(l, cID.blankline, cln)      # blank line
            l = f.next()
            cln += 1
            ncid = cID.title
        elif 'continue' == kw:
            # input file for continue job. Contains only data block.
            ncid = cID.data
        else:
            ncid = cID.title
        if ncid == cID.title:
            # l contains the title card
            yield _yield([l], ncid, cln)
            ncid += 1

        # read all other lines
        # --------------------

        # Line can be a continuation line in the following cases:
        #   * all lines in the message block, i.e. before the blank line delimiter
        #   * if line starts with 5 or more spaces,
        #   * if previous line ends with & sign.
        # Thus, the role of the current line (continuation or not) can be
        # defined by the line itself (5 spaces), or by previous lines (message
        # block or & sign). This can lead to inconsistency, when previous line
        # is delimited by &, but is followed by the blank line delimiter.  in
        # this case (rather theretical), blank line delimiter (as appeared more
        # lately) delimites the card from the previous line.
        cf = False  # continuation line flag. Set to true only when prev. line contains &.

        # Comment lines (CL) can be between cards or inside them. CL between two cards are yielded as block of comments
        # (although usually, CL are used to describe cards that follow them).
        # CL inside a card will belong to the card.

        card = []  # card is a list of lines.
        cmnt = []  # list of comment lines.
        for l in f:
            cln += 1
            if is_blankline(l):
                # blank line delimiter. Stops card even if previous line contains &
                if card:
                    # card can be empty, for example, when several empty lines are at the end of file
                    yield _yield(card, ncid, cln - len(card) - len(cmnt))
                if cmnt:
                    yield _yield(cmnt, cID.comment, cln - len(cmnt))
                    cmnt = []
                yield _yield(l, cID.blankline, cln)
                ncid += 1
                card = []
            elif l[0:5] == '     ' or cf:
                # l is continuation line.
                if cmnt:
                    card += cmnt # previous comment lines, if any, belong to the current card.
                    cmnt = []
                card.append(l)
                cf = l.find('&', 0, 81) > -1
            elif is_commented(l):
                # l is a line comment. Where it belongs (to the current card or to the next one),
                # depends on the next line, therefore, just store temorarily.
                cmnt.append(l)
            else:
                # l is the 1-st line of a card. Return previous card and comments
                if card:
                    yield _yield(card, ncid, cln - len(card) - len(cmnt))
                if cmnt:
                    yield _yield(cmnt, cID.comment, cln - len(cmnt))
                    cmnt = []
                card = [l]

                cf = not is_fc_card(l) and l.find('&', 0, 81) > -1 # if tally comment card, i.e. started with fc, the & character does not mean continuation.
        if card:
            yield _yield(card, ncid, cln - len(card) - len(cmnt))
        if cmnt:
            yield _yield(cmnt, cID.comment, cln - len(cmnt))




if __name__ == '__main__':
    pass
