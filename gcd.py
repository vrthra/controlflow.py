#!/usr/bin/env python3
import sys
def gcd(a, b):
    if a<b:
        c = a
        a = b
        b = c

    while b != 0 :
        c = a
        a = b
        b = c % b
    return a

def main(arg):
    v = arg.split(' ')
    print(gcd(int(v[0]), int(v[1])))

if __name__ == '__main__':
    main(sys.argv[0])
