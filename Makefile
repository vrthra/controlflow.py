dots:
	@python3  pycfg.py example.py -d

parents:
	@python3  pycfg.py example.py -p | sort -n -k2

children:
	@python3  pycfg.py example.py -c | sort -n -k2

coverage:
	python3 -mcoverage run --branch example.py
	python3 -mcoverage report

xml:
	python3 -mcoverage xml

example:
	cat example.py | nl -b a

clean:
	rm -rf .coverage
