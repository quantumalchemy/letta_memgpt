#!/usr/bin/env python3
# Letta/memgpt model to Open-Webui OpenAI API server
"""
Put this file where you installed letta container / env- change (last line) port to your needs - run it 
In Open-Webui  admin/settings connections:
add LETTA_MEMGPT as an OpenAI API connection
ie: http://localhost:8088/v1 (or http://your-network:8088/v1 )

open-webui users Must correspond with your letta agents names / Add {{USER_NAME}} in your Model System Prompt

"""

from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional
import asyncio
import json
from letta import create_client

app = FastAPI()
memgpt_client = create_client()

class Message(BaseModel):
    role: str
    content: str

class ChatCompletionRequest(BaseModel):
    model: str
    messages: List[Message]
    temperature: Optional[float] = 1.0
    max_tokens: Optional[int] = 100
    stream: Optional[bool] = False

@app.post("/v1/chat/completions")
async def chat_completion(request: ChatCompletionRequest):
    return StreamingResponse(stream_response(request), media_type="text/event-stream")

async def stream_response(request: ChatCompletionRequest):
    if "#NONE#" in str(request.messages[-1].content):  
        yield "data: [DONE]\n\n"
        return
        
    # get agent id from model sys message ** open-webui users Must correspond with your letta agents names / Add {{USER_NAME}} in your Model System Prompt
    agent_id = memgpt_client.get_agent_id(request.messages[0].content)
    if not agent_id:  
        yield f"data: {json.dumps({'choices': [{'delta': {'role': 'assistant', 'content': f'No Agent'}}]})}\n\n"
        yield f"data: {json.dumps({'choices': [{'finish_reason': 'stop'}]})}\n\n"
        yield "data: [DONE]\n\n"
        return 
    try:
        response = memgpt_client.send_message(
            message=request.messages[-1].content,
            message=prompt,
            role="user",
        )
        
        for message_group in response.messages:
            internal_monologue = ""
            tool_call_message  = ""
            function_return = ""
            
            
            if hasattr(message_group, 'reasoning'):
                internal_monologue = str(message_group.reasoning)
                internal_monologue = f"""
<details>
<summary>Internal Monologue:</summary>
{internal_monologue}
</details>\n\n"""

            if hasattr(message_group, 'tool_call'):
                tool_call = message_group.tool_call
                if tool_call.name == 'send_message':
                    tool_call_message = json.loads(tool_call.arguments)['message']
                    


            yield f"data: {json.dumps({'choices': [{'delta': {'role': 'assistant', 'content': f'{internal_monologue}'}}]})}\n\n"
            await asyncio.sleep(0.01)
                    
            yield f"data: {json.dumps({'choices': [{'delta': {'role': 'assistant', 'content': f'{tool_call_message}'}}]})}\n\n"
            await asyncio.sleep(0.01)

        

    except json.JSONDecodeError as e: #except Exception as e:
         
        #print(f"Error memgpt_client.send_message: {e}", file=log, flush=True)
        artifacts =""
        yield f"data: {json.dumps({'choices': [{'delta': {'content': 'There was a problem Please click Regenerate to recover the response' }}]})}\n\n"
        pass
                
    await asyncio.sleep(0.01)
    yield f"data: {json.dumps({'choices': [{'delta': {'content': f'{artifacts}'}}]})}\n\n"
    yield f"data: {json.dumps({'choices': [{'finish_reason': 'stop'}]})}\n\n"
    yield "data: [DONE]\n\n"

@app.get("/v1/models")
async def models():
    return {"data": [{"created": 1726931162, "id": "LETTA_MEMGPT", "object": "model", "owned_by": "quantumalchemy"}], "object": "list"}

@app.get("/v1")
async def root():
    return {"message": "Welcome to the OpenAI-compatible API"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8088)
