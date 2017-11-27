dots:
	@python3  pycfg.py example.py -d

cfg:
	python3  pycfg.py example.py -c

show:
	nl -ba example.py

coverage:
	python3 -mcoverage run --branch example.py
	python3 -mcoverage report
	mv .coverage example.coverage

xml:
	python3 -mcoverage xml

example:
	cat example.py | nl -b a

clean:
	rm -rf .coverage __pycache__/

I=9
I=5
approach=3 4 5 6
branch_distance:
	python3 ./computedistance.py $(I) $(approach)

branch_distance2:
	python3 ./computedistance.py 32 33 34 35

a=1
b=2
c=3
d=4
op=+
interp:
	python3 interp.py 'a $(op) b' '{"a":$(a), "b":$(b), "c":$(c), "d":$(d)}'

dinterp:
	python3 dexpr.py 'a $(op) b' '{"a":$(a), "b":$(b), "c":$(c), "d":$(d)}'
