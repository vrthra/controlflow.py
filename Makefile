dots:
	@python3  pycfg.py example.py -d

json:
	@python3  pycfg.py example.py   | sort -n -k2
