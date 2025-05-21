FROM node:20-slim

# Install SuperGateway and MCP server
RUN npm install -g supergateway @hubspot/mcp-server

# App config
WORKDIR /app
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 8080
ENTRYPOINT ["/entrypoint.sh"]