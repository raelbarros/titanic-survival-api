resource "aws_lambda_function" "titanic" {
  function_name    = "lambda_${var.project_name}"
  handler          = "lambda_function.lambda_handler"
  runtime          = "python3.12"
  role             = aws_iam_role.lambda_exec.arn
  memory_size      = var.lambda_memory_mb
  timeout          = var.lambda_timeout_seconds

  s3_bucket = aws_s3_bucket.model.id
  s3_key    = aws_s3_object.lambda_code.key
  source_code_hash = filebase64sha256("${path.module}/../lambda.zip")

  environment {
    variables = {
      DYNAMODB_TABLE = aws_dynamodb_table.passengers.name
      MODEL_BUCKET   = aws_s3_bucket.model.id
      MODEL_KEY      = "model.pkl"
    }
  }

  depends_on = [
    aws_iam_role_policy_attachment.lambda_basic,
    aws_cloudwatch_log_group.lambda,
    aws_s3_object.lambda_code
  ]
}

resource "aws_cloudwatch_log_group" "lambda" {
  name              = "/aws/lambda/${var.project_name}"
  retention_in_days = 14
}

# Permissao para o API Gateway invocar a Lambda
resource "aws_lambda_permission" "apigw" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.titanic.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.titanic.execution_arn}/*/*"
}
