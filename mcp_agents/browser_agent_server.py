"""
Browser Agent MCP Server

Runs the Browser Agent as a separate MCP server process for fault isolation.
Handles web browsing, searching, and screenshot capture.
"""

import sys
import os
import asyncio
import configparser

# Add the parent directory to the path to import agent modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcp_agents.base_mcp_agent_server import create_agent_server
from sources.agents.browser_agent import BrowserAgent
from sources.llm_provider import Provider
from sources.browser import Browser, create_driver
import logging

logger = logging.getLogger(__name__)

class BrowserAgentMCPServer:
    """Browser Agent MCP Server wrapper"""
    
    def __init__(self):
        """Initialize the browser agent"""
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
            
            # Initialize browser
            stealth_mode = config.getboolean('BROWSER', 'stealth_mode')
            languages = config["MAIN"]["languages"].split(' ')
            browser = Browser(
                create_driver(headless=config.getboolean('BROWSER', 'headless_browser'), 
                             stealth_mode=stealth_mode, lang=languages[0]),
                anticaptcha_manual_install=stealth_mode
            )
            
            # Select personality folder
            personality_folder = "jarvis" if config.getboolean('MAIN', 'jarvis_personality') else "base"
            
            # Initialize the browser agent
            self.browser_agent = BrowserAgent(
                name="Browser",
                prompt_path=f"prompts/{personality_folder}/browser_agent.txt",
                provider=provider,
                verbose=False,
                browser=browser
            )
            self.capabilities = [
                "web_search",
                "url_browsing", 
                "screenshot_capture",
                "web_content_extraction"
            ]
            self.description = "Browser agent for web research, searching, and content extraction"
            self.version = "1.0.0"
            logger.info("✅ Browser Agent initialized successfully")
        except Exception as e:
            logger.error(f"❌ Failed to initialize Browser Agent: {str(e)}")
            raise

if __name__ == "__main__":
    """Run the Browser Agent MCP Server"""
    
    if len(sys.argv) != 2:
        print("Usage: python browser_agent_server.py <port>")
        sys.exit(1)
    
    try:
        port = int(sys.argv[1])
        logger.info(f"🌐 Starting Browser Agent MCP Server on port {port}")
        create_agent_server("browser", BrowserAgentMCPServer, port)
    except ValueError:
        logger.error("❌ Invalid port number")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Failed to start Browser Agent server: {str(e)}")
        sys.exit(1)
