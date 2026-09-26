variable "vpc_id" {}
variable "app_name" {
  default = "astrovox-ai"
}
variable "public_subnets" {
  type = list(string)
}
