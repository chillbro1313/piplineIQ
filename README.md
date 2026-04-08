PipelineIQ 
A CI/CD Pipeline Monitoring Dashboard built with Django and vanilla JavaScript.
PipelineIQ allows developers to visualize and monitor their CI/CD pipelines in real time.


 Tech Stack

| Technology | Purpose |
|---|---|
| Django | Backend framework |
| Vanilla JavaScript | Frontend dashboard |
| SQLite | Database |
| Docker | Containerization |
| AWS EC2 | Cloud server |
| AWS VPC | Private network |
| AWS Elastic IP | Permanent IP address |
| Terraform | Infrastructure as Code |
| GitHub Actions | CI/CD pipeline |

Architecture

Internet
↓
Elastic IP (permanent - 184.73.39.180)
↓
Internet Gateway
↓
VPC (private network - 10.0.0.0/16)
↓
Public Subnet (10.0.1.0/24)
↓
Security Group (port 22 + port 8000)
↓
EC2 Ubuntu 22.04 (t2.micro)
↓
PipelineIQ Dashboard 

Run Locally
With Docker:

bash
git clone https://github.com/chillbro1313/piplineIQ.git
cd piplineIQ
docker build -t pipelineiq .
docker run -p 8000:8000 pipelineiq

Open: `http://localhost:8000`

Without Docker:
bash
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver


 Deploy on AWS with Terraform
Clone the repository
git clone https://github.com/chillbro1313/piplineIQ.git
cd piplineIQ/terraform


Initialize Terraform
terraform init

Preview infrastructure
terraform plan

Deploy to AWS
terraform apply

Author
Mohamed Amine Belkhiri
 GitHub: [@chillbro1313](https://github.com/chillbro1313)
 LinkedIn: [https://www.linkedin.com/in/mohamed-amine-belkhiri-454b4a249?utm_source=share_via&utm_content=profile&utm_medium=member_android]
  Email: belkhirimohamed664@gmail.com





