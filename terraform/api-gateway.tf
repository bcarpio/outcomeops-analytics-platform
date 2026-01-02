# ============================================================================
# Analytics API Gateway (HTTP API)
# api.analytics.outcomeops.ai (prd) / api.analytics.dev.outcomeops.ai (dev)
# ============================================================================

module "analytics_api_gateway" {
  source  = "terraform-aws-modules/apigateway-v2/aws"
  version = "5.2.1"

  name          = "${local.name_prefix}-api"
  description   = "Analytics Platform API"
  protocol_type = "HTTP"

  cors_configuration = {
    allow_origins = ["https://${local.analytics_domain}"]
    allow_methods = ["GET", "POST", "OPTIONS"]
    allow_headers = ["Content-Type", "Authorization"]
    max_age       = 300
  }

  # Custom domain - we handle certificate and Route53 ourselves
  domain_name                 = local.api_domain
  domain_name_certificate_arn = module.api_certificate.acm_certificate_arn
  create_certificate          = false
  create_domain_records       = false

  # Access logging
  stage_access_log_settings = {
    create_log_group            = true
    log_group_retention_in_days = 7
    format = jsonencode({
      requestId      = "$context.requestId"
      ip             = "$context.identity.sourceIp"
      requestTime    = "$context.requestTime"
      httpMethod     = "$context.httpMethod"
      routeKey       = "$context.routeKey"
      status         = "$context.status"
      responseLength = "$context.responseLength"
      errorMessage   = "$context.error.message"
    })
  }

  # Routes and integrations
  routes = {
    # Auth routes
    "POST /auth/magic-link" = {
      integration = {
        uri                    = module.analytics_auth_lambda.lambda_function_arn
        type                   = "AWS_PROXY"
        payload_format_version = "2.0"
      }
    }
    "POST /auth/verify" = {
      integration = {
        uri                    = module.analytics_auth_lambda.lambda_function_arn
        type                   = "AWS_PROXY"
        payload_format_version = "2.0"
      }
    }

    # Analytics API routes
    "GET /analytics/stats/{domain}" = {
      integration = {
        uri                    = module.analytics_api_lambda.lambda_function_arn
        type                   = "AWS_PROXY"
        payload_format_version = "2.0"
      }
    }
    "GET /analytics/pages/{domain}" = {
      integration = {
        uri                    = module.analytics_api_lambda.lambda_function_arn
        type                   = "AWS_PROXY"
        payload_format_version = "2.0"
      }
    }
    "GET /analytics/referrers/{domain}" = {
      integration = {
        uri                    = module.analytics_api_lambda.lambda_function_arn
        type                   = "AWS_PROXY"
        payload_format_version = "2.0"
      }
    }
    "GET /analytics/hours/{domain}" = {
      integration = {
        uri                    = module.analytics_api_lambda.lambda_function_arn
        type                   = "AWS_PROXY"
        payload_format_version = "2.0"
      }
    }
    "GET /analytics/countries/{domain}" = {
      integration = {
        uri                    = module.analytics_api_lambda.lambda_function_arn
        type                   = "AWS_PROXY"
        payload_format_version = "2.0"
      }
    }

    # Journey tracking routes
    "GET /analytics/journeys/{domain}" = {
      integration = {
        uri                    = module.analytics_api_lambda.lambda_function_arn
        type                   = "AWS_PROXY"
        payload_format_version = "2.0"
      }
    }
    "GET /analytics/sessions/{domain}" = {
      integration = {
        uri                    = module.analytics_api_lambda.lambda_function_arn
        type                   = "AWS_PROXY"
        payload_format_version = "2.0"
      }
    }
    "GET /analytics/sessions/{domain}/{session_id}" = {
      integration = {
        uri                    = module.analytics_api_lambda.lambda_function_arn
        type                   = "AWS_PROXY"
        payload_format_version = "2.0"
      }
    }
    "GET /analytics/flows/{domain}" = {
      integration = {
        uri                    = module.analytics_api_lambda.lambda_function_arn
        type                   = "AWS_PROXY"
        payload_format_version = "2.0"
      }
    }
    "GET /analytics/hallucinations/{domain}" = {
      integration = {
        uri                    = module.analytics_api_lambda.lambda_function_arn
        type                   = "AWS_PROXY"
        payload_format_version = "2.0"
      }
    }
  }

  tags = local.tags
}

# ============================================================================
# ACM Certificate for API Domain
# ============================================================================

module "api_certificate" {
  source  = "terraform-aws-modules/acm/aws"
  version = "5.1.1"

  domain_name = local.api_domain
  zone_id     = local.route53_zone_id

  validation_method = "DNS"

  wait_for_validation = true

  tags = merge(local.tags, {
    Name = "${local.name_prefix}-api-certificate"
  })
}

# ============================================================================
# Route53 Record for API Domain
# ============================================================================

resource "aws_route53_record" "api" {
  zone_id = local.route53_zone_id
  name    = local.api_domain
  type    = "A"

  alias {
    name                   = module.analytics_api_gateway.domain_name_target_domain_name
    zone_id                = module.analytics_api_gateway.domain_name_hosted_zone_id
    evaluate_target_health = false
  }
}

# ============================================================================
# SSM Parameter for API Endpoint
# ============================================================================

resource "aws_ssm_parameter" "api_endpoint" {
  name        = "/${var.environment}/${var.app_name}/api/endpoint"
  description = "Analytics API endpoint URL"
  type        = "String"
  value       = "https://${local.api_domain}"

  tags = local.tags
}
