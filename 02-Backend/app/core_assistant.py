"""Core AI Assistant Phase 1 routes."""

import io
import json
import re
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, status, Header, UploadFile, File, Form, Query
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel, Field
from openai import OpenAI

from app.utils.auth.auth_utils import get_user_id_from_token
from app.repositories.database.client import (
    get_user_profile,
    update_user_profile,
    get_user_settings,
    update_user_settings,
    get_conversations,
    get_conversation,
    update_conversation,
    create_conversation,
    get_messages,
    create_message,
    delete_conversation,
    save_memory,
    get_user_memory,
)
from app.repositories.database.supabase_client import get_supabase

router = APIRouter(prefix="/api/core", tags=["core-assistant"])

openai_client = OpenAI()
supabase = get_supabase()


# ============================================================================
# Schemas
# ============================================================================

class ProfileUpdateRequest(BaseModel):
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None
    bio: Optional[str] = None
    website: Optional[str] = None


class SettingsUpdateRequest(BaseModel):
    theme: Optional[str] = None
    language: Optional[str] = None
    default_model: Optional[str] = None
    notifications_enabled: Optional[bool] = None
    voice_enabled: Optional[bool] = None


class FolderCreateRequest(BaseModel):
    name: str = Field(..., max_length=100)
    color: Optional[str] = "#0ea5e9"


class FolderUpdateRequest(BaseModel):
    name: Optional[str] = Field(None, max_length=100)
    color: Optional[str] = None


class ShareConversationRequest(BaseModel):
    conversation_id: str
    shared_with_user_ids: list[str] = []


class SearchConversationsRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=200)
    limit: int = Field(default=20, ge=1, le=100)


class MemoryHookRequest(BaseModel):
    content: str = Field(..., max_length=4000)
    importance: int = Field(default=1, ge=1, le=5)


# ============================================================================
# User Profile
# ============================================================================

@router.get("/profile")
async def get_profile(authorization: str = Header(None)):
    user_id = get_user_id_from_token(authorization)
    profile = await get_user_profile(user_id)
    if not profile:
        return {"status": "OK", "profile": None}
    return {"status": "OK", "profile": profile}


@router.patch("/profile")
async def update_profile(request: ProfileUpdateRequest, authorization: str = Header(None)):
    user_id = get_user_id_from_token(authorization)
    kwargs = request.dict(exclude_none=True)
    if not kwargs:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields to update")
    profile = await update_user_profile(user_id, **kwargs)
    if not profile:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to update profile")
    return {"status": "OK", "profile": profile}


# ============================================================================
# User Settings (theme, language, etc.)
# ============================================================================

@router.get("/settings")
async def get_settings(authorization: str = Header(None)):
    user_id = get_user_id_from_token(authorization)
    settings = await get_user_settings(user_id)
    if not settings:
        return {"status": "OK", "settings": {
            "theme": "dark",
            "language": "en",
            "default_model": None,
            "notifications_enabled": True,
            "voice_enabled": False,
        }}
    return {"status": "OK", "settings": settings}


@router.patch("/settings")
async def update_settings(request: SettingsUpdateRequest, authorization: str = Header(None)):
    user_id = get_user_id_from_token(authorization)
    kwargs = request.dict(exclude_none=True)
    if not kwargs:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields to update")
    settings = await update_user_settings(user_id, **kwargs)
    if not settings:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to update settings")
    return {"status": "OK", "settings": settings}


# ============================================================================
# Conversation Folders
# ============================================================================

@router.post("/folders")
async def create_folder(request: FolderCreateRequest, authorization: str = Header(None)):
    user_id = get_user_id_from_token(authorization)
    try:
        supabase = get_supabase()
        response = (
            supabase.table("conversation_folders")
            .insert({"user_id": user_id, "name": request.name, "color": request.color or "#0ea5e9"})
            .execute()
        )
        folder = response.data[0] if response.data else None
        if not folder:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create folder")
        return {"status": "OK", "folder": folder}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to create folder: {str(e)[:100]}") from e


