#!/usr/bin/env python3
# Letta/memgpt model to Open-Webui OpenAI API server
"""
Put this file where you installed letta container / env- change (last line) port to your needs - run it 
In Open-Webui  admin/settings connections:
add LETTA_MEMGPT as an OpenAI API connection
ie: http://localhost:8088/v1

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

# Add your open-webui user : memgpt corresponding agents / Add {{USER_NAME}} in your Model System Prompt
agents = {
    "admin": "agent-bce9c276-64d7-4337-be57-aadae77d641c",
    "user1": "agent-68e9ff22-4e94-4f0c-a838-f626fa8a6d82"
}

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
    artifacts ="""
Artifacts
"""

    agent_id = agents.get(request.messages[0].content, "NOT FOUND")
				
    #agent_id = "agent-bce9c276-64d7-4337-be57-aadae77d641c"
    response = memgpt_client.send_message(
        agent_id=agent_id,
        message=request.messages[-1].content,
        role="user",
    )
	#LETTA OBJ PARSE
    for message_group in response.messages:
        internal_monologue = None
        function_call_message = None
        function_return = None

        if hasattr(message_group, 'internal_monologue'):
            internal_monologue = f"""
<details>
<summary>Internal Monologue:</summary>
{str(message_group.internal_monologue)} 
</details>\n\n"""

            yield f"data: {json.dumps({'choices': [{'delta': {'role': 'assistant', 'content': f'{internal_monologue}'}}]})}\n\n"
            await asyncio.sleep(0.01)

        if hasattr(message_group, 'function_call'):
            function_call = message_group.function_call
            if function_call.name == 'send_message':
                function_call_message = json.loads(function_call.arguments)['message']
                yield f"data: {json.dumps({'choices': [{'delta': {'role': 'assistant', 'content': f'{function_call_message}'}}]})}\n\n"
                await asyncio.sleep(0.01)

        # Yield function return if present
        #if function_return:
        #    yield f"data: {json.dumps({'choices': [{'delta': {'role': 'assistant', 'content': f'[Function Return] {function_return}'}}]})}\n\n"
        #    await asyncio.sleep(0.01)
			 
    yield f"data: {json.dumps({'choices': [{'delta': {'content': f'{artifacts}'}}]})}\n\n"
    yield f"data: {json.dumps({'choices': [{'finish_reason': 'stop'}]})}\n\n"
    yield "data: [DONE]\n\n"
    artifacts =""

@app.get("/v1/models")
async def models():
    return {"data": [{"created": 1726931162, "id": "LETTA_MEMGPT", "object": "model", "owned_by": "quantumalchemy"}], "object": "list"}

@app.get("/v1")
async def root():
    return {"message": "Welcome to the OpenAI-compatible API"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8088)
