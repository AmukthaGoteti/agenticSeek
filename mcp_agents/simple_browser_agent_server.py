"""
Simple Browser Agent MCP Server

A simplified version of the browser agent that doesn't require Chrome WebDriver.
This agent can handle web search queries without browser automation.
"""

import sys
import os
import asyncio
import configparser

# Add the parent directory to the path to import agent modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcp_agents.base_mcp_agent_server import create_agent_server
from sources.agents.casual_agent import CasualAgent  # Use casual agent as base for now
from sources.llm_provider import Provider
import logging

logger = logging.getLogger(__name__)

class SimpleBrowserAgentMCPServer:
    """Simple Browser Agent MCP Server wrapper"""
    
    def __init__(self):
        """Initialize the simple browser agent"""
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
            
            # Initialize a casual agent as the base for browser functionality
            # This provides basic conversational abilities without browser automation
            self.browser_agent = CasualAgent(
                name="Simple Browser",
                prompt_path=f"prompts/{personality_folder}/casual_agent.txt",
                provider=provider,
                verbose=False
            )
            
            self.capabilities = [
                "web_search_discussion",
                "url_analysis", 
                "web_content_discussion",
                "search_strategy_advice"
            ]
            self.description = "Simple browser agent for web-related discussions without browser automation"
            self.version = "1.0.0"
            logger.info("✅ Simple Browser Agent initialized successfully")
        except Exception as e:
            logger.error(f"❌ Failed to initialize Simple Browser Agent: {str(e)}")
            raise

if __name__ == "__main__":
    """Run the Simple Browser Agent MCP Server"""
    
    if len(sys.argv) != 2:
        print("Usage: python simple_browser_agent_server.py <port>")
        sys.exit(1)
    
    try:
        port = int(sys.argv[1])
        logger.info(f"🌐 Starting Simple Browser Agent MCP Server on port {port}")
        create_agent_server("browser", SimpleBrowserAgentMCPServer, port)
    except ValueError:
        logger.error("❌ Invalid port number")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Failed to start Simple Browser Agent server: {str(e)}")
        sys.exit(1)
