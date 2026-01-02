# ============================================================================
# Analytics Events Table
# ============================================================================

module "analytics_events_table" {
  source  = "terraform-aws-modules/dynamodb-table/aws"
  version = "4.2.0"

  name      = "${var.environment}-${var.app_name}-events"
  hash_key  = "PK"
  range_key = "SK"

  billing_mode = "PAY_PER_REQUEST"

  attributes = [
    { name = "PK", type = "S" },
    { name = "SK", type = "S" },
    { name = "GSI1PK", type = "S" },
    { name = "GSI1SK", type = "S" },
    { name = "GSI2PK", type = "S" },
    { name = "GSI2SK", type = "S" }
  ]

  global_secondary_indexes = [
    {
      name            = "GSI1"
      hash_key        = "GSI1PK"
      range_key       = "GSI1SK"
      projection_type = "ALL"
    },
    {
      name            = "GSI2"
      hash_key        = "GSI2PK"
      range_key       = "GSI2SK"
      projection_type = "ALL"
    }
  ]

  ttl_enabled        = true
  ttl_attribute_name = "ttl"

  point_in_time_recovery_enabled = var.environment == "prd"

  tags = {
    Name        = "${var.environment}-${var.app_name}-events"
    Environment = var.environment
    App         = var.app_name
  }
}

# ============================================================================
# Admin Users Table (for magic link auth)
# ============================================================================

module "admin_users_table" {
  source  = "terraform-aws-modules/dynamodb-table/aws"
  version = "4.2.0"

  name     = "${var.environment}-${var.app_name}-admin-users"
  hash_key = "email"

  billing_mode = "PAY_PER_REQUEST"

  attributes = [
    { name = "email", type = "S" }
  ]

  point_in_time_recovery_enabled = var.environment == "prd"

  tags = {
    Name        = "${var.environment}-${var.app_name}-admin-users"
    Environment = var.environment
    App         = var.app_name
  }
}

# ============================================================================
# SSM Parameters for table names
# ============================================================================

resource "aws_ssm_parameter" "analytics_events_table" {
  name  = "/${var.environment}/${var.app_name}/dynamodb/events_table"
  type  = "String"
  value = module.analytics_events_table.dynamodb_table_id

  tags = {
    Environment = var.environment
    App         = var.app_name
  }
}

resource "aws_ssm_parameter" "admin_users_table" {
  name  = "/${var.environment}/${var.app_name}/dynamodb/admin_users_table"
  type  = "String"
  value = module.admin_users_table.dynamodb_table_id

  tags = {
    Environment = var.environment
    App         = var.app_name
  }
}

# ============================================================================
# Journey Sessions Table
# ============================================================================

module "journey_sessions_table" {
  source  = "terraform-aws-modules/dynamodb-table/aws"
  version = "4.2.0"

  name      = "${var.environment}-${var.app_name}-sessions"
  hash_key  = "PK"
  range_key = "SK"

  billing_mode = "PAY_PER_REQUEST"

  attributes = [
    { name = "PK", type = "S" },     # SESSION#{session_id}
    { name = "SK", type = "S" },     # EVENT#{timestamp}#{event_id}
    { name = "GSI1PK", type = "S" }, # DOMAIN#{domain}#DATE#{date}
    { name = "GSI1SK", type = "S" }, # SESSION#{session_id}
    { name = "GSI2PK", type = "S" }, # DOMAIN#{domain}#PATH#{path}
    { name = "GSI2SK", type = "S" }  # TIMESTAMP
  ]

  global_secondary_indexes = [
    {
      name            = "GSI1"
      hash_key        = "GSI1PK"
      range_key       = "GSI1SK"
      projection_type = "ALL"
    },
    {
      name            = "GSI2"
      hash_key        = "GSI2PK"
      range_key       = "GSI2SK"
      projection_type = "ALL"
    }
  ]

  ttl_enabled        = true
  ttl_attribute_name = "ttl"

  point_in_time_recovery_enabled = var.environment == "prd"

  tags = {
    Name        = "${var.environment}-${var.app_name}-sessions"
    Environment = var.environment
    App         = var.app_name
    Purpose     = "journey-tracking"
  }
}

resource "aws_ssm_parameter" "sessions_table" {
  name  = "/${var.environment}/${var.app_name}/dynamodb/sessions_table"
  type  = "String"
  value = module.journey_sessions_table.dynamodb_table_id

  tags = {
    Environment = var.environment
    App         = var.app_name
  }
}
