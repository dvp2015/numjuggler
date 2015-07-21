"""
Auxiliary classes.
"""

class MultiRange(list):
    """
    List of ranges.

    Each range is represented by a tuple of integers (n1, n2).
    """

    def __contains__(self, n):
        try:
            for t in self:
                if t[0] <= n <= t[1]:
                    return True
        except:
            raise ValueError('Wrong element in the list of ranges; ', t)
        return False


if __name__ == '__main__':
    lr = MultiRange()
    lr.append((1, 3))
    lr.append((5, 5))
    lr.append((7, 12))

    print lr
    for v in range(15):
        if v in lr:
            print '{} in lr'.format(v)
        else:
            print '{} not in lr'.format(v)
