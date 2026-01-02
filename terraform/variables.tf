variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-west-2"
}

variable "environment" {
  description = "Environment name (dev, prd)"
  type        = string
}

variable "app_name" {
  description = "Application name"
  type        = string
  default     = "outcomeops-analytics"
}

variable "domain_list" {
  description = "List of domains to track analytics for"
  type        = list(string)
  default     = ["myfantasy.ai", "outcomeops.ai", "thetek.net"]
}

variable "domain_ssm_prefixes" {
  description = "Map of domain to SSM parameter prefix (for domains with different SSM naming)"
  type        = map(string)
  default = {
    "myfantasy.ai" = "fantacyai"
  }
}

variable "dashboard_domain" {
  description = "Domain for the analytics dashboard"
  type        = string
  default     = "analytics.outcomeops.ai"
}

variable "sender_email" {
  description = "Email address for sending magic links"
  type        = string
  default     = "noreply@outcomeops.ai"
}

variable "log_retention_days" {
  description = "CloudWatch log retention in days"
  type        = number
  default     = 7
}

variable "excluded_extensions" {
  description = "File extensions to exclude from analytics (static assets)"
  type        = list(string)
  default     = [".js", ".css", ".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".ico", ".woff", ".woff2", ".ttf", ".eot", ".map", ".txt", ".pdf", ".php"]
}

variable "excluded_paths" {
  description = "Path prefixes to exclude from analytics (bots, scanners, browser automation)"
  type        = list(string)
  default = [
    "/.well-known/",               # Browser feature detection
    "/apple-app-site-association", # iOS deep linking
    "/assetlinks.json",            # Android app verification
    "/.env",                       # Security scanners
    "/wp-admin",                   # WordPress exploit scanners
    "/wp-login.php",               # WordPress exploit scanners
    "/wp-includes",                # WordPress exploit scanners
    "/xmlrpc.php",                 # WordPress exploit scanners
    "/_ignition",                  # Laravel exploit scanners
    "/phpinfo.php",                # PHP exploit scanners
    "/admin",                      # Generic exploit scanners
    "/administrator",              # Generic exploit scanners
    "/phpmyadmin",                 # Database admin scanners
    "/cgi-bin",                    # CGI exploit scanners
    "/actuator",                   # Spring Boot actuator scanners
    "/.git",                       # Git exposure scanners
    "/config",                     # Config exposure scanners
    "/backup",                     # Backup file scanners
  ]
}
