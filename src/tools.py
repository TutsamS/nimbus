"""
AWS Tools for the agent to interact with AWS services.
"""

import os
import re
import boto3
from langchain.tools import Tool
from botocore.exceptions import ClientError


class AWSToolkit:
    """Toolkit for AWS operations.

    Creates a single boto3 Session from environment variables and derives
    all service clients from it, avoiding repeated credential passing.
    """

    def __init__(self):
        """Initialize a shared AWS session and create service clients."""
        self.session = boto3.Session(
            region_name=os.getenv("AWS_REGION", "us-east-2"),
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
        )
        self.region = self.session.region_name
        self.s3_client = self.session.client("s3")
        self.ec2_client = self.session.client("ec2")
        self.cloudwatch_client = self.session.client("cloudwatch")

    # ------------------------------------------------------------------
    # S3 Read Tools
    # ------------------------------------------------------------------

    def list_s3_buckets(self, _input: str = "") -> str:
        """Fetch and return the names of all S3 buckets in the account."""
        try:
            response = self.s3_client.list_buckets()
            buckets = response.get("Buckets", [])

            if not buckets:
                return "You don't have any S3 buckets."

            bucket_list = "\n".join([f"  - {b['Name']}" for b in buckets])
            return f"Your S3 buckets:\n{bucket_list}"

        except ClientError as e:
            return f"Error listing S3 buckets: {str(e)}"

    def list_s3_objects(self, bucket_name: str) -> str:
        """List every object inside a bucket with human-readable file sizes."""
        try:
            bucket_name = bucket_name.strip()
            response = self.s3_client.list_objects_v2(Bucket=bucket_name)
            objects = response.get("Contents", [])

            if not objects:
                return f"Bucket '{bucket_name}' is empty."

            def format_size(size_bytes: int) -> str:
                if size_bytes < 1024:
                    return f"{size_bytes} B"
                elif size_bytes < 1024 ** 2:
                    return f"{size_bytes / 1024:.1f} KB"
                elif size_bytes < 1024 ** 3:
                    return f"{size_bytes / 1024 ** 2:.1f} MB"
                return f"{size_bytes / 1024 ** 3:.2f} GB"

            obj_list = "\n".join([
                f"  - {obj['Key']} ({format_size(obj['Size'])})"
                for obj in objects
            ])
            return f"Objects in '{bucket_name}' ({len(objects)} total):\n{obj_list}"

        except ClientError as e:
            return f"Error listing objects in '{bucket_name}': {str(e)}"

    def get_s3_bucket_size(self, bucket_name: str) -> str:
        """Query CloudWatch for the total storage size of a bucket.

        Note: CloudWatch metrics can take up to 48 hours to appear for
        newly created buckets.
        """
        try:
            bucket_name = bucket_name.strip()
            response = self.cloudwatch_client.get_metric_statistics(
                Namespace="AWS/S3",
                MetricName="BucketSizeBytes",
                Dimensions=[
                    {"Name": "BucketName", "Value": bucket_name},
                    {"Name": "StorageType", "Value": "StandardStorage"},
                ],
                StartTime="2024-01-01T00:00:00Z",
                EndTime="2027-12-31T23:59:59Z",
                Period=86400,
                Statistics=["Average"],
            )

            if response["Datapoints"]:
                size_bytes = response["Datapoints"][-1]["Average"]
                size_gb = size_bytes / (1024 ** 3)
                return f"Bucket '{bucket_name}' size: {size_gb:.2f} GB"

            return f"Could not retrieve size for bucket '{bucket_name}'. CloudWatch metrics may take up to 48 hours to populate for new buckets."

        except ClientError as e:
            return f"Error getting bucket size: {str(e)}"

    # ------------------------------------------------------------------
    # S3 Write Tools
    # ------------------------------------------------------------------

    def create_s3_bucket(self, bucket_name: str) -> str:
        """Validate the bucket name against AWS naming rules, then create it
        in the configured region.
        """
        try:
            bucket_name = bucket_name.strip().lower()

            if not re.match(r"^[a-z0-9][a-z0-9.\-]{1,61}[a-z0-9]$", bucket_name):
                return (
                    f"Invalid bucket name '{bucket_name}'. "
                    "Bucket names must be 3-63 characters, lowercase, and can only "
                    "contain letters, numbers, hyphens, and periods."
                )

            self.s3_client.create_bucket(
                Bucket=bucket_name,
                CreateBucketConfiguration={"LocationConstraint": self.region},
            )
            return f"Successfully created bucket '{bucket_name}' in {self.region}."

        except ClientError as e:
            return f"Error creating bucket '{bucket_name}': {str(e)}"

    def delete_s3_bucket(self, bucket_name: str) -> str:
        """Empty all objects from the bucket first (AWS requires this),
        then delete the bucket itself.
        """
        try:
            bucket_name = bucket_name.strip()

            # S3 won't delete a non-empty bucket, so remove all objects first
            objects = self.s3_client.list_objects_v2(Bucket=bucket_name)
            if "Contents" in objects:
                delete_keys = [{"Key": obj["Key"]} for obj in objects["Contents"]]
                self.s3_client.delete_objects(
                    Bucket=bucket_name,
                    Delete={"Objects": delete_keys},
                )

            self.s3_client.delete_bucket(Bucket=bucket_name)
            return f"Successfully deleted bucket '{bucket_name}' and all its contents."

        except ClientError as e:
            return f"Error deleting bucket '{bucket_name}': {str(e)}"

    def upload_to_s3(self, input_str: str) -> str:
        """Parse a colon-delimited string (bucket:key:content) and upload
        the content as a UTF-8 encoded object to S3.
        """
        try:
            parts = input_str.split(":", 2)
            if len(parts) < 3:
                return "Invalid input. Format must be 'bucket_name:key:content'."

            bucket_name = parts[0].strip()
            key = parts[1].strip()
            content = parts[2]

            self.s3_client.put_object(
                Bucket=bucket_name,
                Key=key,
                Body=content.encode("utf-8"),
            )
            return f"Successfully uploaded '{key}' to bucket '{bucket_name}'."

        except ClientError as e:
            return f"Error uploading to S3: {str(e)}"

    def delete_s3_object(self, input_str: str) -> str:
        """Parse a colon-delimited string (bucket:key) and delete the
        specified object from S3.
        """
        try:
            parts = input_str.split(":", 1)
            if len(parts) < 2:
                return "Invalid input. Format must be 'bucket_name:object_key'."

            bucket_name = parts[0].strip()
            object_key = parts[1].strip()

            self.s3_client.delete_object(Bucket=bucket_name, Key=object_key)
            return f"Successfully deleted '{object_key}' from bucket '{bucket_name}'."

        except ClientError as e:
            return f"Error deleting object: {str(e)}"

    # ------------------------------------------------------------------
    # EC2 Tools
    # ------------------------------------------------------------------

    def list_ec2_instances(self, _input: str = "") -> str:
        """Retrieve all EC2 instances across reservations and return a
        summary with instance ID, type, state, and Name tag.
        """
        try:
            response = self.ec2_client.describe_instances()
            instances = []

            for reservation in response["Reservations"]:
                for instance in reservation["Instances"]:
                    name = ""
                    for tag in instance.get("Tags", []):
                        if tag["Key"] == "Name":
                            name = tag["Value"]
                            break
                    instances.append({
                        "id": instance["InstanceId"],
                        "state": instance["State"]["Name"],
                        "type": instance["InstanceType"],
                        "name": name,
                    })

            if not instances:
                return "You don't have any EC2 instances."

            instance_list = "\n".join([
                f"  - {i['id']} ({i['type']}) - State: {i['state']}"
                + (f" - Name: {i['name']}" if i["name"] else "")
                for i in instances
            ])
            return f"Your EC2 instances:\n{instance_list}"

        except ClientError as e:
            return f"Error listing EC2 instances: {str(e)}"

    def describe_ec2_instance(self, instance_id: str) -> str:
        """Fetch detailed metadata for a single EC2 instance: AMI, launch
        time, public/private IPs, availability zone, and security groups.
        """
        try:
            instance_id = instance_id.strip()
            response = self.ec2_client.describe_instances(InstanceIds=[instance_id])

            reservations = response.get("Reservations", [])
            if not reservations or not reservations[0].get("Instances"):
                return f"Instance '{instance_id}' not found."

            inst = reservations[0]["Instances"][0]

            name = ""
            for tag in inst.get("Tags", []):
                if tag["Key"] == "Name":
                    name = tag["Value"]
                    break

            sg_names = [sg["GroupName"] for sg in inst.get("SecurityGroups", [])]

            details = [
                f"Instance ID:      {inst['InstanceId']}",
                f"Name:             {name or '(none)'}",
                f"State:            {inst['State']['Name']}",
                f"Type:             {inst['InstanceType']}",
                f"AMI:              {inst.get('ImageId', 'N/A')}",
                f"Launch Time:      {inst.get('LaunchTime', 'N/A')}",
                f"Availability Zone: {inst.get('Placement', {}).get('AvailabilityZone', 'N/A')}",
                f"Public IP:        {inst.get('PublicIpAddress', 'None')}",
                f"Private IP:       {inst.get('PrivateIpAddress', 'None')}",
                f"Security Groups:  {', '.join(sg_names) if sg_names else 'None'}",
            ]
            return "\n".join(details)

        except ClientError as e:
            return f"Error describing instance '{instance_id}': {str(e)}"


