# Zip das dependencias para Linux
zip:
	rm -rf package lambda.zip
	mkdir -p package

	pip install \
	--platform manylinux2014_x86_64 \
	--target=./package \
	--implementation cp \
	--python-version 3.12 \
	--only-binary=:all: --upgrade \
	-r lambda/requirements.txt

	find package/ -type d -name "__pycache__" -exec rm -rf {} +
	find package/ -type d -name "*.dist-info" -exec rm -rf {} +
	find package/ -type d -name "*.egg-info" -exec rm -rf {} +
	find package/ -type f -name "*.pyc" -delete

	cp lambda/lambda_function.py package/

	cd package && zip -r ../lambda.zip .

# Inicializa e aplica o Terraform
deploy: zip
	cd terraform && terraform init
	cd terraform && terraform apply -auto-approve

# Destrói toda a infraestrutura
destroy:
	cd terraform && terraform destroy -auto-approve

# Testa os endpoints de deploy
test:
	@API_URL=$$(cd terraform && terraform output -raw api_url) && \
	echo "--- POST /sobreviventes ---" && \
	curl -s -X POST "$$API_URL/sobreviventes" \
	  -H "Content-Type: application/json" \
	  -d '{"passengers":[{"id":"01","pclass":1,"sex":"female","age":29,"sibsp":0,"parch":0,"fare":211.3,"embarked":"Q"}]}' | jq . && \
	echo "--- GET /sobreviventes ---" && \
	curl -s "$$API_URL/sobreviventes" | jq . && \
	echo "--- GET /sobreviventes/01 ---" && \
	curl -s "$$API_URL/sobreviventes/01" | jq . && \
	echo "--- DELETE /sobreviventes/01 ---" && \
	curl -s -X DELETE "$$API_URL/sobreviventes/01" | jq .
