variable "regiao" {
  type    = string
  default = "us-east-1"
}

variable "projeto" {
  type    = string
  default = "novabyte"
}

variable "cidr_vpc" {
  type    = string
  default = "10.0.0.0/16"
}

variable "versao_imagem" {
  type    = string
  default = "v1"
}

variable "tarefas" {
  type    = number
  default = 1
}
