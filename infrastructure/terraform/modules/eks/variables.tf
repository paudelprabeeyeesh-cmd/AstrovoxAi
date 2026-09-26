variable "vpc_id" {}
variable "private_subnets" {
  type = list(string)
}
variable "app_name" {
  default = "astrovox-ai"
}
variable "cluster_version" {
  default = "1.28"
}
