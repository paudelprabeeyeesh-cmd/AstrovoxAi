variable "vpc_id" {}
variable "app_name" {
  default = "astrovox-ai"
}
variable "private_subnets" {
  type = list(string)
}
