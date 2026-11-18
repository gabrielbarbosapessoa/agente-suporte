data "aws_iam_policy_document" "assumir_ecs" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["ecs-tasks.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "execucao" {
  name               = "${var.projeto}-ecs-execucao"
  assume_role_policy = data.aws_iam_policy_document.assumir_ecs.json
}

resource "aws_iam_role_policy_attachment" "execucao_padrao" {
  role       = aws_iam_role.execucao.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

data "aws_iam_policy_document" "ler_segredos" {
  statement {
    actions = ["secretsmanager:GetSecretValue"]
    resources = [
      aws_secretsmanager_secret.app.arn,
      aws_db_instance.principal.master_user_secret[0].secret_arn,
    ]
  }
}

resource "aws_iam_role_policy" "execucao_segredos" {
  name   = "ler-segredos"
  role   = aws_iam_role.execucao.id
  policy = data.aws_iam_policy_document.ler_segredos.json
}

resource "aws_iam_role" "tarefa" {
  name               = "${var.projeto}-ecs-tarefa"
  assume_role_policy = data.aws_iam_policy_document.assumir_ecs.json
}

data "aws_iam_policy_document" "ecs_exec" {
  statement {
    actions = [
      "ssmmessages:CreateControlChannel",
      "ssmmessages:CreateDataChannel",
      "ssmmessages:OpenControlChannel",
      "ssmmessages:OpenDataChannel",
    ]
    resources = ["*"]
  }
}

resource "aws_iam_role_policy" "tarefa_exec" {
  name   = "ecs-exec"
  role   = aws_iam_role.tarefa.id
  policy = data.aws_iam_policy_document.ecs_exec.json
}
