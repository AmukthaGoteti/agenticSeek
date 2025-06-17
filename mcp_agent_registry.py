"""
Agent Registry for MCP-based Fault-Tolerant Architecture

This module manages the lifecycle and health monitoring of individual agent MCP servers.
Each agent runs as a separate process, allowing for fault isolation and hot-swapping.
"""

import asyncio
import subprocess
import sys
import time
from typing import Dict, Optional, List
import psutil
import requests
from dataclasses import dataclass
from enum import Enum
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AgentStatus(Enum):
    """Agent status enumeration"""
    STARTING = "starting"
    RUNNING = "running"
    CRASHED = "crashed"
    STOPPED = "stopped"
    RESTARTING = "restarting"

@dataclass
class AgentInfo:
    """Information about an individual agent"""
    name: str
    port: int
    process: Optional[subprocess.Popen] = None
    status: AgentStatus = AgentStatus.STOPPED
    last_health_check: float = 0
    restart_count: int = 0
    max_restarts: int = 3
    script_path: str = ""

class AgentRegistry:
    """
    Registry and health monitor for MCP agent servers.
    
    Responsibilities:
    - Start/stop individual agent processes
    - Monitor agent health
    - Automatic restart on failure
    - Fallback routing when agents fail
    """
    
    def __init__(self):
        """Initialize the agent registry with default agent configurations"""
        self.agents: Dict[str, AgentInfo] = {
            "browser": AgentInfo(
                name="browser",
                port=8001,
                script_path="mcp_agents/browser_agent_server.py"
            ),
            "code": AgentInfo(
                name="code",
                port=8002,
                script_path="mcp_agents/code_agent_server.py"
            ),
            "file": AgentInfo(
                name="file",
                port=8003,
                script_path="mcp_agents/file_agent_server.py"
            ),
            "casual": AgentInfo(
                name="casual",
                port=8004,
                script_path="mcp_agents/casual_agent_server.py"
            ),
            "planner": AgentInfo(
                name="planner",
                port=8005,
                script_path="mcp_agents/planner_agent_server.py"
            )
        }
        
        # Fallback hierarchy - if an agent fails, try these alternatives
        self.fallback_map = {
            "browser": ["casual"],
            "code": ["casual"],
            "file": ["casual"],
            "planner": ["casual", "code"],
            "casual": []  # No fallback for casual agent
        }
        
        self.health_check_interval = 10  # seconds
        self.health_monitor_running = False
    
    async def start_agent(self, agent_name: str) -> bool:
        """
        Start an individual agent MCP server
        
        Args:
            agent_name: Name of the agent to start
            
        Returns:
            bool: True if started successfully, False otherwise
        """
        if agent_name not in self.agents:
            logger.error(f"Unknown agent: {agent_name}")
            return False
        
        agent = self.agents[agent_name]
        
        # Stop existing process if running
        if agent.process and agent.process.poll() is None:
            logger.info(f"Stopping existing {agent_name} agent process")
            await self.stop_agent(agent_name)
        
        try:
            logger.info(f"Starting {agent_name} agent on port {agent.port}")
            agent.status = AgentStatus.STARTING
            
            # Start the agent process
            agent.process = subprocess.Popen([
                sys.executable, agent.script_path, str(agent.port)
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            # Wait for startup
            await asyncio.sleep(3)
            
            # Check if process started successfully
            if agent.process.poll() is None:
                # Verify health
                if await self.check_agent_health(agent_name):
                    agent.status = AgentStatus.RUNNING
                    logger.info(f"✅ {agent_name} agent started successfully on port {agent.port}")
                    return True
                else:
                    logger.error(f"❌ {agent_name} agent started but health check failed")
                    await self.stop_agent(agent_name)
                    return False
            else:
                logger.error(f"❌ {agent_name} agent process failed to start")
                agent.status = AgentStatus.CRASHED
                return False
                
        except Exception as e:
            logger.error(f"❌ Error starting {agent_name} agent: {str(e)}")
            agent.status = AgentStatus.CRASHED
            return False
    
    async def stop_agent(self, agent_name: str) -> bool:
        """
        Stop an individual agent MCP server
        
        Args:
            agent_name: Name of the agent to stop
            
        Returns:
            bool: True if stopped successfully, False otherwise
        """
        if agent_name not in self.agents:
            logger.error(f"Unknown agent: {agent_name}")
            return False
        
        agent = self.agents[agent_name]
        
        try:
            if agent.process and agent.process.poll() is None:
                logger.info(f"Stopping {agent_name} agent (PID: {agent.process.pid})")
                
                # Try graceful shutdown first
                agent.process.terminate()
                
                # Wait for graceful shutdown
                try:
                    agent.process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    logger.warning(f"Force killing {agent_name} agent")
                    agent.process.kill()
                    agent.process.wait()
                
                agent.status = AgentStatus.STOPPED
                logger.info(f"✅ {agent_name} agent stopped successfully")
                return True
            else:
                logger.info(f"{agent_name} agent was not running")
                agent.status = AgentStatus.STOPPED
                return True
                
        except Exception as e:
            logger.error(f"❌ Error stopping {agent_name} agent: {str(e)}")
            return False
    
    async def check_agent_health(self, agent_name: str) -> bool:
        """
        Check if an agent is healthy by sending a health check request
        
        Args:
            agent_name: Name of the agent to check
            
        Returns:
            bool: True if agent is healthy, False otherwise
        """
        if agent_name not in self.agents:
            return False
        
        agent = self.agents[agent_name]
        
        try:
            # Send health check request
            response = requests.get(
                f"http://localhost:{agent.port}/health",
                timeout=5
            )
            
            if response.status_code == 200:
                agent.last_health_check = time.time()
                if agent.status == AgentStatus.CRASHED:
                    agent.status = AgentStatus.RUNNING
                return True
            else:
                logger.warning(f"Health check failed for {agent_name}: HTTP {response.status_code}")
                return False
                
        except Exception as e:
            logger.warning(f"Health check failed for {agent_name}: {str(e)}")
            if agent.status == AgentStatus.RUNNING:
                agent.status = AgentStatus.CRASHED
            return False
    
    async def restart_agent(self, agent_name: str) -> bool:
        """
        Restart a crashed agent with restart count limits
        
        Args:
            agent_name: Name of the agent to restart
            
        Returns:
            bool: True if restarted successfully, False otherwise
        """
        if agent_name not in self.agents:
            return False
        
        agent = self.agents[agent_name]
        
        # Check restart limits
        if agent.restart_count >= agent.max_restarts:
            logger.error(f"❌ {agent_name} agent has exceeded max restart attempts ({agent.max_restarts})")
            agent.status = AgentStatus.CRASHED
            return False
        
        try:
            logger.info(f"🔄 Restarting {agent_name} agent (attempt {agent.restart_count + 1}/{agent.max_restarts})")
            agent.status = AgentStatus.RESTARTING
            agent.restart_count += 1
            
            # Stop and start the agent
            await self.stop_agent(agent_name)
            await asyncio.sleep(2)  # Brief pause before restart
            
            if await self.start_agent(agent_name):
                logger.info(f"✅ {agent_name} agent restarted successfully")
                return True
            else:
                logger.error(f"❌ Failed to restart {agent_name} agent")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error restarting {agent_name} agent: {str(e)}")
            agent.status = AgentStatus.CRASHED
            return False
    
    def get_healthy_agents(self) -> List[str]:
        """
        Get list of currently healthy agents
        
        Returns:
            List[str]: Names of healthy agents
        """
        return [
            name for name, agent in self.agents.items()
            if agent.status == AgentStatus.RUNNING
        ]
    
    def get_fallback_agents(self, failed_agent: str) -> List[str]:
        """
        Get fallback agents for a failed agent
        
        Args:
            failed_agent: Name of the failed agent
            
        Returns:
            List[str]: Names of available fallback agents
        """
        fallbacks = self.fallback_map.get(failed_agent, [])
        healthy_agents = self.get_healthy_agents()
        
        # Return fallbacks that are currently healthy
        return [agent for agent in fallbacks if agent in healthy_agents]
    
    async def start_all_agents(self) -> Dict[str, bool]:
        """
        Start all agents
        
        Returns:
            Dict[str, bool]: Agent name -> success status
        """
        logger.info("🚀 Starting all agent servers...")
        results = {}
        
        for agent_name in self.agents.keys():
            results[agent_name] = await self.start_agent(agent_name)
        
        healthy_count = sum(results.values())
        total_count = len(results)
        
        logger.info(f"📊 Agent startup complete: {healthy_count}/{total_count} agents healthy")
        return results
    
    async def stop_all_agents(self) -> Dict[str, bool]:
        """
        Stop all agents
        
        Returns:
            Dict[str, bool]: Agent name -> success status
        """
        logger.info("🛑 Stopping all agent servers...")
        results = {}
        
        for agent_name in self.agents.keys():
            results[agent_name] = await self.stop_agent(agent_name)
        
        logger.info("✅ All agents stopped")
        return results
    
    async def start_health_monitor(self):
        """Start continuous health monitoring of all agents"""
        logger.info("🏥 Starting agent health monitor...")
        self.health_monitor_running = True
        
        while self.health_monitor_running:
            try:
                for agent_name in self.agents.keys():
                    # Only check agents that should be running
                    if self.agents[agent_name].status in [AgentStatus.RUNNING, AgentStatus.CRASHED]:
                        is_healthy = await self.check_agent_health(agent_name)
                        
                        # Auto-restart crashed agents
                        if not is_healthy and self.agents[agent_name].status == AgentStatus.CRASHED:
                            logger.warning(f"🚨 {agent_name} agent is down, attempting restart...")
                            await self.restart_agent(agent_name)
                
                await asyncio.sleep(self.health_check_interval)
                
            except Exception as e:
                logger.error(f"❌ Error in health monitor: {str(e)}")
                await asyncio.sleep(self.health_check_interval)
    
    def stop_health_monitor(self):
        """Stop the health monitor"""
        logger.info("🏥 Stopping agent health monitor...")
        self.health_monitor_running = False
    
    def get_agent_status(self) -> Dict[str, Dict]:
        """
        Get detailed status of all agents
        
        Returns:
            Dict: Agent status information
        """
        status = {}
        for name, agent in self.agents.items():
            status[name] = {
                "status": agent.status.value,
                "port": agent.port,
                "restart_count": agent.restart_count,
                "last_health_check": agent.last_health_check,
                "process_id": agent.process.pid if agent.process else None,
                "running": agent.process.poll() is None if agent.process else False
            }
        return status

# Singleton instance
agent_registry = AgentRegistry()

if __name__ == "__main__":
    """Test the agent registry"""
    async def main():
        registry = AgentRegistry()
        
        # Start all agents
        await registry.start_all_agents()
        
        # Start health monitoring
        health_task = asyncio.create_task(registry.start_health_monitor())
        
        try:
            # Keep running for a while
            await asyncio.sleep(60)
        except KeyboardInterrupt:
            logger.info("Shutting down...")
        finally:
            # Clean shutdown
            registry.stop_health_monitor()
            await health_task
            await registry.stop_all_agents()
    
    asyncio.run(main())
