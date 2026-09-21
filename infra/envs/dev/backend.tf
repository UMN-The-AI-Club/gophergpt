terraform {
  backend "s3" {
    bucket         = "university-chatbot-tf-state-446394401845"
    key            = "envs/dev/terraform.tfstate"
    region         = "us-east-1"
    dynamodb_table = "university-chatbot-tf-locks"
    encrypt        = true
  }
}