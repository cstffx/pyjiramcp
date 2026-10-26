#!/usr/bin/env python3


import json
import base64
import urllib.request
import urllib.parse
from typing import Optional, Dict, Any


class JiraClient:
    

    def __init__(self, config_path: str = "config.toml"):

        config = self._load_config(config_path)
        jira_cfg = config.get('jira', {})

        self.server = jira_cfg.get('server', '').rstrip('/')
        self.email = jira_cfg.get('email')
        self.token = jira_cfg.get('token')
        self.proxy = jira_cfg.get('proxy', '')

        if not all([self.server, self.email, self.token]):
            raise ValueError("Missing jira config: server, email, token")

        credentials = f"{self.email}:{self.token}".encode()
        self.auth_header = 'Basic ' + base64.b64encode(credentials).decode()

    @staticmethod
    def _load_config(path: str) -> dict:
        
        config = {}
        current_section = None

        try:
            with open(path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue

                    if line.startswith('[') and line.endswith(']'):
                        current_section = line[1:-1]
                        config[current_section] = {}
                    elif '=' in line and current_section:
                        key, value = line.split('=', 1)
                        key = key.strip()
                        value = value.strip().strip('"').strip("'")
                        config[current_section][key] = value
        except FileNotFoundError:
            raise FileNotFoundError(f"Config file not found: {path}")

        return config

    def _make_request(self, method: str, endpoint: str, data: Optional[Dict] = None) -> Dict[str, Any]:

        url = f"{self.server}/rest/api/3{endpoint}"

        headers = {
            'Authorization': self.auth_header,
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        }

        body = json.dumps(data).encode() if data else None

        try:
            req = urllib.request.Request(url, data=body, headers=headers, method=method)
            if self.proxy:
                proxy_handler = urllib.request.ProxyHandler({'http': self.proxy, 'https': self.proxy})
                opener = urllib.request.build_opener(proxy_handler)
                response = opener.open(req)
            else:
                response = urllib.request.urlopen(req)
            with response as r:
                response_data = r.read().decode()
                return json.loads(response_data) if response_data else {}

        except urllib.error.HTTPError as e:
            error_body = e.read().decode()
            try:
                error_json = json.loads(error_body)
                error_msg = error_json.get('errorMessages', [error_body])
                raise Exception(f"HTTP {e.code}: {error_msg}")
            except json.JSONDecodeError:
                raise Exception(f"HTTP {e.code}: {error_body}")

        except urllib.error.URLError as e:
            raise Exception(f"Connection error: {e}")

    def get_issue(self, issue_key: str) -> Dict[str, Any]:
        
        data = self._make_request('GET', f'/issues/{issue_key}')

        fields = data.get('fields', {})
        return {
            'key': data.get('key'),
            'summary': fields.get('summary'),
            'description': fields.get('description'),
            'status': fields.get('status', {}).get('name'),
            'type': fields.get('issuetype', {}).get('name'),
            'assignee': fields.get('assignee', {}).get('displayName'),
            'created': fields.get('created'),
            'updated': fields.get('updated'),
        }

    def create_issue(self, project: str, summary: str,
                    description: Optional[str] = None,
                    issue_type: str = 'Bug') -> str:
        
        payload = {
            'fields': {
                'project': {'key': project},
                'summary': summary,
                'issuetype': {'name': issue_type},
            }
        }

        if description:
            payload['fields']['description'] = description

        response = self._make_request('POST', '/issues', payload)
        return response.get('key', 'Unknown')

    def update_issue(self, issue_key: str, **fields) -> str:
        
        payload = {'fields': {}}

        field_map = {
            'summary': 'summary',
            'description': 'description',
            'status': 'status',
            'assignee': 'assignee',
        }

        for key, jira_key in field_map.items():
            if key in fields and fields[key]:
                value = fields[key]
                if jira_key == 'assignee':
                    payload['fields'][jira_key] = {'name': value}
                elif jira_key == 'status':
                    return self._transition_issue(issue_key, value)
                else:
                    payload['fields'][jira_key] = value

        if not payload['fields']:
            return f"No fields to update for {issue_key}"

        self._make_request('PUT', f'/issues/{issue_key}', payload)
        return f"Updated {issue_key}"

    def _transition_issue(self, issue_key: str, target_status: str) -> str:
        
        transitions = self._make_request('GET', f'/issues/{issue_key}/transitions')

        transition_id = None
        for t in transitions.get('transitions', []):
            if t.get('to', {}).get('name', '').lower() == target_status.lower():
                transition_id = t.get('id')
                break

        if not transition_id:
            return f"Status '{target_status}' not available for {issue_key}"

        payload = {'transition': {'id': transition_id}}
        self._make_request('POST', f'/issues/{issue_key}/transitions', payload)
        return f"Transitioned {issue_key} to {target_status}"

    def search_issues(self, jql: str, max_results: int = 10) -> list:
        """
        Buscar tickets usando JQL (Jira Query Language)

        Args:
            jql: Consulta JQL (ej: "project = CRM AND status = Open")
            max_results: Máximo número de resultados

        Returns:
            Lista de tickets encontrados
        
        Obtener transiciones disponibles para un ticket

        Args:
            issue_key: Clave del ticket

        Returns:
            Lista de transiciones disponibles
        """
        data = self._make_request('GET', f'/issues/{issue_key}/transitions')

        transitions = []
        for t in data.get('transitions', []):
            transitions.append({
                'id': t.get('id'),
                'name': t.get('name'),
                'to': t.get('to', {}).get('name'),
            })

        return transitions
