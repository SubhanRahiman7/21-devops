provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project   = var.project_name
      ManagedBy = "Terraform"
    }
  }

  # ---- Optional: run the same code against a local AWS emulator (Moto) ---------------
  # Default (use_local_emulator = false) talks to real AWS with your normal credentials.
  access_key                  = var.use_local_emulator ? "test" : null
  secret_key                  = var.use_local_emulator ? "test" : null
  skip_credentials_validation = var.use_local_emulator
  skip_requesting_account_id  = var.use_local_emulator
  skip_metadata_api_check     = var.use_local_emulator
  s3_use_path_style           = var.use_local_emulator

  endpoints {
    ec2 = var.use_local_emulator ? var.emulator_endpoint : null
    ecr = var.use_local_emulator ? var.emulator_endpoint : null
    iam = var.use_local_emulator ? var.emulator_endpoint : null
    kms = var.use_local_emulator ? var.emulator_endpoint : null
    s3  = var.use_local_emulator ? var.emulator_endpoint : null
    sts = var.use_local_emulator ? var.emulator_endpoint : null
  }
}
