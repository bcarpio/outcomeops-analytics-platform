terraform {
  backend "s3" {
    bucket = "terraform-state-136400015737-us-west-2-dev"
    key    = "outcomeops-analytics-platform.tfstate"
    region = "us-west-2"
  }
}
