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

output "db_subnet_group" {
  value = aws_db_subnet_group.main.name
}

output "security_group_id" {
  value = aws_security_group.rds.id
}
