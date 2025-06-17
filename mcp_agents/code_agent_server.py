"""
Code Agent MCP Server

Runs the Code Agent as a separate MCP server process for fault isolation.
Handles programming tasks, code generation, debugging, and file operations.
"""

import sys
import os
import asyncio
import configparser

# Add the parent directory to the path to import agent modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcp_agents.base_mcp_agent_server import create_agent_server
from sources.agents.code_agent import CoderAgent
from sources.llm_provider import Provider
import logging

logger = logging.getLogger(__name__)

class CodeAgentMCPServer:
    """Code Agent MCP Server wrapper"""
    
    def __init__(self):
        """Initialize the code agent"""
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
            
            # Initialize the code agent
            self.code_agent = CoderAgent(
                name="coder",
                prompt_path=f"prompts/{personality_folder}/coder_agent.txt",
                provider=provider,
                verbose=False
            )
            self.capabilities = [
                "code_generation",
                "code_debugging",
                "code_review",
                "file_operations",
                "code_execution"
            ]
            self.description = "Code agent for programming assistance, debugging, and development tasks"
            self.version = "1.0.0"
            logger.info("✅ Code Agent initialized successfully")
        except Exception as e:
            logger.error(f"❌ Failed to initialize Code Agent: {str(e)}")
            raise

if __name__ == "__main__":
    """Run the Code Agent MCP Server"""
    
    if len(sys.argv) != 2:
        print("Usage: python code_agent_server.py <port>")
        sys.exit(1)
    
    try:
        port = int(sys.argv[1])
        logger.info(f"💻 Starting Code Agent MCP Server on port {port}")
        create_agent_server("code", CodeAgentMCPServer, port)
    except ValueError:
        logger.error("❌ Invalid port number")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Failed to start Code Agent server: {str(e)}")
        sys.exit(1)
