variable "vpc_id" {}
variable "private_subnets" {
  type = list(string)
}
variable "app_name" {
  default = "astrovox-ai"
}
variable "environment" {
  default = "production"
}
variable "db_instance_class" {
  default = "db.t3.medium"
}
variable "db_engine_version" {
  default = "16.2"
}
variable "db_allocated_storage" {
  default = 100
}
variable "db_max_allocated_storage" {
  default = 1000
}
variable "replica_count" {
  default = 2
}
variable "multi_az" {
  default = true
}
variable "backup_retention_period" {
  default = 30
}
variable "deletion_protection" {
  default = true
}

resource "aws_db_subnet_group" "main" {
  name       = "${var.app_name}-db-subnet"
  subnet_ids = var.private_subnets

  tags = {
    Name = "${var.app_name}-db-subnet-group"
  }
}

resource "random_password" "db_password" {
  length  = 32
  special = false
}

resource "aws_db_instance" "postgres" {
  identifier     = "${var.app_name}-db"
  engine         = "postgres"
  engine_version = var.db_engine_version
  instance_class = var.db_instance_class

  allocated_storage     = var.db_allocated_storage
  max_allocated_storage = var.db_max_allocated_storage
  storage_type          = "gp3"
  storage_encrypted     = true

  db_name  = "astrovox"
  username = "astrovox"
  password = random_password.db_password.result

  vpc_security_group_ids    = [aws_security_group.rds.id]
  db_subnet_group_name      = aws_db_subnet_group.main.name
  publicly_accessible       = false
  multi_az                  = var.multi_az
  backup_retention_period   = var.backup_retention_period
  backup_window             = "03:00-04:00"
  maintenance_window        = "sun:04:00-sun:05:00"
  skip_final_snapshot       = false
  final_snapshot_identifier = "${var.app_name}-db-final-snapshot"
  deletion_protection       = var.deletion_protection

  enabled_cloudwatch_logs_exports = ["postgresql", "upgrade"]

  tags = {
    Name        = "${var.app_name}-postgres"
    Environment = var.environment
  }
}

resource "aws_db_instance" "postgres_replica" {
  count = var.replica_count

  identifier         = "${var.app_name}-db-replica-${count.index + 1}"
  engine             = "postgres"
  engine_version     = var.db_engine_version
  instance_class     = var.db_instance_class
  replicate_source_db = aws_db_instance.postgres.arn

  publicly_accessible = false
  skip_final_snapshot = true

  vpc_security_group_ids    = [aws_security_group.rds.id]
  db_subnet_group_name      = aws_db_subnet_group.main.name
  backup_retention_period   = 0
  maintenance_window        = "sun:04:00-sun:05:00"

  tags = {
    Name        = "${var.app_name}-postgres-replica-${count.index + 1}"
    Environment = var.environment
  }
}

resource "aws_security_group" "rds" {
  name_prefix = "${var.app_name}-rds-"
  vpc_id      = var.vpc_id

  ingress {
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.app.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.app_name}-rds-sg"
  }
}

resource "aws_security_group" "app" {
  name_prefix = "${var.app_name}-app-"
  vpc_id      = var.vpc_id

  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    from_port   = 8000
    to_port     = 8000
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.app_name}-app-sg"
  }
}

output "endpoint" {
  value = aws_db_instance.postgres.endpoint
}

output "replica_endpoints" {
  value = aws_db_instance.postgres_replica[*].endpoint
}

output "password" {
  value     = random_password.db_password.result
  sensitive = true
}
