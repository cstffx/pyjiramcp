#!/usr/bin/env python3


import json
import base64
import urllib.request
import urllib.parse
from typing import Optional, Dict, Any


ADF_NODE_TYPES = {
    'doc', 'paragraph', 'text', 'bulletList', 'orderedList', 'listItem',
    'codeBlock', 'heading', 'blockquote', 'rule', 'hardBreak', 'mention',
    'table', 'tableRow', 'tableCell', 'tableHeader', 'panel', 'emoji',
    'mediaSingle', 'media', 'inlineCard',
}


def _text_to_adf(text: str) -> Dict[str, Any]:
    """Convierte texto plano (párrafos separados por línea en blanco) a un documento ADF mínimo.

    Las líneas que empiezan con '# ', '## ' o '### ' se convierten en encabezados
    reales de Jira (heading level 1/2/3) en vez de quedar como texto literal con
    los símbolos '#' visibles.
    """
    content = []
    for para in text.split('\n\n'):
        lines = [l for l in para.split('\n')]

        heading_match = None
        if len(lines) == 1:
            for prefix, level in (('### ', 3), ('## ', 2), ('# ', 1)):
                if lines[0].startswith(prefix):
                    heading_match = (level, lines[0][len(prefix):])
                    break

        if heading_match:
            level, heading_text = heading_match
            if heading_text:
                content.append({
                    'type': 'heading',
                    'attrs': {'level': level},
                    'content': [{'type': 'text', 'text': heading_text}],
                })
            continue

        para_content = []
        for i, line in enumerate(lines):
            if i > 0:
                para_content.append({'type': 'hardBreak'})
            if line:
                para_content.append({'type': 'text', 'text': line})
        if para_content:
            content.append({'type': 'paragraph', 'content': para_content})

    if not content:
        content = [{'type': 'paragraph', 'content': []}]

    return {'type': 'doc', 'version': 1, 'content': content}


def _validate_adf_node(node: Any, path: str) -> None:
    if not isinstance(node, dict):
        raise ValueError(
            f"{path}: cada nodo ADF debe ser un objeto (dict), recibido {type(node).__name__} ({node!r}). "
            f"Arreglo: envuelve el valor en un nodo, p.ej. {{'type': 'text', 'text': ...}}."
        )

    node_type = node.get('type')
    if node_type not in ADF_NODE_TYPES:
        raise ValueError(
            f"{path}: tipo de nodo ADF desconocido '{node_type}'. "
            f"Arreglo: usa uno de los tipos soportados: {sorted(ADF_NODE_TYPES)}."
        )

    if node_type == 'text' and not isinstance(node.get('text'), str):
        raise ValueError(
            f"{path}>text: falta la clave 'text' con un string (tiene: {node.get('text')!r}). "
            f"Arreglo: {{'type': 'text', 'text': '<contenido>'}}."
        )

    if node_type == 'codeBlock':
        attrs = node.get('attrs')
        if attrs is not None:
            language = attrs.get('language')
            if language is None:
                del node['attrs']
            elif not isinstance(language, str):
                raise ValueError(
                    f"{path}>codeBlock.attrs.language debe ser string (ej: 'python', 'json'), "
                    f"recibido {type(language).__name__} ({language!r}). "
                    f"Arreglo: usa un string de lenguaje o elimina 'attrs' por completo."
                )

    for child in node.get('content') or []:
        _validate_adf_node(child, path=f"{path}>{node_type}")


