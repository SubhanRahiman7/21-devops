output "vpc_id" {
  description = "ID of the VPC."
  value       = aws_vpc.main.id
}

output "public_subnet_id" {
  description = "ID of the public subnet."
  value       = aws_subnet.public.id
}

output "security_group_id" {
  description = "ID of the application security group."
  value       = aws_security_group.app.id
}

output "ecr_repository_url" {
  description = "URL of the ECR repository (docker push target)."
  value       = aws_ecr_repository.app.repository_url
}

output "artifacts_bucket" {
  description = "Name of the S3 artifacts bucket."
  value       = aws_s3_bucket.artifacts.bucket
}

output "instance_id" {
  description = "ID of the application EC2 instance."
  value       = aws_instance.app.id
}

output "instance_public_ip" {
  description = "Public IP of the application host."
  value       = aws_instance.app.public_ip
}

output "app_url" {
  description = "URL of the application on the EC2 host."
  value       = "http://${aws_instance.app.public_ip}"
}
