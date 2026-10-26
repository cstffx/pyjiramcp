PyJiraMCP - Jira CLI sin deps

Python 3.7+. Sin dependencias externas.

Setup

cp config.toml.example config.toml
Edita: server, email, token

Comandos

get CRM-4017
create --project CRM --summary "txt"
update CRM-4017 --summary "txt" --status "In Progress"
search --jql "project=CRM AND status=Open"
transitions CRM-4017

Archivos

jira_client.py - core
mcp_server.py - MCP server
cli.py - CLI
config.toml.example - config template
MCP_SETUP.md - MCP config

Código

from jira_client import JiraClient
c = JiraClient()
c.get_issue('CRM-4017')