@router.get("/folders")
async def list_folders(authorization: str = Header(None)):
    user_id = get_user_id_from_token(authorization)
    try:
        supabase = get_supabase()
        response = (
            supabase.table("conversation_folders")
            .select("*")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .execute()
        )
        return {"status": "OK", "folders": response.data}
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to fetch folders: {str(e)[:100]}") from e


@router.patch("/folders/{folder_id}")
async def update_folder(folder_id: str, request: FolderUpdateRequest, authorization: str = Header(None)):
    user_id = get_user_id_from_token(authorization)
    kwargs = request.dict(exclude_none=True)
    if not kwargs:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields to update")
    try:
        supabase = get_supabase()
        response = (
            supabase.table("conversation_folders")
            .update(kwargs)
            .eq("id", folder_id)
            .eq("user_id", user_id)
            .execute()
        )
        folder = response.data[0] if response.data else None
        if not folder:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Folder not found")
        return {"status": "OK", "folder": folder}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to update folder: {str(e)[:100]}") from e


@router.delete("/folders/{folder_id}")
async def delete_folder(folder_id: str, authorization: str = Header(None)):
    user_id = get_user_id_from_token(authorization)
    try:
        supabase = get_supabase()
        supabase.table("conversation_folders").delete().eq("id", folder_id).eq("user_id", user_id).execute()
        return {"status": "OK", "message": "Folder deleted"}
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to delete folder: {str(e)[:100]}") from e


# ============================================================================
# Pin Conversations
# ============================================================================

@router.post("/conversations/{conversation_id}/pin")
async def pin_conversation(conversation_id: str, authorization: str = Header(None)):
    user_id = get_user_id_from_token(authorization)
    conv = await get_conversation(conversation_id, user_id)
    if not conv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    updated = await update_conversation(conversation_id, is_pinned=True)
    return {"status": "OK", "conversation": updated}


@router.delete("/conversations/{conversation_id}/pin")
async def unpin_conversation(conversation_id: str, authorization: str = Header(None)):
    user_id = get_user_id_from_token(authorization)
    conv = await get_conversation(conversation_id, user_id)
    if not conv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    updated = await update_conversation(conversation_id, is_pinned=False)
    return {"status": "OK", "conversation": updated}


# ============================================================================
# Move Conversation to Folder
# ============================================================================

class MoveConversationRequest(BaseModel):
    folder_id: Optional[str] = None


@router.patch("/conversations/{conversation_id}/folder")
async def move_conversation_to_folder(conversation_id: str, request: MoveConversationRequest, authorization: str = Header(None)):
    user_id = get_user_id_from_token(authorization)
    conv = await get_conversation(conversation_id, user_id)
    if not conv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    if request.folder_id:
        try:
            supabase = get_supabase()
            folder = supabase.table("conversation_folders").select("id").eq("id", request.folder_id).eq("user_id", user_id).execute()
            if not folder.data:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Folder not found")
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to verify folder") from e
    updated = await update_conversation(conversation_id, folder_id=request.folder_id)
    return {"status": "OK", "conversation": updated}


# ============================================================================
# Share Conversations
# ============================================================================

@router.post("/conversations/share")
async def share_conversation(request: ShareConversationRequest, authorization: str = Header(None)):
    user_id = get_user_id_from_token(authorization)
    conv = await get_conversation(request.conversation_id, user_id)
    if not conv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    try:
        supabase = get_supabase()
        response = (
            supabase.table("conversations")
            .update({"is_shared": True, "shared_at": datetime.now(timezone.utc).isoformat(), "shared_with": request.shared_with_user_ids})
            .eq("id", request.conversation_id)
            .execute()
        )
        return {"status": "OK", "conversation": response.data[0] if response.data else conv}
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to share conversation: {str(e)[:100]}") from e


