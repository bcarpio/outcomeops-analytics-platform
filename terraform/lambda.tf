# ============================================================================
# Log Parser Lambda
# ============================================================================

module "log_parser_lambda" {
  source  = "terraform-aws-modules/lambda/aws"
  version = "8.1.2"

  function_name = "${var.environment}-${var.app_name}-log-parser"
  description   = "Parses CloudFront access logs and writes analytics events to DynamoDB"
  handler       = "handler.lambda_handler"
  runtime       = "python3.12"
  timeout       = 60
  memory_size   = 512
  publish       = true

  source_path = [
    {
      path = "${path.module}/../lambda/log-parser"
      patterns = [
        "!tests/.*",
        "!__pycache__/.*",
        "!\\.venv/.*",
        "!requirements-dev\\.txt",
        "!.*\\.pyc",
        "!\\.pytest_cache/.*",
      ]
    }
  ]

  cloudwatch_logs_retention_in_days = 7
  quiet_archive_local_exec          = true

  environment_variables = {
    ENV                 = var.environment
    APP_NAME            = var.app_name
    LOG_LEVEL           = "INFO"
    TABLE_NAME          = module.analytics_events_table.dynamodb_table_id
    EXCLUDED_EXTENSIONS = join(",", var.excluded_extensions)
    EXCLUDED_PATHS      = join(",", var.excluded_paths)
  }

  allowed_triggers = {
    S3 = {
      service    = "s3"
      source_arn = module.analytics_logs_bucket.s3_bucket_arn
    }
  }

  attach_policy_statements = true
  policy_statements = {
    s3_read = {
      effect = "Allow"
      actions = [
        "s3:GetObject"
      ]
      resources = ["${module.analytics_logs_bucket.s3_bucket_arn}/*"]
    }
    dynamodb_write = {
      effect = "Allow"
      actions = [
        "dynamodb:BatchWriteItem",
        "dynamodb:PutItem",
        "dynamodb:UpdateItem"
      ]
      resources = [module.analytics_events_table.dynamodb_table_arn]
    }
    kms = {
      effect    = "Allow"
      actions   = ["kms:Decrypt"]
      resources = ["arn:aws:kms:*:*:key/*"]
    }
  }

}

# ============================================================================
# Analytics API Lambda
# ============================================================================

module "analytics_api_lambda" {
  source  = "terraform-aws-modules/lambda/aws"
  version = "8.1.2"

  function_name = "${var.environment}-${var.app_name}-api"
  description   = "Analytics query API - stats, pages, referrers, countries"
  handler       = "handler.lambda_handler"
  runtime       = "python3.12"
  timeout       = 30
  memory_size   = 256
  publish       = true

  source_path = [
    {
      path = "${path.module}/../lambda/analytics-api"
      patterns = [
        "!tests/.*",
        "!__pycache__/.*",
        "!\\.venv/.*",
        "!requirements-dev\\.txt",
        "!.*\\.pyc",
        "!\\.pytest_cache/.*",
      ]
    }
  ]

  cloudwatch_logs_retention_in_days = 7
  quiet_archive_local_exec          = true

  environment_variables = {
    ENV             = var.environment
    APP_NAME        = var.app_name
    LOG_LEVEL       = "INFO"
    TABLE_NAME      = module.analytics_events_table.dynamodb_table_id
    SESSIONS_TABLE  = module.journey_sessions_table.dynamodb_table_id
    ALLOWED_DOMAINS = join(",", var.domain_list)
  }

  allowed_triggers = {
    APIGateway = {
      service    = "apigateway"
      source_arn = "${module.analytics_api_gateway.api_execution_arn}/*/*"
    }
  }

  attach_policy_statements = true
  policy_statements = {
    dynamodb_read = {
      effect = "Allow"
      actions = [
        "dynamodb:Query",
        "dynamodb:GetItem"
      ]
      resources = [
        module.analytics_events_table.dynamodb_table_arn,
        "${module.analytics_events_table.dynamodb_table_arn}/index/*",
        module.journey_sessions_table.dynamodb_table_arn,
        "${module.journey_sessions_table.dynamodb_table_arn}/index/*"
      ]
    }
    kms = {
      effect    = "Allow"
      actions   = ["kms:Decrypt"]
      resources = ["arn:aws:kms:*:*:key/*"]
    }
  }

}

# ============================================================================
# Analytics Auth Lambda
# ============================================================================

module "analytics_auth_lambda" {
  source  = "terraform-aws-modules/lambda/aws"
  version = "8.1.2"

  function_name = "${var.environment}-${var.app_name}-auth"
  description   = "Magic link authentication for analytics dashboard"
  handler       = "handler.lambda_handler"
  runtime       = "python3.12"
  timeout       = 30
  memory_size   = 256
  publish       = true

  source_path = [
    {
      path             = "${path.module}/../lambda/analytics-auth"
      pip_requirements = true
      patterns = [
        "!tests/.*",
        "!__pycache__/.*",
        "!\\.venv/.*",
        "!requirements-dev\\.txt",
        "!.*\\.pyc",
        "!\\.pytest_cache/.*",
      ]
    }
  ]

  cloudwatch_logs_retention_in_days = 7
  quiet_archive_local_exec          = true

  environment_variables = {
    ENV               = var.environment
    APP_NAME          = var.app_name
    LOG_LEVEL         = "INFO"
    ADMIN_USERS_TABLE = module.admin_users_table.dynamodb_table_id
    SENDER_EMAIL      = var.sender_email
  }

