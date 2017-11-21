dots:
	@python3  pycfg.py example.py -d

json:
	@python3  pycfg.py example.py   | sort -n -k2

coverage:
	python3 -mcoverage run example.py

example:
	cat example.py | nl -b a
