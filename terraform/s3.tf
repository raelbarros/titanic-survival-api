resource "aws_s3_bucket" "model" {
  bucket = "s3-${var.project_name}"
}

resource "aws_s3_bucket_public_access_block" "model" {
  bucket                  = aws_s3_bucket.model.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_object" "model_pkl" {
  bucket = aws_s3_bucket.model.id
  key    = "model.pkl"
  source = "${path.module}/../model/model.pkl"
  etag   = filemd5("${path.module}/../model/model.pkl")
}

resource "aws_s3_object" "lambda_code" {
  bucket = aws_s3_bucket.model.id
  key    = "lambda.zip"
  source = "${path.module}/../lambda.zip"
  etag = filemd5("${path.module}/../lambda.zip")
}


