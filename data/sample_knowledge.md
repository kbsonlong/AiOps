# AiOps System Documentation

## Overview
This AiOps system is designed to monitor and remediate issues in IT operations using AI agents.

## Components
1. **Router**: Classifies queries and routes them to specialized agents.
2. **GitHub Agent**: Searches code and issues.
3. **Notion Agent**: Searches documentation.
4. **Slack Agent**: Searches discussions.

## Authentication
To authenticate API requests, use the `Authorization` header with a Bearer token.
Example: `Authorization: Bearer <token>`

## Deployment
The system is deployed using Docker containers.
Run `docker-compose up -d` to start the services.

## Troubleshooting
If the system is slow, check the Redis queue length.
If the database connection fails, verify the credentials in `.env`.
