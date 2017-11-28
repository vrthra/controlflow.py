dots: coverage
	@python3  pycfg.py example.py -d -y ./example.bcoverage > out.dot

#dot -Tpng out.dot -o out.png

cfg:
	python3  pycfg.py example.py -c

show:
	nl -ba example.py

coverage:
	@python3 ./branchcov.py ./example.py main > example.bcoverage

oldcoverage:
	python3 -mcoverage run --branch example.py
	python3 -mcoverage report
	mv .coverage example.bcoverage

xml:
	python3 -mcoverage xml

example:
	cat example.py | nl -b a

clean:
	rm -rf .coverage __pycache__/

I=9
I=5
branch_distance_old: approach=3 4 5 6
branch_distance_old:
	python3 ./branchfitness.py example.py main $(I) $(approach)

branch_distance: approach=32 33 34 35
branch_distance: file=example.py
branch_distance: method=main
branch_distance:
	python3 ./branchfitness.py $(file) $(method) $(approach)

a=1
b=2
c=3
d=4
op=+
interp:
	python3 interp.py 'a $(op) b' '{"a":$(a), "b":$(b), "c":$(c), "d":$(d)}'

dinterp:
	python3 dexpr.py 'a $(op) b' '{"a":$(a), "b":$(b), "c":$(c), "d":$(d)}'
