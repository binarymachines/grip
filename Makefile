

regen:
	./mkapp --config config/test.yaml --project-name griptest -f > testapp.py

run:
	python testapp.py --config config/test.yaml
	