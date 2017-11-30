file=example.py
dots: method=main
dots: arg=%20abc
dots: coverage
dots:
	python3  pycfg.py $(file) -d -y ./example.cov 2> out.dot

cfg:
	python3  pycfg.py $(file) -c

show:; nl -ba $(file)

coverage: method=main
coverage: arg=%20abc
coverage:
	python3 ./branchcov.py $(file) $(method) '$(arg)' 2> example.cov

clean:
	rm -rf *.*coverage __pycache__/ out.*

branch_distance: approach=32 33 34 35
branch_distance: method=main
branch_distance: arg='abc'
branch_distance:
	python3 ./branchfitness.py $(file) $(method) '$(arg)' $(approach)

cgi.branch_distance:; $(MAKE) branch_distance file=cgidecode.py  method=main arg='abc'  approach='33 34 35'
tri.branch_distance:; $(MAKE) branch_distance file=triangle.py method=main arg='1 2 0'  approach='4 5 6'
gcd.branch_distance:; $(MAKE) branch_distance file=gcd.py method=main arg='15 12'  approach='3 4 5'

cgi.dots: arg='%20abc'
cgi.dots:; $(MAKE) dots file=cgidecode.py arg='$(arg)'

tri.dots: arg='1 2 0'
tri.dots:; $(MAKE) dots file=triangle.py arg='$(arg)'

gcd.dots: arg='15 12'
gcd.dots:; $(MAKE) dots file=gcd.py arg='$(arg)'

a=1
b=2
c=3
d=4
op=+
interp:
	python3 interp.py 'a $(op) b' '{"a":$(a), "b":$(b), "c":$(c), "d":$(d)}'

dinterp:
	python3 dexpr.py 'a $(op) b' '{"a":$(a), "b":$(b), "c":$(c), "d":$(d)}'
