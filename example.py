#!/usr/bin/env python3
def gcd(a, b):
    pass
    if a < b:
        c = a
        a = b
        b = c

    while b != 0:
        c = a
        a = b
        b = c % b
    return a

if __name__ == '__main__':
    gcd(15, 12)
