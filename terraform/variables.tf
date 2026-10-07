variable "aws_region" {
  type        = string
  description = "AWS region for all resources."
  default     = "ap-south-1"
}

variable "project_name" {
  type        = string
  description = "Name prefix for resources and tags."
  default     = "task-tracker"
}

variable "environment" {
  type        = string
  description = "Environment name (used in tags and names)."
  default     = "prod"
}

variable "vpc_cidr" {
  type        = string
  description = "CIDR block of the VPC."
  default     = "10.30.0.0/16"
}

variable "public_subnet_cidr" {
  type        = string
  description = "CIDR block of the public subnet that hosts the application server."
  default     = "10.30.1.0/24"
}

variable "instance_type" {
  type        = string
  description = "EC2 instance type of the application host."
  default     = "t3.micro"
}

variable "ami_id" {
  type        = string
  description = "AMI to launch. Empty = latest Amazon Linux 2023 (looked up automatically)."
  default     = ""
}

variable "app_image_tag" {
  type        = string
  description = "Image tag of the application in the ECR repository started by the EC2 host."
  default     = "latest"
}

variable "allowed_ssh_cidr" {
  type        = string
  description = "CIDR allowed to reach SSH (22). Restrict to your own IP, e.g. 203.0.113.10/32."
  default     = "10.0.0.0/8"
}

variable "artifacts_bucket_name" {
  type        = string
  description = "Globally unique name of the S3 bucket for build artifacts."
}

variable "use_local_emulator" {
  type        = bool
  description = "true = send API calls to a local AWS emulator (Moto) instead of real AWS."
  default     = false
}

variable "emulator_endpoint" {
  type        = string
  description = "URL of the local AWS emulator (only used when use_local_emulator = true)."
  default     = "http://localhost:5555"
}
