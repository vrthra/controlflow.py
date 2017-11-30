#!/usr/bin/env python3
import sys
def triangle(a, b, c):
    if a == b:
        if b == c:
            return 'Equilateral'
        else:
            return 'Isosceless'
    else:
        if b == c:
            return 'Isosceless'
        else:
            return 'Scalene'

def main(arg):
    v = arg.split(' ')
    print(triangle(int(v[0]), int(v[1]), int(v[2])))

if __name__ == '__main__':
    main(sys.argv[0])
