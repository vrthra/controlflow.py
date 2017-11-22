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
	rm -rf .coverage

I=1
branch_distance:
	python3 ./computedistance.py $(I)
