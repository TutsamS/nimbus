# Nimbus - AWS Cloud AI Agent
*AI-Powered Cloud Management CLI*

Manage your AWS resources through natural language instead of the AWS console.

## Tech Stack

- **LangChain** -- connects the LLM to AWS tools so it can reason about which action to take
- **OpenAI GPT-3.5-turbo** -- natural language understanding
- **Boto3** -- AWS SDK for Python
- **Docker** -- containerized deployment

## Current Features

**S3 (read + write):**
- List all S3 buckets
- List objects inside a bucket
- Get bucket size via CloudWatch
- Create a new bucket
- Upload text content to a bucket
- Delete an object from a bucket
- Delete a bucket and all its contents

**EC2 (read-only):**
- List all EC2 instances
- Get detailed info on a specific instance (AMI, IPs, security groups, etc.)

**Safety:**
- Destructive actions (delete bucket, delete object) require explicit y/n confirmation before execution

## Prerequisites

- Python 3.11+
- OpenAI API key
- AWS credentials (Access Key ID + Secret Access Key)
- Docker (optional, for containerized usage)

## Setup

```bash
cd AWS_AI_Agent
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Copy the example env file and fill in your credentials:

```bash
cp .env.example .env
```

Run the agent:

```bash
python src/main.py
```

## Usage Examples

```
You: List my S3 buckets
You: What's inside my-app-data bucket?
You: Create a bucket called my-new-project
You: Upload a file called notes.txt with "hello world" to my-new-project
You: Delete the bucket my-new-project   --> triggers y/n confirmation
You: Show me my EC2 instances
```

## Docker Usage

Build the image:

```bash
docker build -t aws-agent .
```

Run the container:

```bash
docker run --env-file .env -it aws-agent
```

## Project Structure

```
AWS_AI_Agent/
├── src/
│   ├── main.py       # CLI entry point and interactive loop
│   ├── agent.py      # LangChain ReAct agent with confirmation guards
│   ├── tools.py      # AWS tool definitions (S3, EC2, CloudWatch)
│   └── safety.py     # Confirmation layer for destructive actions
├── requirements.txt
├── Dockerfile
├── .env.example
└── README.md
```

---

Made by Tutsam Singh
