.PHONY: package deploy update mkbucket

package:
ifeq (,$(wildcard function.zip))
	cd ${VIRTUAL_ENV}/lib/python3.7/site-packages/; zip -r9 ${PROJECT_HOME}${LAMBDA_FUNCTION_NAME}/function.zip .
	zip -g function.zip function.py
else
	$(info Already packaged.)
endif


mkbucket:
	aws s3 mb s3://fara-watcher


deploy:
	make package
	aws --region lambda create-function \
		--function-name ${LAMBDA_FUNCTION_NAME} \
		--zip-file fileb://function.zip \
		--handler function.lambda_handler \
		--runtime python3.7 \
		--role ${AWS_ROLE} \
		--timeout 120
	rm function.zip


update:
	make package
	aws lambda update-function-code \
		--function-name ${LAMBDA_FUNCTION_NAME} \
		--zip-file fileb://function.zip
	rm function.zip
