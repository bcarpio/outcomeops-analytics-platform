# ============================================================================
# Analytics Logs Bucket (CloudFront access logs)
# ============================================================================

module "analytics_logs_bucket" {
  source  = "terraform-aws-modules/s3-bucket/aws"
  version = "4.1.1"

  bucket = "${var.environment}-${var.app_name}-logs-${data.aws_caller_identity.current.account_id}"

  # CloudFront logging requires ACL access
  control_object_ownership = true
  object_ownership         = "BucketOwnerPreferred"
  acl                      = "log-delivery-write"

  versioning = {
    enabled = false
  }

  lifecycle_rule = [
    {
      id     = "expire-old-logs"
      status = "Enabled"

      expiration = {
        days = 30
      }

      noncurrent_version_expiration = {
        days = 7
      }
    }
  ]

  server_side_encryption_configuration = {
    rule = {
      apply_server_side_encryption_by_default = {
        sse_algorithm = "AES256"
      }
    }
  }

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true

  tags = {
    Name        = "${var.environment}-${var.app_name}-logs"
    Environment = var.environment
    App         = var.app_name
    Purpose     = "cloudfront-access-logs"
  }
}

# S3 bucket notification for Lambda trigger
resource "aws_s3_bucket_notification" "analytics_logs" {
  bucket = module.analytics_logs_bucket.s3_bucket_id

  lambda_function {
    lambda_function_arn = module.log_parser_lambda.lambda_function_arn
    events              = ["s3:ObjectCreated:*"]
    filter_suffix       = ".gz"
  }

  depends_on = [module.log_parser_lambda]
}

# SSM Parameters for logs bucket (used by other CloudFront distributions)
resource "aws_ssm_parameter" "logs_bucket_name" {
  name        = "/${var.environment}/${var.app_name}/logs/s3_bucket"
  description = "S3 bucket name for CloudFront access logs"
  type        = "String"
  value       = module.analytics_logs_bucket.s3_bucket_id

  tags = local.tags
}

resource "aws_ssm_parameter" "logs_bucket_arn" {
  name        = "/${var.environment}/${var.app_name}/logs/s3_bucket_arn"
  description = "S3 bucket ARN for CloudFront access logs"
  type        = "String"
  value       = module.analytics_logs_bucket.s3_bucket_arn

  tags = local.tags
}

# ============================================================================
# Dashboard Bucket (React app static files)
# ============================================================================

module "dashboard_bucket" {
  source  = "terraform-aws-modules/s3-bucket/aws"
  version = "4.1.1"

  bucket = "${var.environment}-${var.app_name}-dashboard"

  versioning = {
    enabled = true
  }

  lifecycle_rule = [
    {
      id     = "expire-old-versions"
      status = "Enabled"

      noncurrent_version_expiration = {
        days = 30
      }
    }
  ]

  server_side_encryption_configuration = {
    rule = {
      apply_server_side_encryption_by_default = {
        sse_algorithm = "AES256"
      }
    }
  }

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true

  tags = {
    Name        = "${var.environment}-${var.app_name}-dashboard"
    Environment = var.environment
    App         = var.app_name
    Purpose     = "dashboard-static-files"
  }
}
