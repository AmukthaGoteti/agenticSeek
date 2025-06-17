#!/usr/bin python3
"""
AgenticSeek Command Line Interface
==================================

This module provides a command-line interface for interacting with AgenticSeek agents.
It offers a terminal-based way to access all agent capabilities including web browsing,
code execution, file management, and general conversation.

Key Features:
- Interactive command-line interface
- Multi-agent system access via CLI
- Configuration-based setup
- Cross-platform compatibility
- Real-time agent interaction
- Session management and history

Available Agents:
- CasualAgent: General conversation and Q&A
- CodeAgent: Programming and development tasks
- FileAgent: File system operations
- BrowserAgent: Web browsing and research
- PlannerAgent: Task planning and orchestration
- McpAgent: Model Context Protocol integration

CLI Features:
- Interactive conversation mode
- Command history and navigation
- Real-time response streaming
- Multi-language support
- Personality customization (Jarvis mode)
- Configuration management

Usage:
    python cli.py                    # Start interactive mode
    python cli.py --agent code       # Start with specific agent
    python cli.py --config custom    # Use custom configuration

Configuration:
- config.ini: Main configuration file
- Personality selection: base or jarvis
- Language preferences
- Provider settings (Ollama, OpenAI, etc.)

Author: AgenticSeek Team
License: See LICENSE file
"""

import sys
import argparse
import configparser
import asyncio

# Import AgenticSeek core modules
from sources.llm_provider import Provider
from sources.interaction import Interaction
from sources.agents import Agent, CoderAgent, CasualAgent, FileAgent, PlannerAgent, BrowserAgent, McpAgent
from sources.browser import Browser, create_driver
from sources.utility import pretty_print

# Suppress warnings for cleaner CLI output
import warnings
warnings.filterwarnings("ignore")

# Load configuration from config.ini
config = configparser.ConfigParser()
config.read('config.ini')

async def main():
    """
    Main CLI entry point for AgenticSeek
    
    Initializes the system, loads configuration, and starts the interactive
    command-line interface for agent interaction.
    """
    pretty_print("Initializing AgenticSeek CLI...", color="status")
    
    # Load configuration settings
    stealth_mode = config.getboolean('BROWSER', 'stealth_mode')
    personality_folder = "jarvis" if config.getboolean('MAIN', 'jarvis_personality') else "base"
    languages = config["MAIN"]["languages"].split(' ')

    # Initialize LLM provider
    provider = Provider(provider_name=config["MAIN"]["provider_name"],
                        model=config["MAIN"]["provider_model"],
                        server_address=config["MAIN"]["provider_server_address"],
                        is_local=config.getboolean('MAIN', 'is_local'))

    browser = Browser(
        create_driver(headless=config.getboolean('BROWSER', 'headless_browser'), stealth_mode=stealth_mode, lang=languages[0]),
        anticaptcha_manual_install=stealth_mode
    )

    agents = [
        CasualAgent(name=config["MAIN"]["agent_name"],
                    prompt_path=f"prompts/{personality_folder}/casual_agent.txt",
                    provider=provider, verbose=False),
        CoderAgent(name="coder",
                   prompt_path=f"prompts/{personality_folder}/coder_agent.txt",
                   provider=provider, verbose=False),
        FileAgent(name="File Agent",
                  prompt_path=f"prompts/{personality_folder}/file_agent.txt",
                  provider=provider, verbose=False),
        BrowserAgent(name="Browser",
                     prompt_path=f"prompts/{personality_folder}/browser_agent.txt",
                     provider=provider, verbose=False, browser=browser),
        PlannerAgent(name="Planner",
                     prompt_path=f"prompts/{personality_folder}/planner_agent.txt",
                     provider=provider, verbose=False, browser=browser),
        #McpAgent(name="MCP Agent",
        #            prompt_path=f"prompts/{personality_folder}/mcp_agent.txt",
        #            provider=provider, verbose=False), # NOTE under development
    ]

    interaction = Interaction(agents,
                              tts_enabled=config.getboolean('MAIN', 'speak'),
                              stt_enabled=config.getboolean('MAIN', 'listen'),
                              recover_last_session=config.getboolean('MAIN', 'recover_last_session'),
                              langs=languages
                            )
    try:
        while interaction.is_active:
            interaction.get_user()
            if await interaction.think():
                interaction.show_answer()
                interaction.speak_answer()
    except Exception as e:
        if config.getboolean('MAIN', 'save_session'):
            interaction.save_session()
        raise e
    finally:
        if config.getboolean('MAIN', 'save_session'):
            interaction.save_session()

if __name__ == "__main__":
    asyncio.run(main())