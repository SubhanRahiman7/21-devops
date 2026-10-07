# Customer-managed key used to encrypt the artifacts bucket
resource "aws_kms_key" "artifacts" {
  description             = "${local.name} artifacts bucket key"
  enable_key_rotation     = true
  deletion_window_in_days = 7
}

resource "aws_kms_alias" "artifacts" {
  name          = "alias/${local.name}-artifacts"
  target_key_id = aws_kms_key.artifacts.key_id
}
