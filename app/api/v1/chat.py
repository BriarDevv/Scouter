import json
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.agent.core import run_agent_turn
from app.agent.events import (
    AgentError,
    ConfirmationRequired,
    TextDelta,
    ToolResult,
    ToolStart,
    TurnComplete,
)
from app.api.deps import get_session
from app.core.logging import get_logger
from app.schemas.chat import (
    ConfirmationRequest,
    ConversationDetail,
    ConversationResponse,
    ConversationSummary,
    MessageResponse,
    SendMessageRequest,
    ToolCallResponse,
)
from app.services.chat_service import (
    create_conversation,
    delete_conversation,
    generate_title,
    get_conversation,
    get_messages,
    list_conversations,
    update_conversation_title,
)

logger = get_logger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post(
    "/conversations", response_model=ConversationResponse, status_code=201
)
def create(db: Session = Depends(get_session)):
    return create_conversation(db)


@router.get("/conversations")
def list_all(
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_session),
) -> list[ConversationSummary]:
    return [
        ConversationSummary(**c) for c in list_conversations(db, limit=limit)
    ]


@router.get("/conversations/{conversation_id}")
def get_detail(
    conversation_id: uuid.UUID,
    db: Session = Depends(get_session),
) -> ConversationDetail:
    conv = get_conversation(db, conversation_id)
    if not conv:
        raise HTTPException(404, "Conversación no encontrada")
    messages = get_messages(db, conversation_id)
    msg_responses = []
    for msg in messages:
        tool_call_responses = [
            ToolCallResponse(
                id=tc.id,
                tool_name=tc.tool_name,
                arguments=tc.arguments_json,
                result=tc.result_json,
                error=tc.error,
                status=tc.status,
                duration_ms=tc.duration_ms,
            )
            for tc in (msg.tool_calls or [])
        ]
        msg_responses.append(
            MessageResponse(
                id=msg.id,
                role=msg.role,
                content=msg.content,
                attachments=msg.attachments_json,
                tool_calls=tool_call_responses,
                model=msg.model,
                created_at=msg.created_at,
            )
        )
    return ConversationDetail(
        id=conv.id,
        channel=conv.channel,
        title=conv.title,
        is_active=conv.is_active,
        created_at=conv.created_at,
        updated_at=conv.updated_at,
        messages=msg_responses,
    )


@router.delete("/conversations/{conversation_id}", status_code=204)
def delete(
    conversation_id: uuid.UUID, db: Session = Depends(get_session)
):
    if not delete_conversation(db, conversation_id):
        raise HTTPException(404, "Conversación no encontrada")


@router.post("/conversations/{conversation_id}/messages")
async def send_message(
    conversation_id: uuid.UUID,
    body: SendMessageRequest,
    db: Session = Depends(get_session),
):
    conv = get_conversation(db, conversation_id)
    if not conv:
        raise HTTPException(404, "Conversación no encontrada")

    # Auto-generate title from first message
    if not conv.title:
        update_conversation_title(
            db, conversation_id, generate_title(body.content)
        )

    async def event_stream():
        try:
            async for event in run_agent_turn(
                conversation_id=conversation_id,
                user_message=body.content,
                db=db,
                channel=conv.channel,
            ):
                if isinstance(event, TextDelta):
                    yield (
                        "event: text_delta\n"
                        f"data: {json.dumps({'content': event.content}, ensure_ascii=False)}\n\n"
                    )
                elif isinstance(event, ToolStart):
                    yield (
                        "event: tool_start\n"
                        f"data: {json.dumps({'tool_name': event.tool_name, 'tool_call_id': event.tool_call_id, 'arguments': event.arguments}, ensure_ascii=False)}\n\n"
                    )
                elif isinstance(event, ToolResult):
                    yield (
                        "event: tool_result\n"
                        f"data: {json.dumps({'tool_call_id': event.tool_call_id, 'tool_name': event.tool_name, 'result': event.result, 'error': event.error}, ensure_ascii=False)}\n\n"
                    )
                elif isinstance(event, ConfirmationRequired):
                    yield (
                        "event: confirmation_required\n"
                        f"data: {json.dumps({'tool_name': event.tool_name, 'tool_call_id': event.tool_call_id, 'arguments': event.arguments, 'description': event.description_es}, ensure_ascii=False)}\n\n"
                    )
                elif isinstance(event, TurnComplete):
                    yield (
                        "event: turn_complete\n"
                        f"data: {json.dumps({'message_id': str(event.message_id)})}\n\n"
                    )
                elif isinstance(event, AgentError):
                    yield (
                        "event: error\n"
                        f"data: {json.dumps({'error': event.error}, ensure_ascii=False)}\n\n"
                    )
        except Exception as exc:
            logger.error("agent_stream_error", error=str(exc))
            yield (
                "event: error\n"
                f"data: {json.dumps({'error': str(exc)})}\n\n"
            )

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
