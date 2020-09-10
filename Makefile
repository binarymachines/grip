

regen:
	./mkapp --config config/test.yaml --project-name griptest -f > testapp.py


regen-verifier:
	./mkapp --config config/verifier_svc.yaml --project-name verifier -f > verifier.py


run:
	python testapp.py --config config/test.yaml


run-verifier:
	python verifier.py --config config/verifier_svc.yaml


transfer:
	cp vfy_*.py ~/workshop/fstate/finite-state/lib/queryutil
	cp core.py ~/workshop/fstate/finite-state/lib/queryutil
	cp templates.py ~/workshop/fstate/finite-state/lib/queryutil
	cp griputil.py ~/workshop/fstate/finite-state/lib/queryutil
	cp mkapp ~/workshop/fstate/finite-state/lib/queryutil
	cp mkschema ~/workshop/fstate/finite-state/lib/queryutil
	cp config/verifier_svc.yaml ~/workshop/fstate/finite-state/lib/queryutil/config