  allowed_triggers = {
    APIGateway = {
      service    = "apigateway"
      source_arn = "${module.analytics_api_gateway.api_execution_arn}/*/*"
    }
  }

  attach_policy_statements = true
  policy_statements = {
    dynamodb_read = {
      effect = "Allow"
      actions = [
        "dynamodb:GetItem"
      ]
      resources = [module.admin_users_table.dynamodb_table_arn]
    }
    ssm_read = {
      effect = "Allow"
      actions = [
        "ssm:GetParameter"
      ]
      resources = [
        "arn:aws:ssm:${data.aws_region.current.id}:${data.aws_caller_identity.current.account_id}:parameter/${var.environment}/${var.app_name}/secrets/*"
      ]
    }
    ses_send = {
      effect = "Allow"
      actions = [
        "ses:SendEmail"
      ]
      resources = ["*"]
    }
    kms = {
      effect    = "Allow"
      actions   = ["kms:Decrypt"]
      resources = ["arn:aws:kms:*:*:key/*"]
    }
  }

}

# ============================================================================
# Journey Tracker Lambda
# ============================================================================

module "journey_tracker_lambda" {
  source  = "terraform-aws-modules/lambda/aws"
  version = "8.1.2"

  function_name = "${var.environment}-${var.app_name}-journey-tracker"
  description   = "Tracks user sessions and page journeys"
  handler       = "handler.lambda_handler"
  runtime       = "python3.12"
  timeout       = 10
  memory_size   = 256
  publish       = true

  source_path = [
    {
      path = "${path.module}/../lambda/journey-tracker"
      patterns = [
        "!tests/.*",
        "!__pycache__/.*",
        "!\\.venv/.*",
        "!requirements-dev\\.txt",
        "!.*\\.pyc",
        "!\\.pytest_cache/.*",
      ]
    }
  ]

  cloudwatch_logs_retention_in_days = 7
  quiet_archive_local_exec          = true

  environment_variables = {
    ENV             = var.environment
    APP_NAME        = var.app_name
    LOG_LEVEL       = "INFO"
    SESSIONS_TABLE  = module.journey_sessions_table.dynamodb_table_id
    ALLOWED_DOMAINS = join(",", var.domain_list)
  }

  # Allow triggers from all tracking API Gateways
  allowed_triggers = {
    for domain in var.domain_list : "APIGateway-${replace(domain, ".", "-")}" => {
      service    = "apigateway"
      source_arn = "${module.tracking_api_gateways[domain].api_execution_arn}/*/*"
    }
  }

  attach_policy_statements = true
  policy_statements = {
    dynamodb_write = {
      effect = "Allow"
      actions = [
        "dynamodb:BatchWriteItem",
        "dynamodb:PutItem",
        "dynamodb:UpdateItem"
      ]
      resources = [module.journey_sessions_table.dynamodb_table_arn]
    }
    kms = {
      effect    = "Allow"
      actions   = ["kms:Decrypt"]
      resources = ["arn:aws:kms:*:*:key/*"]
    }
  }

}

# ============================================================================
# Cache Builder Lambda
# ============================================================================

module "cache_builder_lambda" {
  source  = "terraform-aws-modules/lambda/aws"
  version = "8.1.2"

  function_name = "${var.environment}-${var.app_name}-cache-builder"
  description   = "Pre-computes dashboard data from rollups for fast reads"
  handler       = "handler.lambda_handler"
  runtime       = "python3.12"
  timeout       = 120
  memory_size   = 512
  publish       = true

  source_path = [
    {
      path = "${path.module}/../lambda/cache-builder"
      patterns = [
        "!tests/.*",
        "!__pycache__/.*",
        "!\\.venv/.*",
        "!requirements-dev\\.txt",
        "!.*\\.pyc",
        "!\\.pytest_cache/.*",
      ]
    }
  ]

  cloudwatch_logs_retention_in_days = 7
  quiet_archive_local_exec          = true

  environment_variables = {
    ENV         = var.environment
    APP_NAME    = var.app_name
    LOG_LEVEL   = "INFO"
    TABLE_NAME  = module.analytics_events_table.dynamodb_table_id
    DOMAIN_LIST = join(",", var.domain_list)
  }

  allowed_triggers = {
    EventBridge = {
      principal  = "events.amazonaws.com"
      source_arn = aws_cloudwatch_event_rule.cache_builder_schedule.arn
    }
  }

  attach_policy_statements = true
  policy_statements = {
    dynamodb_read_write = {
      effect = "Allow"
      actions = [
        "dynamodb:Query",
        "dynamodb:GetItem",
        "dynamodb:PutItem"
      ]
      resources = [module.analytics_events_table.dynamodb_table_arn]
    }
    kms = {
      effect    = "Allow"
      actions   = ["kms:Decrypt"]
      resources = ["arn:aws:kms:*:*:key/*"]
    }
  }

}

# EventBridge schedule for cache builder (hourly)
resource "aws_cloudwatch_event_rule" "cache_builder_schedule" {
  name                = "${var.environment}-${var.app_name}-cache-builder-schedule"
  description         = "Trigger cache builder Lambda hourly"
  schedule_expression = "rate(1 hour)"
}

resource "aws_cloudwatch_event_target" "cache_builder_target" {
  rule      = aws_cloudwatch_event_rule.cache_builder_schedule.name
  target_id = "cache-builder-lambda"
  arn       = module.cache_builder_lambda.lambda_function_arn
}
