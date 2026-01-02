# ============================================================================
# Journey Tracking API Gateways (per-domain first-party endpoints)
# t.myfantasy.ai, t.outcomeops.ai, t.thetek.net
# ============================================================================

locals {
  # Build tracking domain config for each domain in domain_list
  tracking_domains = {
    for domain in var.domain_list : domain => {
      domain          = domain
      tracking_domain = "t.${var.environment == "prd" ? "" : "${var.environment}."}${domain}"
      ssm_prefix      = lookup(var.domain_ssm_prefixes, domain, domain)
      zone_id_param   = "/prd/${lookup(var.domain_ssm_prefixes, domain, domain)}/route53/zone_id"
    }
  }
}

# Lookup Route53 zone IDs from SSM (stored by each domain's repo)
data "aws_ssm_parameter" "tracking_zone_ids" {
  for_each = local.tracking_domains
  name     = each.value.zone_id_param
}

# ============================================================================
# ACM Certificates (one per tracking domain)
# ============================================================================

module "tracking_certificates" {
  for_each = local.tracking_domains
  source   = "terraform-aws-modules/acm/aws"
  version  = "5.1.1"

  domain_name = each.value.tracking_domain
  zone_id     = data.aws_ssm_parameter.tracking_zone_ids[each.key].value

  validation_method   = "DNS"
  wait_for_validation = true

  tags = merge(local.tags, {
    Name   = "${local.name_prefix}-tracking-${replace(each.key, ".", "-")}"
    Domain = each.key
  })
}

# ============================================================================
# API Gateways (one per tracking domain, all route to same Lambda)
# ============================================================================

module "tracking_api_gateways" {
  for_each = local.tracking_domains
  source   = "terraform-aws-modules/apigateway-v2/aws"
  version  = "5.2.1"

  name          = "${local.name_prefix}-tracking-${replace(each.key, ".", "-")}"
  description   = "Journey tracking API for ${each.key}"
  protocol_type = "HTTP"

  cors_configuration = {
    allow_origins = [
      "https://${each.key}",
      "https://www.${each.key}",
      "https://${var.environment == "prd" ? "" : "${var.environment}."}${each.key}"
    ]
    allow_methods = ["POST", "OPTIONS"]
    allow_headers = ["Content-Type"]
    max_age       = 300
  }

  # Custom domain
  domain_name                 = each.value.tracking_domain
  domain_name_certificate_arn = module.tracking_certificates[each.key].acm_certificate_arn
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

  # Routes - all point to journey-tracker Lambda
  routes = {
    "POST /t" = {
      integration = {
        uri                    = module.journey_tracker_lambda.lambda_function_arn
        type                   = "AWS_PROXY"
        payload_format_version = "2.0"
      }
    }
    "POST /t/batch" = {
      integration = {
        uri                    = module.journey_tracker_lambda.lambda_function_arn
        type                   = "AWS_PROXY"
        payload_format_version = "2.0"
      }
    }
  }

  tags = merge(local.tags, { Domain = each.key })
}

# ============================================================================
# Route53 Records (one per tracking domain)
# ============================================================================

resource "aws_route53_record" "tracking" {
  for_each = local.tracking_domains

  zone_id = data.aws_ssm_parameter.tracking_zone_ids[each.key].value
  name    = each.value.tracking_domain
  type    = "A"

  alias {
    name                   = module.tracking_api_gateways[each.key].domain_name_target_domain_name
    zone_id                = module.tracking_api_gateways[each.key].domain_name_hosted_zone_id
    evaluate_target_health = false
  }
}

# ============================================================================
# SSM Parameters for tracking endpoints
# ============================================================================

resource "aws_ssm_parameter" "tracking_endpoints" {
  for_each = local.tracking_domains

  name        = "/${var.environment}/${var.app_name}/tracking/${replace(each.key, ".", "-")}/endpoint"
  description = "Tracking endpoint for ${each.key}"
  type        = "String"
  value       = "https://${each.value.tracking_domain}"

  tags = local.tags
}