@router.get("/conversations/shared")
async def list_shared_conversations(authorization: str = Header(None)):
    user_id = get_user_id_from_token(authorization)
    try:
        supabase = get_supabase()
        response = (
            supabase.table("conversations")
            .select("*")
            .or_(f"user_id.eq.{user_id},shared_with.cs.{{{user_id}}}")
            .eq("is_shared", True)
            .order("updated_at", desc=True)
            .execute()
        )
        return {"status": "OK", "conversations": response.data, "count": len(response.data)}
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to fetch shared conversations: {str(e)[:100]}") from e


# ============================================================================
# Search Conversations
# ============================================================================

@router.post("/conversations/search")
async def search_conversations(request: SearchConversationsRequest, authorization: str = Header(None)):
    user_id = get_user_id_from_token(authorization)
    query = request.query.strip()
    if not query:
        return {"status": "OK", "results": [], "count": 0}
    try:
        supabase = get_supabase()
        conv_response = (
            supabase.table("conversations")
            .select("*")
            .eq("user_id", user_id)
            .ilike("title", f"%{query}%")
            .order("updated_at", desc=True)
            .limit(request.limit)
            .execute()
        )
        msg_response = (
            supabase.table("messages")
            .select("conversation_id, content, created_at, conversations!inner(*)")
            .eq("user_id", user_id)
            .ilike("content", f"%{query}%")
            .order("created_at", desc=True)
            .limit(request.limit)
            .execute()
        )
        conv_results = conv_response.data or []
        msg_results = []
        for m in (msg_response.data or []):
            conv = m.get("conversations")
            if conv:
                msg_results.append({
                    "id": conv["id"],
                    "title": conv.get("title", "Untitled"),
                    "snippet": m["content"][:200],
                    "matched_at": m["created_at"],
                })
        combined = {r["id"]: r for r in conv_results}
        for r in msg_results:
            if r["id"] not in combined:
                combined[r["id"]] = r
        results = list(combined.values())[: request.limit]
        return {"status": "OK", "results": results, "count": len(results)}
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Search failed: {str(e)[:100]}") from e


# ============================================================================
# Export Chats
# ============================================================================

@router.post("/conversations/{conversation_id}/export")
async def export_conversation(conversation_id: str, authorization: str = Header(None), fmt: str = Query("json")):
    user_id = get_user_id_from_token(authorization)
    conv = await get_conversation(conversation_id, user_id)
    if not conv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    messages = await get_messages(conversation_id, limit=1000)
    if fmt == "json":
        payload = json.dumps({"conversation": conv, "messages": messages}, indent=2, default=str)
        media_type = "application/json"
        filename = f"conversation_{conversation_id}.json"
    elif fmt == "markdown":
        lines = [f"# {conv.get('title', 'Conversation')}\n"]
        for msg in messages:
            role = msg.get("role", "unknown")
            lines.append(f"## {role}\n")
            lines.append(msg.get("content", ""))
            lines.append("\n")
        payload = "\n".join(lines)
        media_type = "text/markdown"
        filename = f"conversation_{conversation_id}.md"
    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported format. Use json or markdown.")
    try:
        supabase = get_supabase()
        supabase.table("chat_exports").insert({
            "user_id": user_id,
            "conversation_id": conversation_id,
            "format": fmt,
        }).execute()
    except Exception:
        pass
    return StreamingResponse(
        io.StringIO(payload),
        media_type=media_type,
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


# ============================================================================
# Voice: Text-to-Speech
# ============================================================================

class TTSRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=4000)
    voice: str = Field(default="alloy")


@router.post("/voice/tts")
async def text_to_speech(request: TTSRequest, authorization: str = Header(None)):
    get_user_id_from_token(authorization)
    try:
        response = openai_client.audio.speech.create(model="tts-1", voice=request.voice, input=request.text)
        return StreamingResponse(
            io.BytesIO(response.content),
            media_type="audio/mpeg",
            headers={"Content-Disposition": f"attachment; filename=tts_{uuid.uuid4().hex}.mp3"},
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"TTS failed: {str(e)[:100]}") from e


# ============================================================================
# Voice: Speech-to-Text
# ============================================================================

