variable "vpc_id" {
  type = string
}
variable "private_subnets" {
  type = list(string)
}
variable "app_name" {
  type    = string
  default = "astrovox-ai"
}
variable "environment" {
  type    = string
  default = "production"
}
variable "db_instance_class" {
  type    = string
  default = "db.t3.medium"
}
variable "db_engine_version" {
  type    = string
  default = "16.2"
}
variable "db_allocated_storage" {
  type    = number
  default = 100
}
variable "db_max_allocated_storage" {
  type    = number
  default = 1000
}
variable "replica_count" {
  type    = number
  default = 2
}
variable "multi_az" {
  type    = bool
  default = true
}
variable "backup_retention_period" {
  type    = number
  default = 30
}
variable "deletion_protection" {
  type    = bool
  default = true
}
