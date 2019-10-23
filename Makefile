.PHONY: package deploy update mkbucket

package:
ifeq (,$(wildcard function.zip))
	cd ${VIRTUAL_ENV}/lib/python3.7/site-packages/; zip -r9 ${PROJECT_HOME}fara-watcher/function.zip .
	zip -g function.zip function.py
else
	$(info Already packaged.)
endif


mkbucket:
	aws --region us-east-1 --profile rji-futures-lab s3 mb s3://fara-watcher


deploy:
	make package
	aws --region us-east-1 --profile rji-futures-lab lambda create-function \
		--function-name fara-watcher --zip-file fileb://function.zip \
		--handler function.lambda_handler --runtime python3.7 \
		--role arn:aws:iam::796077402566:role/fara-watcher --timeout 120
	rm function.zip


update:
	make package
	aws --region us-east-1 --profile rji-futures-lab lambda update-function-code \
		--function-name fara-watcher --zip-file fileb://function.zip
	rm function.zip
