# ============================================================================
# API Gateway Outputs
# ============================================================================

output "api_endpoint" {
  description = "API Gateway endpoint URL (custom domain)"
  value       = "https://${local.api_domain}"
}

output "api_id" {
  description = "API Gateway ID"
  value       = module.analytics_api_gateway.api_id
}

output "api_execution_endpoint" {
  description = "API Gateway execution endpoint"
  value       = module.analytics_api_gateway.api_endpoint
}

# ============================================================================
# CloudFront / Dashboard Outputs
# ============================================================================

output "dashboard_url" {
  description = "Analytics dashboard URL"
  value       = "https://${local.analytics_domain}"
}

output "cloudfront_distribution_id" {
  description = "CloudFront distribution ID for dashboard"
  value       = aws_cloudfront_distribution.dashboard.id
}

output "cloudfront_domain_name" {
  description = "CloudFront distribution domain name"
  value       = aws_cloudfront_distribution.dashboard.domain_name
}

# ============================================================================
# S3 Outputs
# ============================================================================

output "logs_bucket_name" {
  description = "S3 bucket name for CloudFront logs"
  value       = module.analytics_logs_bucket.s3_bucket_id
}

output "logs_bucket_arn" {
  description = "S3 bucket ARN for CloudFront logs"
  value       = module.analytics_logs_bucket.s3_bucket_arn
}

output "dashboard_bucket_name" {
  description = "S3 bucket name for dashboard static files"
  value       = module.dashboard_bucket.s3_bucket_id
}

# ============================================================================
# DynamoDB Outputs
# ============================================================================

output "analytics_table_name" {
  description = "DynamoDB table name for analytics events"
  value       = module.analytics_events_table.dynamodb_table_id
}

output "analytics_table_arn" {
  description = "DynamoDB table ARN for analytics events"
  value       = module.analytics_events_table.dynamodb_table_arn
}

output "admin_users_table_name" {
  description = "DynamoDB table name for admin users"
  value       = module.admin_users_table.dynamodb_table_id
}

# ============================================================================
# Lambda Outputs
# ============================================================================

output "log_parser_function_name" {
  description = "Log parser Lambda function name"
  value       = module.log_parser_lambda.lambda_function_name
}

output "log_parser_function_arn" {
  description = "Log parser Lambda function ARN"
  value       = module.log_parser_lambda.lambda_function_arn
}

output "analytics_api_function_name" {
  description = "Analytics API Lambda function name"
  value       = module.analytics_api_lambda.lambda_function_name
}

output "analytics_api_function_arn" {
  description = "Analytics API Lambda function ARN"
  value       = module.analytics_api_lambda.lambda_function_arn
}

output "analytics_auth_function_name" {
  description = "Analytics Auth Lambda function name"
  value       = module.analytics_auth_lambda.lambda_function_name
}

output "analytics_auth_function_arn" {
  description = "Analytics Auth Lambda function ARN"
  value       = module.analytics_auth_lambda.lambda_function_arn
}

output "journey_tracker_function_name" {
  description = "Journey Tracker Lambda function name"
  value       = module.journey_tracker_lambda.lambda_function_name
}

output "journey_tracker_function_arn" {
  description = "Journey Tracker Lambda function ARN"
  value       = module.journey_tracker_lambda.lambda_function_arn
}

# ============================================================================
# Journey Tracking Outputs
# ============================================================================

output "sessions_table_name" {
  description = "DynamoDB table name for journey sessions"
  value       = module.journey_sessions_table.dynamodb_table_id
}

output "sessions_table_arn" {
  description = "DynamoDB table ARN for journey sessions"
  value       = module.journey_sessions_table.dynamodb_table_arn
}

output "tracking_endpoints" {
  description = "Tracking API endpoints per domain"
  value = {
    for domain, config in local.tracking_domains :
    domain => "https://${config.tracking_domain}"
  }
}
