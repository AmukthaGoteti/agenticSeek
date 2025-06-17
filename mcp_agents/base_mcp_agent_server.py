"""
Base MCP Agent Server

This module provides the base class for all individual agent MCP servers.
Each agent runs as a separate process with fault isolation.
"""

import asyncio
import sys
import traceback
from typing import Dict, Any, Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class QueryRequest(BaseModel):
    """Request model for agent queries"""
    query: str
    context: Optional[Dict[str, Any]] = None
    parameters: Optional[Dict[str, Any]] = None

class QueryResponse(BaseModel):
    """Response model for agent queries"""
    answer: str
    reasoning: str
    agent_name: str
    status: str
    blocks: Dict[str, Any]
    success: bool
    error: Optional[str] = None

class BaseMCPAgentServer:
    """
    Base class for MCP Agent Servers
    
    Each agent inherits from this class and implements the execute_query method.
    This provides standardized health checks, error handling, and API endpoints.
    """
    
    def __init__(self, agent_name: str, agent_instance):
        """
        Initialize the base MCP agent server
        
        Args:
            agent_name: Name of the agent (e.g., 'browser', 'code')
            agent_instance: Instance of the actual agent class
        """
        self.agent_name = agent_name
        self.agent = agent_instance
        self.app = FastAPI(title=f"{agent_name.title()} Agent MCP Server")
        self.setup_routes()
        
    def setup_routes(self):
        """Setup FastAPI routes for the agent server"""
        
        @self.app.get("/health")
        async def health_check():
            """Health check endpoint"""
            return {
                "status": "healthy",
                "agent": self.agent_name,
                "timestamp": asyncio.get_event_loop().time()
            }
        
        @self.app.post("/query", response_model=QueryResponse)
        async def execute_query(request: QueryRequest):
            """Execute a query using this agent"""
            try:
                logger.info(f"📝 {self.agent_name} agent received query: {request.query[:100]}...")
                
                # Execute the agent's query processing
                result = await self.execute_agent_query(request.query, request.context, request.parameters)
                
                # Format the response
                response = QueryResponse(
                    answer=result.get("answer", ""),
                    reasoning=result.get("reasoning", ""),
                    agent_name=self.agent_name,
                    status=result.get("status", "completed"),
                    blocks=result.get("blocks", {}),
                    success=True,
                    error=None
                )
                
                logger.info(f"✅ {self.agent_name} agent completed query successfully")
                return response
                
            except Exception as e:
                error_msg = f"Error in {self.agent_name} agent: {str(e)}"
                logger.error(f"❌ {error_msg}")
                logger.error(traceback.format_exc())
                
                # Return error response
                return QueryResponse(
                    answer=f"I apologize, but I encountered an error while processing your request: {str(e)}",
                    reasoning=f"The {self.agent_name} agent encountered an unexpected error.",
                    agent_name=self.agent_name,
                    status="error",
                    blocks={},
                    success=False,
                    error=error_msg
                )
        
        @self.app.get("/status")
        async def get_status():
            """Get detailed agent status"""
            return {
                "agent_name": self.agent_name,
                "status": "running",                "capabilities": getattr(self.agent, 'capabilities', []),
                "description": getattr(self.agent, 'description', f"{self.agent_name} agent"),
                "version": getattr(self.agent, 'version', '1.0.0')
            }
        
    async def execute_agent_query(self, query: str, context: Optional[Dict] = None, parameters: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Execute a query using the agent instance
        
        This method should be overridden by specific agent implementations
        if they need custom query processing logic.
        
        Args:
            query: The user query
            context: Optional context information
            parameters: Optional parameters
            
        Returns:
            Dict containing the agent's response
        """
        # Try to call the agent's execute method first
        if hasattr(self.agent, 'execute'):
            return await self.agent.execute(query)
        elif hasattr(self.agent, 'process'):
            # The process method expects (prompt, speech_module) and returns (answer, reasoning)
            answer, reasoning = await self.agent.process(query, None)  # speech_module is None for MCP
            return {
                "answer": answer,
                "reasoning": reasoning,
                "status": "completed",
                "blocks": {}
            }
        else:
            raise NotImplementedError(f"Agent {self.agent_name} does not implement execute() or process() method")
    
    def run(self, port: int):
        """
        Run the agent server
        
        Args:
            port: Port number to run the server on
        """
        logger.info(f"🚀 Starting {self.agent_name} agent server on port {port}")
        
        try:
            uvicorn.run(
                self.app,
                host="127.0.0.1",
                port=port,
                log_level="info",
                access_log=True
            )
        except Exception as e:
            logger.error(f"❌ Failed to start {self.agent_name} agent server: {str(e)}")
            sys.exit(1)

def create_agent_server(agent_name: str, agent_class, port: int):
    """
    Helper function to create and run an agent server
    
    Args:
        agent_name: Name of the agent
        agent_class: The agent class to instantiate
        port: Port to run the server on
    """
    try:
        # Create agent wrapper instance
        agent_wrapper = agent_class()
        
        # Extract the actual agent instance from the wrapper
        actual_agent = None
        if hasattr(agent_wrapper, f'{agent_name}_agent'):
            actual_agent = getattr(agent_wrapper, f'{agent_name}_agent')
        elif hasattr(agent_wrapper, 'browser_agent'):
            actual_agent = agent_wrapper.browser_agent
        elif hasattr(agent_wrapper, 'code_agent'):
            actual_agent = agent_wrapper.code_agent
        elif hasattr(agent_wrapper, 'file_agent'):
            actual_agent = agent_wrapper.file_agent
        elif hasattr(agent_wrapper, 'casual_agent'):
            actual_agent = agent_wrapper.casual_agent
        elif hasattr(agent_wrapper, 'planner_agent'):
            actual_agent = agent_wrapper.planner_agent
        else:
            raise Exception(f"Could not find agent instance in {agent_name} wrapper")
        
        # Create MCP server with the actual agent
        server = BaseMCPAgentServer(agent_name, actual_agent)
        
        # Run the server
        server.run(port)
        
    except Exception as e:
        logger.error(f"❌ Failed to create {agent_name} agent server: {str(e)}")
        logger.error(traceback.format_exc())
        sys.exit(1)

if __name__ == "__main__":
    """Test the base server"""
    
    # Mock agent for testing
    class MockAgent:
        async def execute(self, query: str):
            return {
                "answer": f"Mock response to: {query}",
                "reasoning": "This is a mock agent for testing",
                "status": "completed",
                "blocks": {}
            }
    
    if len(sys.argv) != 2:
        print("Usage: python base_mcp_agent_server.py <port>")
        sys.exit(1)
    
    port = int(sys.argv[1])
    create_agent_server("mock", MockAgent, port)
