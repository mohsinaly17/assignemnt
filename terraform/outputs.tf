output "instance_public_ip" {
  description = "Public IP address of the deployed EC2 instance"
  value       = aws_instance.app_server.public_ip
}

output "instance_id" {
  description = "ID of the deployed EC2 instance"
  value       = aws_instance.app_server.id
}

output "ssh_command" {
  description = "Convenience SSH command to connect to the instance"
  value       = "ssh -i ~/.ssh/id_rsa ubuntu@${aws_instance.app_server.public_ip}"
}
