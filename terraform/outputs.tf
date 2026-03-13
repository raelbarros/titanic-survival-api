output "api_url" {
  description = "URL base da API"
  value       = "https://${aws_api_gateway_rest_api.titanic.id}.execute-api.${var.aws_region}.amazonaws.com/dev"
}

output "lambda_function_name" {
  description = "Nome da função Lambda"
  value       = aws_lambda_function.titanic.function_name
}

output "dynamodb_table_name" {
  description = "Nome da tabela DynamoDB"
  value       = aws_dynamodb_table.database.name
}

output "model_bucket_name" {
  description = "Nome do bucket S3 com os dados"
  value       = aws_s3_bucket.model.id
}
