import logging
from typing import Any, Dict, List, Optional
import os
from dotenv import load_dotenv
from hubspot import HubSpot
from hubspot.crm.contacts import SimplePublicObjectInputForCreate
from hubspot.crm.contacts.exceptions import ApiException
from mcp.server.models import InitializationOptions
import mcp.types as types
from mcp.server import NotificationOptions, Server
import mcp.server.stdio
from pydantic import AnyUrl

logger = logging.getLogger('mcp_hubspot_server')

class HubSpotClient:
    def __init__(self, access_token: Optional[str] = None):
        access_token = access_token or os.getenv("HUBSPOT_ACCESS_TOKEN")
        logger.debug(f"Using access token: {'[MASKED]' if access_token else 'None'}")
        if not access_token:
            raise ValueError("HUBSPOT_ACCESS_TOKEN environment variable is required")
        
        self.client = HubSpot(access_token=access_token)

    def get_contacts(self) -> List[Dict[str, Any]]:
        """Get all contacts from HubSpot"""
        try:
            contacts = self.client.crm.contacts.get_all()
            return [contact.to_dict() for contact in contacts]
        except ApiException as e:
            raise Exception(f"Exception when requesting contacts: {str(e)}")

    def create_contact(self, email: str, firstname: str, lastname: str, properties: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Create a new contact in HubSpot"""
        try:
            properties = properties or {}
            properties.update({
                "email": email,
                "firstname": firstname,
                "lastname": lastname
            })
            simple_public_object_input = SimplePublicObjectInputForCreate(
                properties=properties
            )
            response = self.client.crm.contacts.basic_api.create(
                simple_public_object_input_for_create=simple_public_object_input
            )
            return response.to_dict()
        except ApiException as e:
            raise Exception(f"Exception when creating contact: {str(e)}")

    def get_companies(self) -> List[Dict[str, Any]]:
        """Get all companies from HubSpot"""
        try:
            companies = self.client.crm.companies.get_all()
            return [company.to_dict() for company in companies]
        except ApiException as e:
            raise Exception(f"Exception when requesting companies: {str(e)}")

    def create_company(self, name: str, domain: str, properties: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Create a new company in HubSpot"""
        try:
            properties = properties or {}
            properties.update({
                "name": name,
                "domain": domain
            })
            response = self.client.crm.companies.basic_api.create(properties=properties)
            return response.to_dict()
        except Exception as e:
            raise Exception(f"Failed to create company: {str(e)}")

async def main(access_token: Optional[str] = None):
    """Run the HubSpot MCP server."""
    logger.info("Server starting")
    hubspot = HubSpotClient(access_token)
    server = Server("hubspot-manager")

    @server.list_resources()
    async def handle_list_resources() -> list[types.Resource]:
        return [
            types.Resource(
                uri=AnyUrl("hubspot://contacts"),
                name="HubSpot Contacts",
                description="List of HubSpot contacts",
                mimeType="application/json",
            ),
            types.Resource(
                uri=AnyUrl("hubspot://companies"),
                name="HubSpot Companies", 
                description="List of HubSpot companies",
                mimeType="application/json",
            )
        ]

    @server.read_resource()
    async def handle_read_resource(uri: AnyUrl) -> str:
        if uri.scheme != "hubspot":
            await server.request_context.session.send_log_message(
                level="error",
                data=f"Unsupported URI scheme: {uri.scheme}",
            )
            raise ValueError(f"Unsupported URI scheme: {uri.scheme}")

        path = str(uri).replace("hubspot://", "")
        if path == "contacts":
            return str(hubspot.get_contacts())
        elif path == "companies":
            return str(hubspot.get_companies())
        else:
            await server.request_context.session.send_log_message(
                level="error",
                data=f"Unknown resource path: {path}",
            )
            raise ValueError(f"Unknown resource path: {path}")

    @server.list_tools()
    async def handle_list_tools() -> list[types.Tool]:
        """List available tools"""
        return [
            types.Tool(
                name="get_contacts",
                description="Get contacts from HubSpot",
                inputSchema={
                    "type": "object",
                    "properties": {},
                },
            ),
            types.Tool(
                name="create_contact",
                description="Create a new contact in HubSpot",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "email": {"type": "string", "description": "Contact's email address"},
                        "firstname": {"type": "string", "description": "Contact's first name"},
                        "lastname": {"type": "string", "description": "Contact's last name"},
                        "properties": {"type": "object", "description": "Additional contact properties"}
                    },
                    "required": ["email", "firstname", "lastname"]
                },
            ),
            types.Tool(
                name="get_companies",
                description="Get companies from HubSpot",
                inputSchema={
                    "type": "object",
                    "properties": {},
                },
            ),
            types.Tool(
                name="create_company",
                description="Create a new company in HubSpot",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "Company name"},
                        "domain": {"type": "string", "description": "Company domain"},
                        "properties": {"type": "object", "description": "Additional company properties"}
                    },
                    "required": ["name", "domain"]
                },
            ),
        ]

    @server.call_tool()
    async def handle_call_tool(
        name: str, arguments: dict[str, Any] | None
    ) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
        """Handle tool execution requests"""
        try:
            if name == "get_contacts":
                results = hubspot.get_contacts()
                return [types.TextContent(type="text", text=str(results))]

            elif name == "create_contact":
                if not arguments:
                    raise ValueError("Missing arguments for create_contact")
                results = hubspot.create_contact(
                    email=arguments["email"],
                    firstname=arguments["firstname"],
                    lastname=arguments["lastname"],
                    properties=arguments.get("properties")
                )
                return [types.TextContent(type="text", text=str(results))]

            elif name == "get_companies":
                results = hubspot.get_companies()
                return [types.TextContent(type="text", text=str(results))]

            elif name == "create_company":
                if not arguments:
                    raise ValueError("Missing arguments for create_company")
                results = hubspot.create_company(
                    name=arguments["name"],
                    domain=arguments["domain"],
                    properties=arguments.get("properties")
                )
                return [types.TextContent(type="text", text=str(results))]

            else:
                raise ValueError(f"Unknown tool: {name}")

        except ApiException as e:
            return [types.TextContent(type="text", text=f"HubSpot API error: {str(e)}")]
        except Exception as e:
            return [types.TextContent(type="text", text=f"Error: {str(e)}")]

    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        logger.info("Server running with stdio transport")
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="hubspot",
                server_version="0.1.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )

if __name__ == "__main__":
    import asyncio
    asyncio.run(main()) 