@router.post("/voice/stt")
async def speech_to_text(file: UploadFile = File(...), authorization: str = Header(None)):
    get_user_id_from_token(authorization)
    try:
        content = await file.read()
        if len(content) > 25 * 1024 * 1024:
            raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Audio file too large")
        audio_file = io.BytesIO(content)
        audio_file.name = file.filename or "audio.webm"
        transcript = openai_client.audio.transcriptions.create(model="whisper-1", file=audio_file)
        return {"status": "OK", "text": transcript.text}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"STT failed: {str(e)[:100]}") from e


# ============================================================================
# Image Understanding
# ============================================================================

class ImageAnalyzeRequest(BaseModel):
    image_url: str = Field(..., min_length=1, max_length=2000)
    prompt: str = Field(..., min_length=1, max_length=2000)


@router.post("/vision/analyze")
async def analyze_image(request: ImageAnalyzeRequest, authorization: str = Header(None)):
    get_user_id_from_token(authorization)
    try:
        response = openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that analyzes images."},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": request.prompt},
                        {"type": "image_url", "image_url": {"url": request.image_url}},
                    ],
                },
            ],
            max_tokens=1000,
        )
        return {"status": "OK", "result": response.choices[0].message.content or ""}
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Image analysis failed: {str(e)[:100]}") from e


# ============================================================================
# File Upload for Chat
# ============================================================================

@router.post("/upload")
async def upload_file(file: UploadFile = File(...), authorization: str = Header(None)):
    user_id = get_user_id_from_token(authorization)
    ALLOWED = {"image/png", "image/jpeg", "image/webp", "application/pdf", "text/plain", "text/markdown"}
    if file.content_type not in ALLOWED:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported file type")
    try:
        content = await file.read()
        if len(content) > 20 * 1024 * 1024:
            raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="File too large")
        safe_name = re.sub(r'[^a-zA-Z0-9._-]', '_', file.filename or "file")
        path = f"user/{user_id}/chat/{uuid.uuid4().hex}_{safe_name}"
        supabase = get_supabase()
        storage = supabase.storage.from_("chat-uploads")
        storage.upload(path, content, {"content-type": file.content_type or "application/octet-stream"})
        public_url = supabase.storage.from_("chat-uploads").get_public_url(path)
        return {"status": "OK", "file": {"filename": file.filename, "content_type": file.content_type, "size": len(content), "url": public_url, "path": path}}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Upload failed: {str(e)[:100]}") from e


# ============================================================================
# Memory System Hooks
# ============================================================================

@router.post("/memory/hooks")
async def create_memory_hook(request: MemoryHookRequest, authorization: str = Header(None)):
    user_id = get_user_id_from_token(authorization)
    memory = await save_memory(user_id, request.content, importance=request.importance)
    if not memory:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to save memory")
    return {"status": "OK", "memory": memory}


@router.get("/memory/hooks")
async def list_memory_hooks(authorization: str = Header(None), limit: int = Query(default=50, ge=1, le=200)):
    user_id = get_user_id_from_token(authorization)
    memories = await get_user_memory(user_id, limit=limit)
    return {"status": "OK", "memories": memories, "count": len(memories)}


# ============================================================================
# Multi-language Support (i18n translations)
# ============================================================================

