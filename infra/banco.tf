resource "aws_db_subnet_group" "banco" {
  name       = "${var.projeto}-banco"
  subnet_ids = aws_subnet.banco[*].id
}

resource "aws_db_instance" "principal" {
  identifier                  = "${var.projeto}-db"
  engine                      = "postgres"
  engine_version              = "17"
  instance_class              = "db.t4g.micro"
  allocated_storage           = 20
  storage_type                = "gp3"
  storage_encrypted           = true
  db_name                     = "novabyte"
  username                    = "novabyte"
  manage_master_user_password = true
  db_subnet_group_name        = aws_db_subnet_group.banco.name
  vpc_security_group_ids      = [aws_security_group.banco.id]
  publicly_accessible         = false
  multi_az                    = false
  backup_retention_period     = 0
  skip_final_snapshot         = true
  deletion_protection         = false
  apply_immediately           = true
}
