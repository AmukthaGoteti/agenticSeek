"""
Planner Agent MCP Server

Runs the Planner Agent as a separate MCP server process for fault isolation.
Handles complex multi-step tasks, task planning, and agent orchestration.
"""

import sys
import os
import asyncio
import configparser

# Add the parent directory to the path to import agent modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcp_agents.base_mcp_agent_server import create_agent_server
from sources.agents.planner_agent import PlannerAgent
from sources.llm_provider import Provider
from sources.browser import Browser, create_driver
import logging

logger = logging.getLogger(__name__)

class PlannerAgentMCPServer:
    """Planner Agent MCP Server wrapper"""
    
    def __init__(self):
        """Initialize the planner agent"""
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
            
            # Initialize the planner agent
            self.planner_agent = PlannerAgent(
                name="Planner",
                prompt_path=f"prompts/{personality_folder}/planner_agent.txt",
                provider=provider,
                verbose=False,
                browser=browser
            )
            self.capabilities = [
                "task_planning",
                "multi_step_coordination",
                "workflow_management",
                "agent_orchestration",
                "complex_problem_solving"
            ]
            self.description = "Planner agent for complex multi-step tasks and workflow coordination"
            self.version = "1.0.0"
            logger.info("✅ Planner Agent initialized successfully")
        except Exception as e:
            logger.error(f"❌ Failed to initialize Planner Agent: {str(e)}")
            raise

if __name__ == "__main__":
    """Run the Planner Agent MCP Server"""
    
    if len(sys.argv) != 2:
        print("Usage: python planner_agent_server.py <port>")
        sys.exit(1)
    
    try:
        port = int(sys.argv[1])
        logger.info(f"📋 Starting Planner Agent MCP Server on port {port}")
        create_agent_server("planner", PlannerAgentMCPServer, port)
    except ValueError:
        logger.error("❌ Invalid port number")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Failed to start Planner Agent server: {str(e)}")
        sys.exit(1)
