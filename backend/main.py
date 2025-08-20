from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import os
import json
import uuid
import hashlib
from datetime import datetime
import xml.etree.ElementTree as ET

from pathlib import Path

# Import user's compression algorithm module¬
try:
    from compressor import ContextCompressor
except ImportError as e:
    # If import fails, use simplified version
    print(f"Warning: Unable to import user-provided compression module: {e}")
    print("Will use simplified version")
    

app = FastAPI(title="Context Compression System", version="1.0.0")

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins in development environment
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Data models
class CompressionRequest(BaseModel):
    role: str = "system"  # Only meaningful in HISTORY section
    section: str  # BACKGROUND, PLAN, SUB_APP, HISTORY
    content: str
    target_modules: List[str] = ["all"]
    use_tf_idf: bool = False
    use_history_compression: bool = False
    max_token: int = 1000
    
    # TF-IDF compression parameters
    tf_idf_compression_ratio: float = 0.6  # TF-IDF compression retention ratio (0.1-1.0), default 0.6 means retain 60% of sentences
    
    # History compression parameters
    history_preserve_tokens: int = 500  # Number of latest tokens to preserve in history compression, default 500
    history_compression_ratio: float = 0.3  # Compression ratio for old content in history compression (0.1-1.0), default 0.3 means compress to 30%
    
    # User identifier (optional, auto-generated if not provided)
    user_id: Optional[str] = None
    
    openai_api_key: Optional[str] = None  # API key
    openai_base_url: Optional[str] = None  # API base URL

class CompressionResponse(BaseModel):
    success: bool
    original_content: str
    compressed_content: str
    compression_ratio: float
    token_count_original: int
    token_count_compressed: int
    file_path: str
    message: str

