# Container registry for the application image
resource "aws_ecr_repository" "app" {
  name                 = "${var.project_name}/app"
  image_tag_mutability = "IMMUTABLE"
  force_delete         = true # demo only: allow `terraform destroy` even if images exist

  image_scanning_configuration {
    scan_on_push = true # image scanning in the registry (in addition to Trivy in the pipeline)
  }
}

resource "aws_ecr_lifecycle_policy" "app" {
  repository = aws_ecr_repository.app.name

  policy = jsonencode({
    rules = [{
      rulePriority = 1
      description  = "Keep the 20 most recent images"
      selection = {
        tagStatus   = "any"
        countType   = "imageCountMoreThan"
        countNumber = 20
      }
      action = { type = "expire" }
    }]
  })
}
