resource "aws_cloudwatch_log_group" "app" {
  name              = "/ecs/${var.projeto}-app"
  retention_in_days = 7
}

resource "aws_ecs_cluster" "principal" {
  name = "${var.projeto}-cluster"
}

locals {
  segredo_app   = aws_secretsmanager_secret.app.arn
  segredo_banco = aws_db_instance.principal.master_user_secret[0].secret_arn
}

resource "aws_ecs_task_definition" "app" {
  family                   = "${var.projeto}-app"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = 2048
  memory                   = 8192
  execution_role_arn       = aws_iam_role.execucao.arn
  task_role_arn            = aws_iam_role.tarefa.arn

  runtime_platform {
    operating_system_family = "LINUX"
    cpu_architecture        = "X86_64"
  }

  container_definitions = jsonencode([{
    name      = "app"
    image     = "${aws_ecr_repository.app.repository_url}:${var.versao_imagem}"
    essential = true
    portMappings = [{
      containerPort = 8000
      protocol      = "tcp"
    }]
    environment = [
      { name = "POSTGRES_HOST", value = aws_db_instance.principal.address },
      { name = "POSTGRES_PORT", value = tostring(aws_db_instance.principal.port) },
      { name = "POSTGRES_DB", value = aws_db_instance.principal.db_name },
      { name = "LANGSMITH_TRACING", value = "true" },
      { name = "LANGSMITH_PROJECT", value = "agente-suporte-aws" },
      { name = "PROMPT_GUARD_ATIVO", value = "true" },
      { name = "DEMO_PUBLICA", value = "true" },
      { name = "DOCS_ATIVO", value = "false" },
      { name = "LIMITE_POR_MINUTO", value = "5" },
      { name = "LIMITE_DIARIO_MENSAGENS", value = "200" },
    ]
    secrets = [
      { name = "POSTGRES_USER", valueFrom = "${local.segredo_banco}:username::" },
      { name = "POSTGRES_PASSWORD", valueFrom = "${local.segredo_banco}:password::" },
      { name = "GOOGLE_API_KEY", valueFrom = "${local.segredo_app}:GOOGLE_API_KEY::" },
      { name = "LANGSMITH_API_KEY", valueFrom = "${local.segredo_app}:LANGSMITH_API_KEY::" },
      { name = "HF_TOKEN", valueFrom = "${local.segredo_app}:HF_TOKEN::" },
      { name = "API_KEY", valueFrom = "${local.segredo_app}:API_KEY::" },
    ]
    logConfiguration = {
      logDriver = "awslogs"
      options = {
        awslogs-group         = aws_cloudwatch_log_group.app.name
        awslogs-region        = var.regiao
        awslogs-stream-prefix = "app"
      }
    }
  }])
}

resource "aws_ecs_service" "app" {
  name                              = "${var.projeto}-app"
  cluster                           = aws_ecs_cluster.principal.id
  task_definition                   = aws_ecs_task_definition.app.arn
  desired_count                     = var.tarefas
  launch_type                       = "FARGATE"
  enable_execute_command            = true
  health_check_grace_period_seconds = 900

  network_configuration {
    subnets          = aws_subnet.publica[*].id
    security_groups  = [aws_security_group.app.id]
    assign_public_ip = true
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.app.arn
    container_name   = "app"
    container_port   = 8000
  }

  deployment_circuit_breaker {
    enable   = true
    rollback = true
  }

  depends_on = [aws_lb_listener.http]
}
