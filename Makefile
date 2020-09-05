

regen:
	./mkapp --config config/test.yaml --project-name griptest -f > testapp.py


regen-verifier:
	./mkapp --config config/verifier_svc.yaml --project-name verifier -f > verifier.py


run:
	python testapp.py --config config/test.yaml


run-verifier:
	python verifier.py --config config/verifier_svc.yaml