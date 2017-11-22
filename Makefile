dots:
	@python3  pycfg.py example.py -d

cfg:
	@python3  pycfg.py example.py -c

coverage:
	python3 -mcoverage run --branch example.py
	python3 -mcoverage report

xml:
	python3 -mcoverage xml

example:
	cat example.py | nl -b a

clean:
	rm -rf .coverage
