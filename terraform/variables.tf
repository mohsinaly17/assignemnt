variable "aws_region" {
  description = "AWS region to deploy into"
  type        = string
  default     = "us-east-1"
}

variable "instance_type" {
  description = "EC2 instance type (free tier eligible)"
  type        = string
  default     = "t2.micro"
}

variable "key_name" {
  description = "Name of the existing AWS key pair to use for SSH access"
  type        = string
}

variable "public_key_path" {
  description = "Path to your local public SSH key (.pub file)"
  type        = string
  default     = "~/.ssh/id_rsa.pub"
}

variable "app_port" {
  description = "Port the containerized app listens on inside the server"
  type        = number
  default     = 5000
}

variable "allowed_ssh_cidr" {
  description = "CIDR block allowed to SSH into the instance (restrict this to your own IP in production)"
  type        = string
  default     = "0.0.0.0/0"
}