def validate_description(value: Any) -> Dict[str, Any]:
    """Normaliza y valida un valor de description antes de enviarlo a Jira.

    Acepta texto plano (se convierte a ADF) o un documento ADF ya construido.
    Corrige en el momento los problemas conocidos (p.ej. codeBlock.attrs.language=None,
    que Jira rechaza con HTTP 400 INVALID_INPUT) y lanza ValueError ante estructuras
    inválidas, antes de llegar a la API.
    """
    if isinstance(value, str):
        return _text_to_adf(value)

    if isinstance(value, dict):
        if value.get('type') != 'doc' or value.get('version') != 1:
            raise ValueError(
                f"description: el documento ADF debe tener type='doc' y version=1 "
                f"(recibido type={value.get('type')!r}, version={value.get('version')!r}). "
                f"Arreglo: {{'type': 'doc', 'version': 1, 'content': [...]}}."
            )
        if not isinstance(value.get('content'), list):
            raise ValueError(
                f"description.content debe ser una lista de nodos, recibido "
                f"{type(value.get('content')).__name__}. Arreglo: 'content': [{{'type': 'paragraph', ...}}]."
            )
        for i, child in enumerate(value['content']):
            _validate_adf_node(child, path=f'description.content[{i}]')
        return value

    raise ValueError(
        f"description: tipo no soportado {type(value).__name__} (recibido: {value!r}). "
        f"Arreglo: pasa un string de texto plano (se convierte a ADF automáticamente) "
        f"o un dict ADF completo con {{'type': 'doc', 'version': 1, 'content': [...]}}."
    )


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

        data = self._make_request('GET', f'/issue/{issue_key}')

        fields = data.get('fields', {})
        return {
            'key': data.get('key'),
            'summary': fields.get('summary'),
            'description': fields.get('description'),
            'status': (fields.get('status') or {}).get('name'),
            'type': (fields.get('issuetype') or {}).get('name'),
            'assignee': (fields.get('assignee') or {}).get('displayName'),
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
            payload['fields']['description'] = validate_description(description)

        response = self._make_request('POST', '/issue', payload)
        return response.get('key', 'Unknown')

    def find_user(self, query: str) -> list:
        """
        Buscar usuarios de Jira por email o nombre.

        Args:
            query: Email o nombre (parcial) a buscar

        Returns:
            Lista de usuarios encontrados (accountId, displayName, emailAddress)
        """
        encoded = urllib.parse.urlencode({'query': query})
        results = self._make_request('GET', f'/user/search?{encoded}')
        return [
            {
                'accountId': u.get('accountId'),
                'displayName': u.get('displayName'),
                'emailAddress': u.get('emailAddress'),
            }
            for u in results
        ]

    def _resolve_account_id(self, value: str) -> str:
        """Resuelve un email o nombre de usuario a su accountId de Jira Cloud.

        La API Cloud ya no acepta 'name' para identificar usuarios (eso era de
        Jira Server); el campo assignee necesita 'accountId'.
        """
        results = self.find_user(value)
        if not results:
            raise ValueError(f"No se encontró ningún usuario de Jira que coincida con '{value}'")
        return results[0]['accountId']

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
                    payload['fields'][jira_key] = {'accountId': self._resolve_account_id(value)}
                elif jira_key == 'status':
                    return self._transition_issue(issue_key, value)
                elif jira_key == 'description':
                    payload['fields'][jira_key] = validate_description(value)
                else:
                    payload['fields'][jira_key] = value

        if not payload['fields']:
            return f"No fields to update for {issue_key}"

        self._make_request('PUT', f'/issue/{issue_key}', payload)
        return f"Updated {issue_key}"

    def _transition_issue(self, issue_key: str, target_status: str) -> str:
        
        transitions = self._make_request('GET', f'/issue/{issue_key}/transitions')

        transition_id = None
        for t in transitions.get('transitions', []):
            if (t.get('to') or {}).get('name', '').lower() == target_status.lower():
                transition_id = t.get('id')
                break

        if not transition_id:
            return f"Status '{target_status}' not available for {issue_key}"

        payload = {'transition': {'id': transition_id}}
        self._make_request('POST', f'/issue/{issue_key}/transitions', payload)
        return f"Transitioned {issue_key} to {target_status}"

    def search_issues(self, jql: str, max_results: int = 10) -> list:
        """
        Buscar tickets usando JQL (Jira Query Language)

        Args:
            jql: Consulta JQL (ej: "project = CRM AND status = Open")
            max_results: Máximo número de resultados

        Returns:
            Lista de tickets encontrados
        """
        # La API vieja /rest/api/3/search fue eliminada por Atlassian (HTTP 410).
        # Hay que usar la nueva /rest/api/3/search/jql, que además requiere pedir
        # explícitamente los 'fields' que se quieren de vuelta (antes venían todos por defecto).
        query = urllib.parse.urlencode({
            'jql': jql,
            'maxResults': max_results,
            'fields': 'summary,status,issuetype,assignee',
        })
        data = self._make_request('GET', f'/search/jql?{query}')

        issues = []
        for issue in data.get('issues', []):
            fields = issue.get('fields', {})
            issues.append({
                'key': issue.get('key'),
                'summary': fields.get('summary'),
                'status': (fields.get('status') or {}).get('name'),
                'type': (fields.get('issuetype') or {}).get('name'),
                'assignee': (fields.get('assignee') or {}).get('displayName'),
            })

        return issues

    def get_transitions(self, issue_key: str) -> list:
        """
        Obtener transiciones disponibles para un ticket

        Args:
            issue_key: Clave del ticket

        Returns:
            Lista de transiciones disponibles
        """
        data = self._make_request('GET', f'/issue/{issue_key}/transitions')

        transitions = []
        for t in data.get('transitions', []):
            transitions.append({
                'id': t.get('id'),
                'name': t.get('name'),
                'to': (t.get('to') or {}).get('name'),
            })

        return transitions
