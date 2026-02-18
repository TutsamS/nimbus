#!/usr/bin/env python3
"""
Main entry point for the AWS Resource Management Agent CLI.
"""

import os
from dotenv import load_dotenv
from agent import AWSAgent


def main():
    """Run the interactive CLI loop.

    Loads credentials from .env, initializes the agent, then enters a
    read-eval-print loop. Destructive actions trigger a y/n confirmation
    prompt before execution.
    """

    load_dotenv()

    if not os.getenv("OPENAI_API_KEY"):
        print("Error: OPENAI_API_KEY not found in .env file")
        return

    if not os.getenv("AWS_ACCESS_KEY_ID") or not os.getenv("AWS_SECRET_ACCESS_KEY"):
        print("Error: AWS credentials not found in .env file")
        return

    print("\n" + "=" * 60)
    print("  Nimbus -- AWS Resource Manager")
    print("  AI-Powered Cloud Management CLI")
    print("=" * 60)
    print("\nI can help you manage your AWS resources.")
    print("Type 'exit' or 'quit' to leave.\n")

    agent = AWSAgent()

    while True:
        try:
            user_input = input("You: ").strip()

            if not user_input:
                continue

            if user_input.lower() in ("exit", "quit"):
                print("\nGoodbye!")
                break

            response = agent.process_request(user_input)

            # If the agent tried to call a destructive tool, prompt for y/n
            if response.needs_confirmation:
                print(f"\nAgent: {response.message}")
                confirm = input(f"\n{response.confirmation_prompt}").strip().lower()
                if confirm in ("y", "yes"):
                    result = agent.confirm_and_execute()
                    print(f"\nAgent: {result}\n")
                else:
                    print("\nAgent: Action cancelled.\n")
            else:
                print(f"\nAgent: {response.message}\n")

        except (KeyboardInterrupt, EOFError):
            print("\n\nGoodbye!")
            break
        except Exception as e:
            print(f"\nError: {str(e)}\n")


if __name__ == "__main__":
    main()
