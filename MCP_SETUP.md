# 🔌 Configurar PyJiraMCP como MCP Server

Este documento explica cómo registrar PyJiraMCP como servidor MCP (Model Context Protocol) para que los agentes Claude puedan usarlo.

## ¿Qué es MCP?

**MCP (Model Context Protocol)** es el protocolo de Anthropic que permite a los modelos IA acceder a herramientas y recursos externos de forma segura y estandarizada. Con MCP, puedes usar PyJiraMCP directamente desde Claude sin escribir código.

## 📋 Requisitos previos

1. **Tener PyJiraMCP configurado:**
   ```bash
   cd ~/Desktop/pyjiramcp
   cp config.toml.example config.toml
   # Editar config.toml con tus credenciales
   ```

2. **Python 3.7+ instalado**

3. **Claude Code (versión reciente)**

## 🚀 Instalación

### Opción 1: Usando settings.json global

1. Ir a `~/.claude/settings.json`:
   ```bash
   mkdir -p ~/.claude
   cat > ~/.claude/settings.json << 'EOF'
{
  "mcpServers": {
    "pyjiramcp": {
      "command": "python3",
      "args": [
        "/home/user/Desktop/pyjiramcp/mcp_server.py",
        "--config",
        "/home/user/Desktop/pyjiramcp/config.toml"
      ]
    }
  }
}
EOF
   ```

2. Reiniciar Claude Code

### Opción 2: Usando settings.json del proyecto

Si estás en un proyecto específico:

1. Crear `.claude/settings.json` en la raíz del proyecto:
   ```bash
   mkdir -p .claude
   cat > .claude/settings.json << 'EOF'
{
  "mcpServers": {
    "pyjiramcp": {
      "command": "python3",
      "args": [
        "/home/user/Desktop/pyjiramcp/mcp_server.py",
        "--config",
        "/home/user/Desktop/pyjiramcp/config.toml"
      ]
    }
  }
}
EOF
   ```

2. Abrir el proyecto en Claude Code

### Opción 3: Desde la interfaz Claude Code

1. Abrir Claude Code
2. Ir a **Settings** → **MCP Servers**
3. Click en **Add New Server**
4. Configurar:
   - **Name:** PyJiraMCP
   - **Command:** python3
   - **Arguments:** `/home/user/Desktop/pyjiramcp/mcp_server.py --config /home/user/Desktop/pyjiramcp/config.toml`

## ✅ Verificar que funciona

Después de configurar, prueba en Claude Code:

```
Obtén el ticket CRM-4017 de Jira
```

Si funciona, verás que Claude puede acceder a la herramienta `jira_get_issue` automáticamente.

## 🛠️ Herramientas disponibles

Una vez configurado, los agentes pueden usar estas herramientas:

### 1. `jira_get_issue`
Obtener detalles de un ticket
```
Parámetros:
- issue_key (requerido): Clave del ticket (ej: CRM-4017)
```

### 2. `jira_create_issue`
Crear un nuevo ticket
```
Parámetros:
- project (requerido): Clave del proyecto (ej: CRM)
- summary (requerido): Título del ticket
- description (opcional): Descripción
- issue_type (opcional): Tipo (Bug, Task, Story, etc) - default: Bug
```

### 3. `jira_update_issue`
Actualizar un ticket
```
Parámetros:
- issue_key (requerido): Clave del ticket
- summary (opcional): Nuevo título
- description (opcional): Nueva descripción
- status (opcional): Nuevo estado (In Progress, Done, etc)
- assignee (opcional): Usuario a asignar
```

### 4. `jira_search_issues`
Buscar tickets con JQL
```
Parámetros:
- jql (requerido): Consulta JQL (ej: "project = CRM AND status = Open")
- max_results (opcional): Máximo de resultados - default: 10
```

### 5. `jira_get_transitions`
Ver transiciones disponibles
```
Parámetros:
- issue_key (requerido): Clave del ticket
```

## 💡 Ejemplos de uso en Claude Code

### Ejemplo 1: Consultar un ticket
**Prompt:**
```
Obtén el ticket CRM-4029 y cuéntame el status
```

**Qué hace Claude:**
- Automáticamente llama a `jira_get_issue` con `issue_key: CRM-4029`
- Te muestra el status y otros detalles

### Ejemplo 2: Buscar y crear
**Prompt:**
```
Busca todos los tickets abiertos en el proyecto CRM y crea uno nuevo llamado "Fix: integración con MCP"
```

**Qué hace Claude:**
- Llama a `jira_search_issues` con JQL
- Muestra los resultados
- Llama a `jira_create_issue` para crear el nuevo ticket

### Ejemplo 3: Actualizar descripción
**Prompt:**
```
El ticket CRM-4017 tiene caracteres de escape literales en la descripción. 
Actualiza la descripción a: "Implementar cálculo dinámico del precio total de servicios extras en el PDP de excursiones"
```

**Qué hace Claude:**
- Llama a `jira_update_issue` para actualizar la descripción

### Ejemplo 4: Ver transiciones
**Prompt:**
```
¿Cuáles son los estados a los que puedo cambiar el ticket CRM-4017?
```

**Qué hace Claude:**
- Llama a `jira_get_transitions`
- Te muestra todas las transiciones disponibles

## 🔒 Seguridad

- ✅ El token está en `config.toml` (protegido con `.gitignore`)
- ✅ El servidor MCP corre localmente (sin exposición a internet)
- ✅ Claude solo accede a través de stdio (aislado)
- ✅ El `config.toml` no se commitea

## 🐛 Troubleshooting

### Error: "Server not found: pyjiramcp"
- Verifica que `~/.claude/settings.json` tiene la configuración correcta
- Reinicia Claude Code
- Verifica que Python 3 está en el PATH: `which python3`

### Error: "Connection refused"
- Verifica que el archivo `config.toml` existe y tiene credenciales válidas
- Prueba ejecutar el servidor manualmente:
  ```bash
  cd ~/Desktop/pyjiramcp
  python3 mcp_server.py < /dev/null
  ```

### Error: "config.toml not found"
- Copia el archivo de ejemplo:
  ```bash
  cd ~/Desktop/pyjiramcp
  cp config.toml.example config.toml
  ```
- Edita con tus credenciales

### Las herramientas aparecen pero no funcionan
- Verifica que el token de Jira es válido
- Prueba manualmente:
  ```bash
  cd ~/Desktop/pyjiramcp
  python3 cli.py get CRM-4017
  ```

## 📚 Más información

- [MCP Protocol Spec](https://modelcontextprotocol.io/)
- [Claude Code Documentation](https://claude.com/claude-code)
- [Jira API Documentation](https://developer.atlassian.com/cloud/jira/rest/v3/)

---

**¡Listo!** Una vez configurado, los agentes Claude tendrán acceso completo a Jira a través de PyJiraMCP. 🚀
