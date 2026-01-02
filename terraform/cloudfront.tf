# ============================================================================
# Analytics Dashboard CloudFront Distribution
# analytics.outcomeops.ai (prd) / analytics.dev.outcomeops.ai (dev)
# ============================================================================

# ==============================================================================
# Origin Access Control for S3
# ==============================================================================

resource "aws_cloudfront_origin_access_control" "dashboard" {
  name                              = "${local.name_prefix}-dashboard-oac"
  description                       = "OAC for analytics dashboard S3 bucket"
  origin_access_control_origin_type = "s3"
  signing_behavior                  = "always"
  signing_protocol                  = "sigv4"
}

# ==============================================================================
# ACM Certificate for CloudFront (must be in us-east-1)
# ==============================================================================

resource "aws_acm_certificate" "dashboard" {
  provider          = aws.us_east_1
  domain_name       = local.analytics_domain
  validation_method = "DNS"

  lifecycle {
    create_before_destroy = true
  }

  tags = merge(local.tags, {
    Name = "${local.name_prefix}-dashboard-certificate"
  })
}

resource "aws_route53_record" "dashboard_cert_validation" {
  for_each = {
    for dvo in aws_acm_certificate.dashboard.domain_validation_options : dvo.domain_name => {
      name   = dvo.resource_record_name
      type   = dvo.resource_record_type
      record = dvo.resource_record_value
    }
  }

  zone_id = local.route53_zone_id
  name    = each.value.name
  type    = each.value.type
  records = [each.value.record]
  ttl     = 300
}

resource "aws_acm_certificate_validation" "dashboard" {
  provider                = aws.us_east_1
  certificate_arn         = aws_acm_certificate.dashboard.arn
  validation_record_fqdns = [for record in aws_route53_record.dashboard_cert_validation : record.fqdn]
}

# ==============================================================================
# CloudFront Distribution
# ==============================================================================

resource "aws_cloudfront_distribution" "dashboard" {
  origin {
    domain_name              = module.dashboard_bucket.s3_bucket_bucket_regional_domain_name
    origin_access_control_id = aws_cloudfront_origin_access_control.dashboard.id
    origin_id                = "S3Origin"
  }

  enabled             = true
  is_ipv6_enabled     = true
  default_root_object = "index.html"
  comment             = "Analytics dashboard for ${local.name_prefix}"

  aliases = [local.analytics_domain]

  default_cache_behavior {
    allowed_methods  = ["GET", "HEAD", "OPTIONS"]
    cached_methods   = ["GET", "HEAD"]
    target_origin_id = "S3Origin"

    forwarded_values {
      query_string = false
      cookies {
        forward = "none"
      }
    }

    viewer_protocol_policy = "redirect-to-https"
    min_ttl                = 0
    default_ttl            = 3600
    max_ttl                = 86400
    compress               = true
  }

  # SPA routing - return index.html for all 404s
  custom_error_response {
    error_code         = 404
    response_code      = 200
    response_page_path = "/index.html"
  }

  custom_error_response {
    error_code         = 403
    response_code      = 200
    response_page_path = "/index.html"
  }

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  viewer_certificate {
    acm_certificate_arn      = aws_acm_certificate_validation.dashboard.certificate_arn
    ssl_support_method       = "sni-only"
    minimum_protocol_version = "TLSv1.2_2021"
  }

  tags = merge(local.tags, {
    Name = "${local.name_prefix}-dashboard-cloudfront"
  })
}

# ==============================================================================
# S3 Bucket Policy for CloudFront
# ==============================================================================

resource "aws_s3_bucket_policy" "dashboard" {
  bucket = module.dashboard_bucket.s3_bucket_id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "AllowCloudFrontServicePrincipal"
        Effect    = "Allow"
        Principal = { Service = "cloudfront.amazonaws.com" }
        Action    = "s3:GetObject"
        Resource  = "${module.dashboard_bucket.s3_bucket_arn}/*"
        Condition = {
          StringEquals = {
            "AWS:SourceArn" = aws_cloudfront_distribution.dashboard.arn
          }
        }
      }
    ]
  })
}

# ==============================================================================
# Route53 A Record for Dashboard
# ==============================================================================

resource "aws_route53_record" "dashboard" {
  zone_id = local.route53_zone_id
  name    = local.analytics_domain
  type    = "A"

  alias {
    name                   = aws_cloudfront_distribution.dashboard.domain_name
    zone_id                = aws_cloudfront_distribution.dashboard.hosted_zone_id
    evaluate_target_health = false
  }
}

# ==============================================================================
# SSM Parameters for Dashboard
# ==============================================================================

resource "aws_ssm_parameter" "dashboard_bucket" {
  name        = "/${var.environment}/${var.app_name}/dashboard/s3_bucket"
  description = "Analytics dashboard S3 bucket name"
  type        = "String"
  value       = module.dashboard_bucket.s3_bucket_id

  tags = local.tags
}

resource "aws_ssm_parameter" "dashboard_cloudfront_id" {
  name        = "/${var.environment}/${var.app_name}/cloudfront/dashboard_distribution_id"
  description = "Analytics dashboard CloudFront distribution ID"
  type        = "String"
  value       = aws_cloudfront_distribution.dashboard.id

  tags = local.tags
}

resource "aws_ssm_parameter" "dashboard_url" {
  name        = "/${var.environment}/${var.app_name}/dashboard/url"
  description = "Analytics dashboard URL"
  type        = "String"
  value       = "https://${local.analytics_domain}"

  tags = local.tags
}
