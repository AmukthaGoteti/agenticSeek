"""
MCP-enabled API Server

Updated version of the main API that uses the MCP-based fault-tolerant router
for enhanced reliability, fault isolation, and hot-swapping capabilities.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
import asyncio
import os
import sys
from typing import Optional, Dict, Any
import logging
from datetime import datetime
from mcp_fault_tolerant_router import fault_tolerant_router

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="AgenticSeek MCP API", version="2.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global state for API responses
latest_answer_data = {
    "answer": "",
    "reasoning": "",
    "agent_name": "",
    "status": "ready",
    "blocks": {},
    "done": False,
    "uid": "",
    "error": None,
    "routing_info": {}
}

current_query = ""
processing_query = False

class QueryRequest(BaseModel):
    """Request model for query endpoint"""
    query: str
    tts_enabled: bool = False
    selected_agent: Optional[str] = None

class AgentRestartRequest(BaseModel):
    """Request model for agent restart endpoint"""
    agent_name: str

@app.on_event("startup")
async def startup_event():
    """Initialize the MCP router on startup"""
    try:
        logger.info("🚀 Starting AgenticSeek MCP API Server...")
        app.include_router(fault_tolerant_router.router)
        await fault_tolerant_router.initialize()
        logger.info("✅ MCP Router initialized successfully")
    except Exception as e:
        logger.error(f"❌ Failed to initialize MCP Router: {str(e)}")
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """Shutdown the MCP router on app shutdown"""
    try:
        logger.info("🛑 Shutting down AgenticSeek MCP API Server...")
        await fault_tolerant_router.shutdown()
        logger.info("✅ MCP Router shutdown complete")
    except Exception as e:
        logger.error(f"❌ Error during shutdown: {str(e)}")

@app.get("/health")
async def health_check():
    """
    Health check endpoint for the API server
    """
    try:
        # Get system status from the router
        system_status = await fault_tolerant_router.get_system_status()
        
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "api_version": "2.0.0",
            "mcp_enabled": True,
            "system_status": system_status
        }
    except Exception as e:
        logger.error(f"❌ Health check failed: {str(e)}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
        )

@app.post("/query")
async def query_endpoint(request: QueryRequest):
    """
    Process a user query using the MCP-based agent system
    """
    global current_query, latest_answer_data, processing_query
    
    try:
        logger.info(f"📝 Received query: {request.query[:100]}...")
        
        # Store query globally
        current_query = request.query
        processing_query = True
        
        # Reset previous data
        latest_answer_data = {
            "answer": "",
            "reasoning": "",
            "agent_name": "",
            "status": "processing",
            "blocks": {},
            "done": False,
            "uid": f"query_{datetime.now().timestamp()}",
            "error": None,
            "routing_info": {}
        }
        
        # Start processing in background
        asyncio.create_task(process_query_background(request))
        
        return {
            "status": "Query received, processing started",
            "uid": latest_answer_data["uid"],
            "mcp_enabled": True
        }
        
    except Exception as e:
        logger.error(f"❌ Error in query endpoint: {str(e)}")
        processing_query = False
        raise HTTPException(status_code=500, detail=str(e))

async def process_query_background(request: QueryRequest):
    """
    Process the query in the background using the MCP router
    """
    global latest_answer_data, processing_query
    
    try:
        logger.info(f"🔄 Processing query with MCP router: {request.query[:100]}...")
        
        # Route query through the fault-tolerant router
        result = await fault_tolerant_router.route_query(
            query=request.query,
            selected_agent=request.selected_agent
        )
        
        # Update global state with result
        latest_answer_data.update({
            "answer": result.get("answer", ""),
            "reasoning": result.get("reasoning", ""),
            "agent_name": result.get("agent_name", "unknown"),
            "status": result.get("status", "completed"),
            "blocks": result.get("blocks", {}),
            "done": True,
            "error": result.get("error"),
            "routing_info": result.get("routing_info", {})
        })
        
        logger.info(f"✅ Query processed successfully by {result.get('agent_name', 'unknown')} agent")
        
    except Exception as e:
        error_msg = f"Error processing query: {str(e)}"
        logger.error(f"❌ {error_msg}")
        
        # Update global state with error
        latest_answer_data.update({
            "answer": f"I apologize, but I encountered an error: {str(e)}",
            "reasoning": "The system experienced an unexpected error during processing.",
            "agent_name": "system",
            "status": "error",
            "blocks": {},
            "done": True,
            "error": error_msg,
            "routing_info": {"error": True}
        })
    finally:
        processing_query = False

@app.get("/latest_answer")
async def get_latest_answer():
    """
    Get the latest answer from the agent system
    """
    return latest_answer_data

@app.get("/system_status")
async def get_system_status():
    """
    Get comprehensive system status including all agents
    """
    try:
        status = await fault_tolerant_router.get_system_status()
        return {
            "api_status": "running",
            "mcp_enabled": True,
            "processing_query": processing_query,
            "current_query": current_query[:100] + "..." if len(current_query) > 100 else current_query,
            "system": status
        }
    except Exception as e:
        logger.error(f"❌ Error getting system status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/restart_agent")
async def restart_agent(request: AgentRestartRequest):
    """
    Manually restart a specific agent
    """
    try:
        logger.info(f"🔄 Manual restart requested for {request.agent_name} agent")
        
        result = await fault_tolerant_router.restart_agent(request.agent_name)
        
        if result["success"]:
            return {
                "status": "success",
                "message": f"Agent {request.agent_name} restarted successfully",
                "agent": request.agent_name
            }
        else:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to restart agent {request.agent_name}: {result.get('error', 'Unknown error')}"
            )
            
    except Exception as e:
        logger.error(f"❌ Error restarting agent {request.agent_name}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/stop")
async def stop_processing():
    """
    Stop current processing (legacy endpoint for frontend compatibility)
    """
    global processing_query
    
    logger.info("🛑 Stop processing requested")
    processing_query = False
    
    return {
        "status": "Processing stopped",
        "message": "Current query processing has been interrupted"
    }

@app.post("/kill_process")
async def kill_process():
    """
    Emergency stop for all processing (legacy endpoint for frontend compatibility)
    """
    global processing_query, latest_answer_data
    
    logger.warning("🚨 Emergency kill process requested")
    processing_query = False
    
    # Update status
    latest_answer_data.update({
        "status": "terminated",
        "answer": "Process terminated by user request",
        "done": True
    })
    
    return {
        "status": "Process killed",
        "message": "All processing has been terminated"
    }

@app.get("/screenshots/{filename}")
async def get_screenshot(filename: str):
    """
    Serve screenshot files (legacy endpoint for browser agent compatibility)
    """
    screenshot_path = os.path.join(".screenshots", filename)
    
    if os.path.exists(screenshot_path):
        return FileResponse(screenshot_path)
    else:
        # Return placeholder or 404
        raise HTTPException(status_code=404, detail="Screenshot not found")

@app.get("/agent_logs/{agent_name}")
async def get_agent_logs(agent_name: str):
    """
    Get logs for a specific agent (new endpoint for debugging)
    """
    try:
        # This would be enhanced to read actual agent logs
        return {
            "agent": agent_name,
            "logs": f"Logs for {agent_name} agent would be displayed here",
            "message": "Log retrieval not yet implemented"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    
    logger.info("🚀 Starting AgenticSeek MCP API Server...")
    
    try:
        uvicorn.run(
            "mcp_api:app",
            host="0.0.0.0",
            port=8000,
            reload=False,  # Disable reload to prevent issues with background tasks
            log_level="info"
        )
    except KeyboardInterrupt:
        logger.info("🛑 Server shutdown requested")
    except Exception as e:
        logger.error(f"❌ Server error: {str(e)}")
        sys.exit(1)
