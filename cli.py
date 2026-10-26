#!/usr/bin/env python3


import argparse
import json
import sys
from jira_client import JiraClient


def main():
    parser = argparse.ArgumentParser(
        description='Jira CLI - Cliente sin dependencias externas',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
EJEMPLOS:
  python cli.py get CRM-4017

  python cli.py create --project CRM --summary "Mi bug" --description "Descripción"

  python cli.py update CRM-4017 --description "Descripción corregida sin caracteres de escape"

  python cli.py update CRM-4017 --status "In Progress"

  python cli.py search --jql "project = CRM AND status = Open" --limit 20

  python cli.py transitions CRM-4017
        '''
    )

    parser.add_argument('--config', default='config.toml', help='Ruta a config.toml')
    subparsers = parser.add_subparsers(dest='command', required=True, help='Comando a ejecutar')

    get_parser = subparsers.add_parser('get', help='Obtener detalles de un ticket')
    get_parser.add_argument('issue_key', help='Clave del ticket (ej: CRM-4017)')

    create_parser = subparsers.add_parser('create', help='Crear un nuevo ticket')
    create_parser.add_argument('--project', required=True, help='Clave del proyecto (ej: CRM)')
    create_parser.add_argument('--summary', required=True, help='Título del ticket')
    create_parser.add_argument('--description', help='Descripción del ticket')
    create_parser.add_argument('--type', default='Bug', help='Tipo de ticket (Bug, Task, Story, etc)')

    update_parser = subparsers.add_parser('update', help='Actualizar un ticket')
    update_parser.add_argument('issue_key', help='Clave del ticket (ej: CRM-4017)')
    update_parser.add_argument('--summary', help='Nuevo título')
    update_parser.add_argument('--description', help='Nueva descripción')
    update_parser.add_argument('--status', help='Nuevo estado (In Progress, Done, etc)')
    update_parser.add_argument('--assignee', help='Asignar a usuario')

    search_parser = subparsers.add_parser('search', help='Buscar tickets con JQL')
    search_parser.add_argument('--jql', required=True, help='Consulta JQL')
    search_parser.add_argument('--limit', type=int, default=10, help='Máximo de resultados (default: 10)')

    transitions_parser = subparsers.add_parser('transitions', help='Ver transiciones disponibles')
    transitions_parser.add_argument('issue_key', help='Clave del ticket (ej: CRM-4017)')

    args = parser.parse_args()

    try:
        client = JiraClient(args.config)

        if args.command == 'get':
            result = client.get_issue(args.issue_key)
            print(json.dumps(result, indent=2, ensure_ascii=False))

        elif args.command == 'create':
            key = client.create_issue(
                project=args.project,
                summary=args.summary,
                description=args.description,
                issue_type=args.type
            )
            print(f"✅ Ticket creado: {key}")

        elif args.command == 'update':
            result = client.update_issue(
                args.issue_key,
                summary=args.summary,
                description=args.description,
                status=args.status,
                assignee=args.assignee
            )
            print(f"✅ {result}")

        elif args.command == 'search':
            results = client.search_issues(args.jql, args.limit)
            if results:
                print(json.dumps(results, indent=2, ensure_ascii=False))
                print(f"\n📊 {len(results)} ticket(s) encontrado(s)")
            else:
                print("No hay resultados")

        elif args.command == 'transitions':
            transitions = client.get_transitions(args.issue_key)
            if transitions:
                print(f"Transiciones disponibles para {args.issue_key}:")
                for t in transitions:
                    print(f"  • {t['name']} → {t['to']}")
            else:
                print("No hay transiciones disponibles")

    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
