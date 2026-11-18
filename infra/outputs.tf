output "url" {
  value = "http://${aws_lb.principal.dns_name}"
}

output "ecr" {
  value = aws_ecr_repository.app.repository_url
}

output "segredo_app" {
  value = aws_secretsmanager_secret.app.name
}

output "cluster" {
  value = aws_ecs_cluster.principal.name
}

output "servico" {
  value = aws_ecs_service.app.name
}

output "logs" {
  value = aws_cloudwatch_log_group.app.name
}
