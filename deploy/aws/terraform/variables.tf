variable "region" {
  type    = string
  default = "us-east-1"
}

variable "project" {
  type    = string
  default = "repomind"
}

variable "backend_image" {
  type        = string
  description = "Published backend container image."
}

variable "frontend_image" {
  type        = string
  description = "Published frontend container image."
}

variable "repomind_api_key" {
  type      = string
  sensitive = true
}

variable "postgres_password" {
  type      = string
  sensitive = true
}
