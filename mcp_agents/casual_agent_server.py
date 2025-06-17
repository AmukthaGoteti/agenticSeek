"""
Casual Agent MCP Server

Runs the Casual Agent as a separate MCP server process for fault isolation.
Handles general conversation, Q&A, and casual interactions.
"""

import sys
import os
import asyncio
import configparser

# Add the parent directory to the path to import agent modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcp_agents.base_mcp_agent_server import create_agent_server
from sources.agents.casual_agent import CasualAgent
from sources.llm_provider import Provider
import logging

logger = logging.getLogger(__name__)

class CasualAgentMCPServer:
    """Casual Agent MCP Server wrapper"""
    
    def __init__(self):
        """Initialize the casual agent"""
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
            
            # Initialize the casual agent
            self.casual_agent = CasualAgent(
                name=config["MAIN"]["agent_name"],
                prompt_path=f"prompts/{personality_folder}/casual_agent.txt",
                provider=provider,
                verbose=False
            )
            self.capabilities = [
                "general_conversation",
                "question_answering",
                "casual_chat",
                "knowledge_queries",
                "fallback_responses"
            ]
            self.description = "Casual agent for general conversation, Q&A, and fallback responses"
            self.version = "1.0.0"
            logger.info("✅ Casual Agent initialized successfully")
        except Exception as e:
            logger.error(f"❌ Failed to initialize Casual Agent: {str(e)}")
            raise

if __name__ == "__main__":
    """Run the Casual Agent MCP Server"""
    
    if len(sys.argv) != 2:
        print("Usage: python casual_agent_server.py <port>")
        sys.exit(1)
    
    try:
        port = int(sys.argv[1])
        logger.info(f"💬 Starting Casual Agent MCP Server on port {port}")
        create_agent_server("casual", CasualAgentMCPServer, port)
    except ValueError:
        logger.error("❌ Invalid port number")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Failed to start Casual Agent server: {str(e)}")
        sys.exit(1)