# Tools that require user confirmation before execution
DESTRUCTIVE_TOOLS = {"delete_s3_bucket", "delete_s3_object"}


def get_aws_tools():
    """Instantiate the toolkit and register each method as a LangChain Tool
    with a description that guides the LLM on when and how to call it.
    """
    toolkit = AWSToolkit()

    tools = [
        Tool(
            name="list_s3_buckets",
            func=toolkit.list_s3_buckets,
            description=(
                "List all S3 buckets in the AWS account. Use this first when "
                "the user asks about their S3 buckets or storage. Input should "
                "be an empty string."
            ),
        ),
        Tool(
            name="list_s3_objects",
            func=toolkit.list_s3_objects,
            description=(
                "List all objects inside a specific S3 bucket. Input must be the "
                "exact bucket name, e.g. 'my-bucket-name'."
            ),
        ),
        Tool(
            name="get_s3_bucket_size",
            func=toolkit.get_s3_bucket_size,
            description=(
                "Get the total size of a specific S3 bucket via CloudWatch metrics. "
                "Input must be the exact bucket name, e.g. 'my-bucket-name'."
            ),
        ),
        Tool(
            name="create_s3_bucket",
            func=toolkit.create_s3_bucket,
            description=(
                "Create a new S3 bucket. Input must be the desired bucket name. "
                "Bucket names must be globally unique, lowercase, 3-63 characters."
            ),
        ),
        Tool(
            name="delete_s3_bucket",
            func=toolkit.delete_s3_bucket,
            description=(
                "Delete an S3 bucket and all its contents. This is destructive and "
                "cannot be undone. Input must be the exact bucket name."
            ),
        ),
        Tool(
            name="upload_to_s3",
            func=toolkit.upload_to_s3,
            description=(
                "Upload text content to an S3 bucket. Input format must be "
                "'bucket_name:key:content', e.g. 'my-bucket:hello.txt:Hello World'."
            ),
        ),
        Tool(
            name="delete_s3_object",
            func=toolkit.delete_s3_object,
            description=(
                "Delete a specific object from an S3 bucket. This is destructive. "
                "Input format must be 'bucket_name:object_key', e.g. 'my-bucket:hello.txt'."
            ),
        ),
        Tool(
            name="list_ec2_instances",
            func=toolkit.list_ec2_instances,
            description=(
                "List all EC2 instances in the AWS account. Use this when the user "
                "asks about their EC2 instances, servers, or compute resources. "
                "Input should be an empty string."
            ),
        ),
        Tool(
            name="describe_ec2_instance",
            func=toolkit.describe_ec2_instance,
            description=(
                "Get detailed information about a specific EC2 instance including "
                "AMI, launch time, IPs, and security groups. Input must be the "
                "instance ID, e.g. 'i-0abc123def456'."
            ),
        ),
    ]

    return tools
