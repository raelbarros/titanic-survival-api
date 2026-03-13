data "aws_iam_policy_document" "trust_lambda_role" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "lambda_exec" {
  name               = "role_${var.project_name}_lambda"
  assume_role_policy = data.aws_iam_policy_document.trust_lambda_role.json
}

# Permissao de logs no CloudWatch
resource "aws_iam_role_policy_attachment" "lambda_basic" {
  role       = aws_iam_role.lambda_exec.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# Permissao para DynamoDB
data "aws_iam_policy_document" "policy_lambda_dynamodb" {
  statement {
    effect = "Allow"
    actions = [
      "dynamodb:PutItem",
      "dynamodb:GetItem",
      "dynamodb:DeleteItem",
      "dynamodb:Scan",
      "dynamodb:Query",
    ]
    resources = ["*"]
  }
}

resource "aws_iam_role_policy" "lambda_dynamodb" {
  name   = "policy_lambda_allow_dynamo"
  role   = aws_iam_role.lambda_exec.id
  policy = data.aws_iam_policy_document.policy_lambda_dynamodb.json
}

# Permisssao para S3
data "aws_iam_policy_document" "policy_lambda_s3" {
  statement {
    effect    = "Allow"
    actions   = ["s3:GetObject"]
    resources = ["*"]
  }
}

resource "aws_iam_role_policy" "lambda_s3" {
  name   = "policy_lambnda_allow_s3"
  role   = aws_iam_role.lambda_exec.id
  policy = data.aws_iam_policy_document.policy_lambda_s3.json
}
