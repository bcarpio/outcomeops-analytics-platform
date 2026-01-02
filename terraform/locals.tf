locals {
  name_prefix = "${var.environment}-${var.app_name}"

  # Workspace helpers
  workspace_is_dev = terraform.workspace == "dev"
  workspace_is_prd = terraform.workspace == "prd"

  # Domain configuration
  # prd: analytics.outcomeops.ai / api.analytics.outcomeops.ai
  # dev: analytics.dev.outcomeops.ai / api.analytics.dev.outcomeops.ai
  env_prefix       = var.environment == "prd" ? "" : "${var.environment}."
  base_domain      = "${local.env_prefix}outcomeops.ai"
  analytics_domain = "analytics.${local.base_domain}"
  api_domain       = "api.analytics.${local.base_domain}"
  route53_zone_id  = data.aws_ssm_parameter.route53_zone_id.value

  tags = {
    Application = var.app_name
    Environment = var.environment
    ManagedBy   = "terraform"
  }
}

# Validate that workspace matches environment to prevent deploying wrong config
check "workspace_matches_environment" {
  assert {
    condition = (
      (terraform.workspace == "dev" && var.environment == "dev") ||
      (terraform.workspace == "prd" && var.environment == "prd")
    )
    error_message = "Terraform workspace '${terraform.workspace}' does not match environment variable '${var.environment}'. Run 'terraform workspace select ${var.environment}' to fix."
  }
}

# Route53 zone ID from outcomeops.ai (created in prd, shared across environments)
data "aws_ssm_parameter" "route53_zone_id" {
  name = "/prd/outcomeops.ai/route53/zone_id"
}