# Ensure data directory exists
CURRENT_DIR = Path(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = CURRENT_DIR.parent / "data"  # Use absolute path of current file
DATA_DIR.mkdir(parents=True, exist_ok=True)

print(f"📁 Data directory: {DATA_DIR.absolute()}")

def generate_user_id(request_info: str = None) -> str:
    """Generate or get user ID"""
    if request_info:
        # Generate consistent user ID based on request info
        hash_object = hashlib.md5(request_info.encode())
        return hash_object.hexdigest()[:12]
    else:
        # Generate random user ID
        return str(uuid.uuid4())[:12]

def get_user_data_dir(user_id: str) -> Path:
    """Get user-specific data directory"""
    user_dir = DATA_DIR / f"user_{user_id}"
    user_dir.mkdir(parents=True, exist_ok=True)
    return user_dir

def get_user_files(user_id: str) -> Dict[str, Path]:
    """Get user-specific file paths"""
    user_dir = get_user_data_dir(user_id)
    return {
        'context': user_dir / "context.xml",
        'before_compressed': user_dir / "before_compressed.xml",
        'tf_idf_compressed': user_dir / "tf_idf_compressed.xml",
        'history_compressed': user_dir / "history_compressed.xml"
    }

def initialize_context_file(context_file_path: Path):
    """Initialize context.xml file, create basic structure if it doesn't exist"""
    if not context_file_path.exists():
        root = ET.Element("context")
        
        # Create four main sections
        ET.SubElement(root, "BACKGROUND")
        ET.SubElement(root, "PLAN")
        ET.SubElement(root, "SUB_APP")
        ET.SubElement(root, "HISTORY")
        
        # Save initial file
        tree = ET.ElementTree(root)
        tree.write(context_file_path, encoding='utf-8', xml_declaration=True)
        
def add_content_to_section(section: str, content: str, role: str = "system", user_id: str = None) -> str:
    """Add content to specified section"""
    # Get user file paths
    user_files = get_user_files(user_id)
    context_file_path = user_files['context']
    
    # Ensure file exists
    initialize_context_file(context_file_path)
    
    # Read file content (as string to avoid ElementTree escaping)
    with open(context_file_path, 'r', encoding='utf-8') as f:
        xml_content = f.read()
    
    # Add content based on different section types
    if section == "BACKGROUND":
        xml_content = add_background_content_raw(xml_content, content, role)
    elif section == "PLAN":
        xml_content = add_plan_content_raw(xml_content, content, role)
    elif section == "SUB_APP":
        xml_content = add_subapp_content_raw(xml_content, content, role)
    elif section == "HISTORY":
        xml_content = add_history_content_raw(xml_content, content, role)
    
            # Save file
    with open(context_file_path, 'w', encoding='utf-8') as f:
        f.write(xml_content)
    
    return xml_content

def add_background_content_raw(xml_content: str, content: str, role: str) -> str:
    """Add BACKGROUND section content (string processing method)"""
    try:
        # Try to parse as JSON format structured data
        structured_data = json.loads(content)
        system_prompt = structured_data.get('system_prompt', '')
        task = structured_data.get('task', '')
        knowledge = structured_data.get('knowledge', '')
        external_knowledge = structured_data.get('external_knowledge', '')
        
        timestamp = datetime.now().isoformat()
        new_content = f'''    <content timestamp="{timestamp}">
        <system_prompt>
            {system_prompt}
        </system_prompt>
        <task>
            {task}
        </task>
        <knowledge>
            {knowledge}
        </knowledge>
        <external_knowledge>
            {external_knowledge}
        </external_knowledge>
    </content>'''
    except json.JSONDecodeError:
        # If not JSON, process in original way
        timestamp = datetime.now().isoformat()
        new_content = f'''    <content role="{role}" timestamp="{timestamp}">{content}</content>'''
    
    if "</BACKGROUND>" in xml_content:
        xml_content = xml_content.replace("</BACKGROUND>", f"{new_content}\n    </BACKGROUND>")
    else:
        xml_content = xml_content.replace("<BACKGROUND />", f"<BACKGROUND>\n{new_content}\n    </BACKGROUND>")
        xml_content = xml_content.replace("<BACKGROUND></BACKGROUND>", f"<BACKGROUND>\n{new_content}\n    </BACKGROUND>")
    
    return xml_content

def add_plan_content_raw(xml_content: str, content: str, role: str) -> str:
    """Add PLAN section content (string processing method)"""
    import re
    
    try:
        # Try to parse as JSON format structured data
        structured_data = json.loads(content)
        steps = structured_data.get('steps', [])
        call_ask = structured_data.get('call_ask', '')
        
        # Calculate current iteration number
        iteration_count = len(re.findall(r'<plan_iteration number="(\d+)"', xml_content)) + 1
        timestamp = datetime.now().isoformat()
        
        # Build steps XML
        steps_xml = '\n'.join([f'                <step>{step}</step>' for step in steps if step.strip()])
        
        new_content = f'''    <plan_iteration number="{iteration_count}" role="{role}" timestamp="{timestamp}">
        <steps>
{steps_xml}
        </steps>
    </plan_iteration>'''
        
        # If call_ask exists, add to content
        if call_ask.strip():
            new_content += f'\n    <call_ask>{call_ask}</call_ask>'
            
    except json.JSONDecodeError:
        # If not JSON, process in original way
        iteration_count = len(re.findall(r'<plan_iteration number="(\d+)"', xml_content)) + 1
        timestamp = datetime.now().isoformat()
        
        new_content = f'''    <plan_iteration number="{iteration_count}" role="{role}" timestamp="{timestamp}">
        <steps>{content}</steps>
    </plan_iteration>'''
    
    # Insert content before </PLAN>
    if "</PLAN>" in xml_content:
        xml_content = xml_content.replace("</PLAN>", f"{new_content}\n    </PLAN>")
    else:
        xml_content = xml_content.replace("<PLAN />", f"<PLAN>\n{new_content}\n    </PLAN>")
        xml_content = xml_content.replace("<PLAN></PLAN>", f"<PLAN>\n{new_content}\n    </PLAN>")
    
    return xml_content

def add_subapp_content_raw(xml_content: str, content: str, role: str) -> str:
    """Add SUB_APP section content (string processing method)"""
    import re
    
    try:
        # Try to parse as JSON format structured data
        structured_data = json.loads(content)
        app_name = structured_data.get('app_name', '')
        app_content = structured_data.get('content', '')
        
        timestamp = datetime.now().isoformat()
        
        new_content = f'''    <agent name="{app_name}" timestamp="{timestamp}">
        <content>{app_content}</content>
    </agent>'''
        
        print(f"📝 Adding SUB_APP using structured data: {app_name}")
        
    except json.JSONDecodeError:
        # If not JSON, check if already in agent format
        content_stripped = content.strip()
        is_agent_format = content_stripped.startswith('<agent') and '</agent>' in content_stripped
        
        if is_agent_format:
            # If in agent format, add directly
            new_content = f"    {content_stripped}"
            print(f"📝 Detected agent format, adding directly")
        else:
            # If plain text, wrap in agent format
            agent_count = len(re.findall(r'<agent name="([^"]*)"', xml_content)) + 1
            agent_name = f"agent_{role}_{agent_count}"
            timestamp = datetime.now().isoformat()
            
            new_content = f'''    <agent name="{agent_name}" timestamp="{timestamp}">
        <content>{content}</content>
    </agent>'''
            print(f"📝 包装普通文本为 agent 格式: {agent_name}")
    
    # Insert content before </SUB_APP>
    if "</SUB_APP>" in xml_content:
        xml_content = xml_content.replace("</SUB_APP>", f"{new_content}\n    </SUB_APP>")
    else:
        xml_content = xml_content.replace("<SUB_APP />", f"<SUB_APP>\n{new_content}\n    </SUB_APP>")
        xml_content = xml_content.replace("<SUB_APP></SUB_APP>", f"<SUB_APP>\n{new_content}\n    </SUB_APP>")
    
    return xml_content

def add_history_content_raw(xml_content: str, content: str, role: str) -> str:
    """Add HISTORY section content (string processing method)"""
    timestamp = datetime.now().isoformat()
    new_content = f'''    <entry role="{role}" timestamp="{timestamp}">{content}</entry>'''
    
    # Insert content before </HISTORY>
    if "</HISTORY>" in xml_content:
        xml_content = xml_content.replace("</HISTORY>", f"{new_content}\n    </HISTORY>")
    else:
        xml_content = xml_content.replace("<HISTORY />", f"<HISTORY>\n{new_content}\n    </HISTORY>")
        xml_content = xml_content.replace("<HISTORY></HISTORY>", f"<HISTORY>\n{new_content}\n    </HISTORY>")
    
    return xml_content

def get_context_file_content(user_id: str = None) -> str:
    """Get complete context.xml file content"""
    user_files = get_user_files(user_id)
    context_file_path = user_files['context']
    
    if not context_file_path.exists():
        initialize_context_file(context_file_path)
    
    with open(context_file_path, 'r', encoding='utf-8') as f:
        return f.read()

@app.get("/")
async def root():
    return {"message": "Context Compression System API", "version": "1.0.0"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

@app.get("/user-info")
async def get_user_info(user_agent: str = Header(None), user_id: Optional[str] = None):
    """Get user information"""
    if not user_id:
        user_id = generate_user_id(user_agent or "default")
    
    user_dir = get_user_data_dir(user_id)
    files_count = len(list(user_dir.glob("*.xml")))
    
    return {
        "user_id": user_id, 
        "user_dir": str(user_dir.relative_to(DATA_DIR)),
        "files_count": files_count,
        "user_agent_hash": hashlib.md5((user_agent or "default").encode()).hexdigest()[:8]
    }

@app.post("/compress", response_model=CompressionResponse)
async def compress_context(request: CompressionRequest, user_agent: str = Header(None)):
    try:
        # Generate or get user ID
        if request.user_id:
            user_id = request.user_id
        else:
            # Generate consistent user ID based on User-Agent, same browser gets same ID
            user_id = generate_user_id(user_agent or "default")
        
        print(f"👤 User ID: {user_id}")
        
        # Get user file paths
        user_files = get_user_files(user_id)
        
        # Add content to corresponding section
        xml_content = add_content_to_section(request.section, request.content, request.role, user_id)
        
        # Get complete context.xml content for compression
        full_context_content = get_context_file_content(user_id)
        
        # Backup content before compression to before_compressed.xml
        print(f"📄 Backing up content to {user_files['before_compressed']}")
        with open(user_files['before_compressed'], 'w', encoding='utf-8') as f:
            f.write(full_context_content)
        
        # Create compressor instance (using API configuration from request)
        compressor = ContextCompressor(
            api_key=request.openai_api_key,
            base_url=request.openai_base_url,
            use_tf_idf=request.use_tf_idf,
            use_history_compression=request.use_history_compression
        )
        
        # Compression configuration
        config = {
            'target_modules': request.section,
            'use_tf_idf': request.use_tf_idf,
            'use_history_compression': request.use_history_compression,
            'max_token': request.max_token,
            'tf_idf_compression_ratio': request.tf_idf_compression_ratio,
            'history_preserve_tokens': request.history_preserve_tokens,
            'history_compression_ratio': request.history_compression_ratio,
            'user_files': user_files
        }
        
        # Execute compression - pass complete XML file content
        compressed_content = compressor.compress_content(full_context_content, config)
        
        # Directly overwrite context.xml with compression result
        print(f"💾 Overwriting {user_files['context']} with compression result")
        with open(user_files['context'], 'w', encoding='utf-8') as f:
            f.write(compressed_content)
        
        # Calculate token counts
        original_tokens = compressor.count_tokens(full_context_content)
        compressed_tokens = compressor.count_tokens(compressed_content)
        
        # Calculate compression ratio
        compression_ratio = (original_tokens - compressed_tokens) / original_tokens if original_tokens > 0 else 0
        
        has_api_key = bool(request.openai_api_key and request.openai_api_key.strip())
        compression_method = 'LLM Intelligent Compression' if (hasattr(compressor, 'client') and compressor.client and has_api_key) else 'Traditional Compression Method'
        
        return CompressionResponse(
            success=True,
            original_content=full_context_content,
            compressed_content=compressed_content,
            compression_ratio=round(compression_ratio, 3),
            token_count_original=original_tokens,
            token_count_compressed=compressed_tokens,
            file_path=f"user_{user_id}/context.xml",  # User-specific file path
            message=f"User {user_id}: Added to {request.section} section, using {compression_method}, compression ratio: {compression_ratio:.1%}. Original content backed up to before_compressed.xml, compression result overwrote context.xml"
        )
        
    except Exception as e:
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail=f"Compression processing failed: {str(e)}")

@app.get("/files")
async def list_files(user_agent: str = Header(None), user_id: Optional[str] = None):
    """List user's XML files"""
    try:
        # Generate or obtain a user ID
        if not user_id:
            user_id = generate_user_id(user_agent or "default")
        
        user_dir = get_user_data_dir(user_id)
        files = []
        
        for file_path in user_dir.glob("*.xml"):
            stat = file_path.stat()
            files.append({
                "name": file_path.name,
                "size": stat.st_size,
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "user_id": user_id
            })
        return {"files": files, "user_id": user_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get file list: {str(e)}")

@app.get("/file/{filename}")
async def get_file(filename: str, user_agent: str = Header(None), user_id: Optional[str] = None):
    """Get specified file content"""
    try:
        # Generate or obtain a user ID
        if not user_id:
            user_id = generate_user_id(user_agent or "default")
        
        user_dir = get_user_data_dir(user_id)
        file_path = user_dir / filename
        
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="File does not exist")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        return {"filename": filename, "content": content, "user_id": user_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read file: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)