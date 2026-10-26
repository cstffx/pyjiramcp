#!/usr/bin/env python3


import sys
import json
from typing import Any, Dict, List
from jira_client import JiraClient


class MCPServer:
    

    def __init__(self, config_path: str = "config.toml"):
        self.client = JiraClient(config_path)
        self.request_id = 0

    def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        
        method = request.get('method')
        params = request.get('params', {})
        request_id = request.get('id')

        try:
            if method == 'initialize':
                result = self._handle_initialize()
            elif method == 'tools/list':
                result = self._handle_tools_list()
            elif method == 'tools/call':
                result = self._handle_tool_call(params)
            else:
                return self._error_response(request_id, f"Unknown method: {method}")

            return {
                'jsonrpc': '2.0',
                'id': request_id,
                'result': result
            }

        except Exception as e:
            return self._error_response(request_id, str(e))

    def _handle_initialize(self) -> Dict[str, Any]:
        
        return {
            'protocolVersion': '2024-11-05',
            'capabilities': {
                'tools': {}
            },
            'serverInfo': {
                'name': 'PyJiraMCP',
                'version': '1.0.0',
                'description': 'Cliente Jira sin dependencias para Claude'
            }
        }

    def _handle_tools_list(self) -> Dict[str, Any]:
        
        tools = [
            {
                'name': 'jira_get_issue',
                'description': 'Obtener detalles de un ticket Jira',
                'inputSchema': {
                    'type': 'object',
                    'properties': {
                        'issue_key': {
                            'type': 'string',
                            'description': 'Clave del ticket (ej: CRM-4017)'
                        }
                    },
                    'required': ['issue_key']
                }
            },
            {
                'name': 'jira_create_issue',
                'description': 'Crear un nuevo ticket Jira',
                'inputSchema': {
                    'type': 'object',
                    'properties': {
                        'project': {
                            'type': 'string',
                            'description': 'Clave del proyecto (ej: CRM)'
                        },
                        'summary': {
                            'type': 'string',
                            'description': 'Título del ticket'
                        },
                        'description': {
                            'type': 'string',
                            'description': 'Descripción del ticket (opcional)'
                        },
                        'issue_type': {
                            'type': 'string',
                            'description': 'Tipo de ticket (Bug, Task, Story, etc)',
                            'default': 'Bug'
                        }
                    },
                    'required': ['project', 'summary']
                }
            },
            {
                'name': 'jira_update_issue',
                'description': 'Actualizar un ticket Jira',
                'inputSchema': {
                    'type': 'object',
                    'properties': {
                        'issue_key': {
                            'type': 'string',
                            'description': 'Clave del ticket (ej: CRM-4017)'
                        },
                        'summary': {
                            'type': 'string',
                            'description': 'Nuevo título (opcional)'
                        },
                        'description': {
                            'type': 'string',
                            'description': 'Nueva descripción (opcional)'
                        },
                        'status': {
                            'type': 'string',
                            'description': 'Nuevo estado: To Do, In Progress, Done, etc (opcional)'
                        },
                        'assignee': {
                            'type': 'string',
                            'description': 'Usuario a asignar (opcional)'
                        }
                    },
                    'required': ['issue_key']
                }
            },
            {
                'name': 'jira_search_issues',
                'description': 'Buscar tickets con JQL (Jira Query Language)',
                'inputSchema': {
                    'type': 'object',
                    'properties': {
                        'jql': {
                            'type': 'string',
                            'description': 'Consulta JQL (ej: "project = CRM AND status = Open")'
                        },
                        'max_results': {
                            'type': 'integer',
                            'description': 'Máximo de resultados (default: 10)',
                            'default': 10
                        }
                    },
                    'required': ['jql']
                }
            },
            {
                'name': 'jira_get_transitions',
                'description': 'Ver transiciones disponibles para un ticket',
                'inputSchema': {
                    'type': 'object',
                    'properties': {
                        'issue_key': {
                            'type': 'string',
                            'description': 'Clave del ticket (ej: CRM-4017)'
                        }
                    },
                    'required': ['issue_key']
                }
            }
        ]

        return {'tools': tools}

    def _handle_tool_call(self, params: Dict[str, Any]) -> Any:
        
        tool_name = params.get('name')
        tool_params = params.get('arguments', {})

        if tool_name == 'jira_get_issue':
            return self.client.get_issue(tool_params['issue_key'])

        elif tool_name == 'jira_create_issue':
            key = self.client.create_issue(
                project=tool_params['project'],
                summary=tool_params['summary'],
                description=tool_params.get('description'),
                issue_type=tool_params.get('issue_type', 'Bug')
            )
            return {'created': key}

        elif tool_name == 'jira_update_issue':
            result = self.client.update_issue(
                tool_params['issue_key'],
                summary=tool_params.get('summary'),
                description=tool_params.get('description'),
                status=tool_params.get('status'),
                assignee=tool_params.get('assignee')
            )
            return {'updated': result}

        elif tool_name == 'jira_search_issues':
            results = self.client.search_issues(
                jql=tool_params['jql'],
                max_results=tool_params.get('max_results', 10)
            )
            return {'issues': results}

        elif tool_name == 'jira_get_transitions':
            transitions = self.client.get_transitions(tool_params['issue_key'])
            return {'transitions': transitions}

        else:
            raise ValueError(f"Unknown tool: {tool_name}")

    def _error_response(self, request_id: Any, error_msg: str) -> Dict[str, Any]:
        
        return {
            'jsonrpc': '2.0',
            'id': request_id,
            'error': {
                'code': -32603,
                'message': error_msg
            }
        }

    def run(self):
        
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue

            try:
                request = json.loads(line)
                response = self.handle_request(request)
                print(json.dumps(response))
                sys.stdout.flush()
            except json.JSONDecodeError as e:
                error_response = {
                    'jsonrpc': '2.0',
                    'id': None,
                    'error': {
                        'code': -32700,
                        'message': f'Parse error: {e}'
                    }
                }
                print(json.dumps(error_response))
                sys.stdout.flush()


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Servidor MCP para PyJiraMCP')
    parser.add_argument('--config', default='config.toml', help='Ruta a config.toml')
    args = parser.parse_args()

    server = MCPServer(args.config)
    server.run()
