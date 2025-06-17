"""
File Agent MCP Server

Runs the File Agent as a separate MCP server process for fault isolation.
Handles file operations, document management, and file system tasks.
"""

import sys
import os
import asyncio
import configparser

# Add the parent directory to the path to import agent modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcp_agents.base_mcp_agent_server import create_agent_server
from sources.agents.file_agent import FileAgent
from sources.llm_provider import Provider
import logging

logger = logging.getLogger(__name__)

class FileAgentMCPServer:
    """File Agent MCP Server wrapper"""
    
    def __init__(self):
        """Initialize the file agent"""
        try:
            # Load config
            config = configparser.ConfigParser()
            config.read('config.ini')
            
            # Initialize provider
            provider = Provider(
                provider_name=config["MAIN"]["provider_name"],
                model=config["MAIN"]["provider_model"],
                server_address=config["MAIN"]["provider_server_address"],
                is_local=config.getboolean('MAIN', 'is_local')
            )
            
            # Select personality folder
            personality_folder = "jarvis" if config.getboolean('MAIN', 'jarvis_personality') else "base"
            
            # Initialize the file agent
            self.file_agent = FileAgent(
                name="File Agent",
                prompt_path=f"prompts/{personality_folder}/file_agent.txt",
                provider=provider,
                verbose=False
            )
            self.capabilities = [
                "file_reading",
                "file_writing",
                "file_management",
                "directory_operations",
                "document_processing"
            ]
            self.description = "File agent for file operations, document management, and file system tasks"
            self.version = "1.0.0"
            logger.info("✅ File Agent initialized successfully")
        except Exception as e:
            logger.error(f"❌ Failed to initialize File Agent: {str(e)}")
            raise

if __name__ == "__main__":
    """Run the File Agent MCP Server"""
    
    if len(sys.argv) != 2:
        print("Usage: python file_agent_server.py <port>")
        sys.exit(1)
    
    try:
        port = int(sys.argv[1])
        logger.info(f"📁 Starting File Agent MCP Server on port {port}")
        create_agent_server("file", FileAgentMCPServer, port)
    except ValueError:
        logger.error("❌ Invalid port number")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Failed to start File Agent server: {str(e)}")
        sys.exit(1)