LANG_PACKS = {
    "en": {
        "new_chat": "New chat",
        "search_placeholder": "Search messages...",
        "send": "Send",
        "stop": "Stop",
        "export": "Export",
        "pin": "Pin",
        "unpin": "Unpin",
        "share": "Share",
        "folders": "Folders",
        "voice_input": "Voice input",
        "upload_file": "Upload file",
        "theme": "Theme",
        "language": "Language",
        "profile": "Profile",
        "settings": "Settings",
    },
    "es": {
        "new_chat": "Nuevo chat",
        "search_placeholder": "Buscar mensajes...",
        "send": "Enviar",
        "stop": "Detener",
        "export": "Exportar",
        "pin": "Fijar",
        "unpin": "Desfijar",
        "share": "Compartir",
        "folders": "Carpetas",
        "voice_input": "Entrada de voz",
        "upload_file": "Subir archivo",
        "theme": "Tema",
        "language": "Idioma",
        "profile": "Perfil",
        "settings": "Configuración",
    },
    "fr": {
        "new_chat": "Nouvelle discussion",
        "search_placeholder": "Rechercher des messages...",
        "send": "Envoyer",
        "stop": "Arrêter",
        "export": "Exporter",
        "pin": "Épingler",
        "unpin": "Désépingler",
        "share": "Partager",
        "folders": "Dossiers",
        "voice_input": "Entrée vocale",
        "upload_file": "Télécharger un fichier",
        "theme": "Thème",
        "language": "Langue",
        "profile": "Profil",
        "settings": "Paramètres",
    },
    "de": {
        "new_chat": "Neuer Chat",
        "search_placeholder": "Nachrichten suchen...",
        "send": "Senden",
        "stop": "Stopp",
        "export": "Exportieren",
        "pin": "Anheften",
        "unpin": "Lösen",
        "share": "Teilen",
        "folders": "Ordner",
        "voice_input": "Spracheingabe",
        "upload_file": "Datei hochladen",
        "theme": "Design",
        "language": "Sprache",
        "profile": "Profil",
        "settings": "Einstellungen",
    },
    "ja": {
        "new_chat": "新しいチャット",
        "search_placeholder": "メッセージを検索...",
        "send": "送信",
        "stop": "停止",
        "export": "エクスポート",
        "pin": "ピン留め",
        "unpin": "ピン解除",
        "share": "共有",
        "folders": "フォルダ",
        "voice_input": "音声入力",
        "upload_file": "ファイルをアップロード",
        "theme": "テーマ",
        "language": "言語",
        "profile": "プロフィール",
        "settings": "設定",
    },
    "zh": {
        "new_chat": "新对话",
        "search_placeholder": "搜索消息...",
        "send": "发送",
        "stop": "停止",
        "export": "导出",
        "pin": "置顶",
        "unpin": "取消置顶",
        "share": "分享",
        "folders": "文件夹",
        "voice_input": "语音输入",
        "upload_file": "上传文件",
        "theme": "主题",
        "language": "语言",
        "profile": "个人资料",
        "settings": "设置",
    },
}


@router.get("/i18n")
async def get_i18n_pack(lang: str = Query(default="en")):
    pack = LANG_PACKS.get(lang, LANG_PACKS["en"])
    return {"status": "OK", "lang": lang, "translations": pack}


@router.get("/i18n/languages")
async def list_supported_languages():
    return {"status": "OK", "languages": [{"code": code, "name": code.upper()} for code in LANG_PACKS.keys()]}


# ============================================================================
# Theme Customization
# ============================================================================

@router.get("/themes")
async def list_themes():
    return {
        "status": "OK",
        "themes": [
            {"id": "dark", "name": "Dark", "tokens": {"--bg-primary": "#0f172a", "--text-primary": "#f1f5f9"}},
            {"id": "light", "name": "Light", "tokens": {"--bg-primary": "#ffffff", "--text-primary": "#0f172a"}},
            {"id": "midnight", "name": "Midnight", "tokens": {"--bg-primary": "#020617", "--text-primary": "#f8fafc"}},
        ],
    }


# ============================================================================
# Conversation Metadata (extended)
# ============================================================================

@router.patch("/conversations/{conversation_id}")
async def update_conversation_meta(conversation_id: str, authorization: str = Header(None), title: Optional[str] = None, folder_id: Optional[str] = None, is_pinned: Optional[bool] = None):
    user_id = get_user_id_from_token(authorization)
    conv = await get_conversation(conversation_id, user_id)
    if not conv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    updates = {}
    if title is not None:
        updates["title"] = title
    if folder_id is not None:
        updates["folder_id"] = folder_id
    if is_pinned is not None:
        updates["is_pinned"] = is_pinned
    if not updates:
        return {"status": "OK", "conversation": conv}
    updated = await update_conversation(conversation_id, **updates)
    return {"status": "OK", "conversation": updated}
