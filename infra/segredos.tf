resource "aws_secretsmanager_secret" "app" {
  name                    = "${var.projeto}/app"
  description             = "Chaves da aplicacao: Gemini, LangSmith, Hugging Face e chave da API"
  recovery_window_in_days = 0
}
