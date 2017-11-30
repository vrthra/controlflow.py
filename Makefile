file=example.py
dots: method=main
dots: arg=%20abc
dots: coverage
	python3  pycfg.py $(file) -d -y ./example.bcoverage 2> out.dot

cfg:
	python3  pycfg.py $(file) -c

show:
	nl -ba $(file)

coverage: method=main
coverage: arg=%20abc
coverage:
	python3 ./branchcov.py $(file) $(method) '$(arg)' 2> example.bcoverage

oldcoverage:
	python3 -mcoverage run --branch example.py
	python3 -mcoverage report
	mv .coverage example.bcoverage

xml:
	python3 -mcoverage xml

example:
	cat example.py | nl -b a

clean:
	rm -rf *.*coverage __pycache__/ out.*

branch_distance: approach=32 33 34 35
branch_distance: method=main
branch_distance:
	python3 ./branchfitness.py example.py main 'abc'  33 34 35
	python3 ./branchfitness.py gcd.py main '15 12' 3 4 5
	python3 ./branchfitness.py triangle.py main '1 2 0' 4 5 6
	#python3 ./branchfitness.py $(file) $(method) 'abc' $(approach)

a=1
b=2
c=3
d=4
op=+
interp:
	python3 interp.py 'a $(op) b' '{"a":$(a), "b":$(b), "c":$(c), "d":$(d)}'

dinterp:
	python3 dexpr.py 'a $(op) b' '{"a":$(a), "b":$(b), "c":$(c), "d":$(d)}'
