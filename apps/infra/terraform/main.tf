# Mental Health Practice Management System Infrastructure
# HIPAA-compliant infrastructure configuration

terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "Mental Health PMS"
      Environment = var.environment
      ManagedBy   = "Terraform"
      Compliance  = "HIPAA"
    }
  }
}

# Variables
variable "aws_region" {
  description = "AWS region for resources"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "Environment must be dev, staging, or prod."
  }
}

variable "project_name" {
  description = "Project name for resource naming"
  type        = string
  default     = "mental-health-pms"
}

# Data sources
data "aws_availability_zones" "available" {
  state = "available"
}

# VPC for secure networking
resource "aws_vpc" "main" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = {
    Name = "${var.project_name}-${var.environment}-vpc"
  }
}

# Private subnets for Redis
resource "aws_subnet" "private" {
  count             = 2
  vpc_id            = aws_vpc.main.id
  cidr_block        = "10.0.${count.index + 1}.0/24"
  availability_zone = data.aws_availability_zones.available.names[count.index]

  tags = {
    Name = "${var.project_name}-${var.environment}-private-${count.index + 1}"
  }
}

# Redis subnet group
resource "aws_elasticache_subnet_group" "redis" {
  name       = "${var.project_name}-${var.environment}-redis-subnet-group"
  subnet_ids = aws_subnet.private[*].id

  tags = {
    Name = "${var.project_name}-${var.environment}-redis-subnet-group"
  }
}

# Security group for Redis
resource "aws_security_group" "redis" {
  name_prefix = "${var.project_name}-${var.environment}-redis-"
  vpc_id      = aws_vpc.main.id

  ingress {
    from_port   = 6379
    to_port     = 6379
    protocol    = "tcp"
    cidr_blocks = [aws_vpc.main.cidr_block]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.project_name}-${var.environment}-redis-sg"
  }
}

# Redis cluster for event bus
resource "aws_elasticache_replication_group" "redis" {
  replication_group_id         = "${var.project_name}-${var.environment}-redis"
  description                  = "Redis cluster for event bus"

  node_type                    = var.environment == "prod" ? "cache.r6g.large" : "cache.t3.micro"
  port                         = 6379
  parameter_group_name         = "default.redis7"

  num_cache_clusters           = var.environment == "prod" ? 3 : 1

  subnet_group_name            = aws_elasticache_subnet_group.redis.name
  security_group_ids           = [aws_security_group.redis.id]

  at_rest_encryption_enabled   = true
  transit_encryption_enabled   = true
  auth_token                   = var.redis_auth_token

  automatic_failover_enabled   = var.environment == "prod" ? true : false
  multi_az_enabled            = var.environment == "prod" ? true : false

  log_delivery_configuration {
    destination      = aws_cloudwatch_log_group.redis.name
    destination_type = "cloudwatch-logs"
    log_format       = "json"
    log_type         = "slow-log"
  }

  tags = {
    Name = "${var.project_name}-${var.environment}-redis"
  }
}

# CloudWatch log group for Redis
resource "aws_cloudwatch_log_group" "redis" {
  name              = "/aws/elasticache/${var.project_name}-${var.environment}-redis"
  retention_in_days = var.environment == "prod" ? 90 : 7

  tags = {
    Name = "${var.project_name}-${var.environment}-redis-logs"
  }
}

# S3 bucket for analytics data
resource "aws_s3_bucket" "analytics" {
  bucket = "${var.project_name}-${var.environment}-analytics-data"

  tags = {
    Name        = "${var.project_name}-${var.environment}-analytics-data"
    Purpose     = "ETL Pipeline Data Storage"
    DataClass   = "Analytics"
  }
}

# S3 bucket versioning
resource "aws_s3_bucket_versioning" "analytics" {
  bucket = aws_s3_bucket.analytics.id
  versioning_configuration {
    status = "Enabled"
  }
}

# S3 bucket encryption
resource "aws_s3_bucket_server_side_encryption_configuration" "analytics" {
  bucket = aws_s3_bucket.analytics.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
    bucket_key_enabled = true
  }
}

# S3 bucket public access block
resource "aws_s3_bucket_public_access_block" "analytics" {
  bucket = aws_s3_bucket.analytics.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# S3 bucket lifecycle configuration
resource "aws_s3_bucket_lifecycle_configuration" "analytics" {
  bucket = aws_s3_bucket.analytics.id

  rule {
    id     = "analytics_data_lifecycle"
    status = "Enabled"

    transition {
      days          = 30
      storage_class = "STANDARD_IA"
    }

    transition {
      days          = 90
      storage_class = "GLACIER"
    }

    transition {
      days          = 365
      storage_class = "DEEP_ARCHIVE"
    }

    expiration {
      days = var.environment == "prod" ? 2555 : 365  # 7 years for prod, 1 year for dev/staging
    }
  }
}

# IAM role for ETL pipeline
resource "aws_iam_role" "etl_pipeline" {
  name = "${var.project_name}-${var.environment}-etl-pipeline-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ec2.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Name = "${var.project_name}-${var.environment}-etl-pipeline-role"
  }
}

# IAM policy for S3 access
resource "aws_iam_role_policy" "etl_s3_access" {
  name = "${var.project_name}-${var.environment}-etl-s3-policy"
  role = aws_iam_role.etl_pipeline.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject",
          "s3:ListBucket"
        ]
        Resource = [
          aws_s3_bucket.analytics.arn,
          "${aws_s3_bucket.analytics.arn}/*"
        ]
      }
    ]
  })
}

# Additional variables
variable "redis_auth_token" {
  description = "Redis authentication token"
  type        = string
  sensitive   = true
  default     = null
}

# Outputs
output "environment" {
  description = "Environment name"
  value       = var.environment
}

output "aws_region" {
  description = "AWS region"
  value       = var.aws_region
}

output "redis_endpoint" {
  description = "Redis cluster endpoint"
  value       = aws_elasticache_replication_group.redis.primary_endpoint_address
  sensitive   = true
}

output "redis_port" {
  description = "Redis cluster port"
  value       = aws_elasticache_replication_group.redis.port
}

output "s3_bucket_name" {
  description = "S3 bucket name for analytics data"
  value       = aws_s3_bucket.analytics.bucket
}

output "s3_bucket_arn" {
  description = "S3 bucket ARN for analytics data"
  value       = aws_s3_bucket.analytics.arn
}

output "etl_role_arn" {
  description = "IAM role ARN for ETL pipeline"
  value       = aws_iam_role.etl_pipeline.arn
}

output "vpc_id" {
  description = "VPC ID"
  value       = aws_vpc.main.id
}

output "private_subnet_ids" {
  description = "Private subnet IDs"
  value       = aws_subnet.private[*].id
}


output "region" {
  description = "AWS region"
  value       = var.aws_region
}
