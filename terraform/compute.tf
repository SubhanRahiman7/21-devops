# Latest Amazon Linux 2023 AMI (only looked up when no ami_id is given)
data "aws_ami" "al2023" {
  count       = var.ami_id == "" ? 1 : 0
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["al2023-ami-2023*-x86_64"]
  }
}

locals {
  ami_id = var.ami_id != "" ? var.ami_id : data.aws_ami.al2023[0].id
}

resource "aws_instance" "app" {
  ami                    = local.ami_id
  instance_type          = var.instance_type
  subnet_id              = aws_subnet.public.id
  vpc_security_group_ids = [aws_security_group.app.id]
  iam_instance_profile   = aws_iam_instance_profile.host.name

  associate_public_ip_address = true # public web server; set per instance instead of per subnet

  metadata_options {
    http_tokens = "required" # IMDSv2 only
  }

  root_block_device {
    encrypted   = true
    volume_size = 12
  }

  user_data = templatefile("${path.module}/user_data.sh.tftpl", {
    region   = var.aws_region
    registry = split("/", aws_ecr_repository.app.repository_url)[0]
    image    = "${aws_ecr_repository.app.repository_url}:${var.app_image_tag}"
  })

  # the route to the Internet Gateway must exist before the instance boots
  depends_on = [aws_route_table_association.public]

  tags = { Name = "${local.name}-app" }
}
