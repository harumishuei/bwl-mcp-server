#!/usr/bin/env python3
"""
Blueworks Live MCP Server

IBM Blueworks Live の REST API を MCP ツールとして公開するサーバー。
認証は OAuth2 (Service ID) または Basic 認証をサポート。

環境変数:
    BWL_ACCOUNT   : アカウント名 (例: mycompany)
    BWL_CLIENT_ID : Service ID の Client ID (OAuth2)
    BWL_CLIENT_SECRET : Service ID の Client Secret (OAuth2)
    BWL_USERNAME  : ユーザー名 (Basic 認証 fallback)
    BWL_PASSWORD  : パスワード (Basic 認証 fallback)
    BWL_BASE_URL  : ベースURL (デフォルト: https://www.blueworkslive.com)
"""

import os
import json
import base64
from typing import Optional
from datetime import datetime, timedelta

import requests
from fastmcp import FastMCP

# ─── 設定 ────────────────────────────────────────────────────────────────────

BWL_BASE_URL     = os.getenv("BWL_BASE_URL", "https://www.blueworkslive.com")
BWL_ACCOUNT      = os.getenv("BWL_ACCOUNT", "")
BWL_CLIENT_ID    = os.getenv("BWL_CLIENT_ID", "")
BWL_CLIENT_SECRET = os.getenv("BWL_CLIENT_SECRET", "")
BWL_USERNAME     = os.getenv("BWL_USERNAME", "")
BWL_PASSWORD     = os.getenv("BWL_PASSWORD", "")

# ─── MCPサーバー初期化 ────────────────────────────────────────────────────────

mcp = FastMCP("blueworks-live")

# ─── 認証ヘルパー ─────────────────────────────────────────────────────────────

_token_cache: dict = {}


def _get_oauth_token() -> str:
    """OAuth2 Client Credentials でアクセストークンを取得（キャッシュあり）"""
    now = datetime.utcnow()
    if _token_cache.get("expires_at") and now < _token_cache["expires_at"]:
        return _token_cache["access_token"]

    url = f"{BWL_BASE_URL}/oauth/token"
    resp = requests.post(
        url,
        data={
            "grant_type": "client_credentials",
            "client_id": BWL_CLIENT_ID,
            "client_secret": BWL_CLIENT_SECRET,
        },
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()
    _token_cache["access_token"] = data["access_token"]
    _token_cache["expires_at"] = now + timedelta(seconds=int(data.get("expires_in", 3600)) - 60)
    return _token_cache["access_token"]


def _build_headers(accept: str = "application/json") -> dict:
    """認証ヘッダーを構築。OAuth2 優先、なければ Basic 認証"""
    headers = {"accept": accept}
    if BWL_CLIENT_ID and BWL_CLIENT_SECRET:
        token = _get_oauth_token()
        headers["Authorization"] = f"Bearer {token}"
    elif BWL_USERNAME and BWL_PASSWORD:
        cred = base64.b64encode(f"{BWL_USERNAME}:{BWL_PASSWORD}".encode()).decode()
        headers["Authorization"] = f"Basic {cred}"
    else:
        raise ValueError(
            "認証情報が設定されていません。BWL_CLIENT_ID/BWL_CLIENT_SECRET "
            "または BWL_USERNAME/BWL_PASSWORD を設定してください。"
        )
    if BWL_ACCOUNT:
        headers["X-Account"] = BWL_ACCOUNT
    return headers


def _get(path: str, params: Optional[dict] = None, accept: str = "application/json") -> dict | str:
    """GETリクエストを送信"""
    url = f"{BWL_BASE_URL}{path}"
    headers = _build_headers(accept=accept)
    resp = requests.get(url, headers=headers, params=params, timeout=30)
    resp.raise_for_status()
    if accept == "application/json":
        return resp.json()
    return resp.text


def _post(path: str, payload: dict) -> dict:
    """POSTリクエストを送信"""
    url = f"{BWL_BASE_URL}{path}"
    headers = _build_headers()
    headers["Content-Type"] = "application/json"
    resp = requests.post(url, headers=headers, json=payload, timeout=30)
    resp.raise_for_status()
    return resp.json()


# ─── MCP ツール定義 ───────────────────────────────────────────────────────────

@mcp.tool()
def bwl_get_server_info() -> str:
    """
    接続中の Blueworks Live サーバーの設定情報を返す。
    認証が正しく設定されているかの確認に使う。
    """
    using_oauth = bool(BWL_CLIENT_ID and BWL_CLIENT_SECRET)
    using_basic = bool(BWL_USERNAME and BWL_PASSWORD)
    info = {
        "base_url": BWL_BASE_URL,
        "account": BWL_ACCOUNT or "(未設定)",
        "auth_method": "OAuth2 (Service ID)" if using_oauth else ("Basic" if using_basic else "未設定"),
        "credentials_configured": using_oauth or using_basic,
    }
    return json.dumps(info, ensure_ascii=False, indent=2)


@mcp.tool()
def bwl_search(
    query: str,
    artifact_type: str = "",
    max_results: int = 20,
) -> str:
    """
    Blueworks Live のアーティファクト（プロセス・ポリシー等）をテキスト検索する。

    Args:
        query: 検索キーワード（例: "経費申請"）
        artifact_type: 絞り込む種別。"process" / "policy" / "decision" / "" (全て)
        max_results: 最大取得件数（デフォルト20）

    Returns:
        検索結果の JSON 文字列
    """
    params: dict = {"query": query, "maxResults": max_results}
    if artifact_type:
        params["type"] = artifact_type
    data = _get("/scr/api/Search", params=params)
    return json.dumps(data, ensure_ascii=False, indent=2)


@mcp.tool()
def bwl_list_spaces(
    name: str = "",
    tag: str = "",
    archived_state: str = "active",
    top_level_only: bool = False,
) -> str:
    """
    Blueworks Live のスペース（フォルダ）一覧を取得する。

    Args:
        name: スペース名で絞り込み（部分一致）
        tag: タグで絞り込み
        archived_state: "active" / "archived" / "all"
        top_level_only: True のときトップレベルのスペースのみ返す

    Returns:
        スペース一覧の JSON 文字列
    """
    params: dict = {"archived-state": archived_state}
    if name:
        params["name"] = name
    if tag:
        params["tag"] = tag
    if top_level_only:
        params["top-space-only"] = "true"
    data = _get("/scr/api/spaces", params=params)
    return json.dumps(data, ensure_ascii=False, indent=2)


@mcp.tool()
def bwl_get_process(process_id: str) -> str:
    """
    指定したプロセスの詳細情報を取得する。

    Args:
        process_id: プロセスの ID（bwl_search の結果から取得）

    Returns:
        プロセス詳細の JSON 文字列
    """
    data = _get(f"/scr/api/process/{process_id}")
    return json.dumps(data, ensure_ascii=False, indent=2)


@mcp.tool()
def bwl_list_process_revisions(process_id: str) -> str:
    """
    プロセスのリビジョン（版）一覧を取得する。

    Args:
        process_id: プロセスの ID

    Returns:
        リビジョン一覧の JSON 文字列
    """
    data = _get(f"/scr/api/revision/{process_id}")
    return json.dumps(data, ensure_ascii=False, indent=2)


@mcp.tool()
def bwl_export_process_bpmn(
    process_id: str,
    revision_id: str = "latest",
) -> str:
    """
    プロセスを BPMN 2.0 XML 形式でエクスポートする。

    Args:
        process_id: プロセスの ID
        revision_id: リビジョン ID（省略時は最新版 "latest"）

    Returns:
        BPMN 2.0 XML 文字列
    """
    path = f"/scr/api/export/process/{process_id}/{revision_id}"
    xml = _get(path, accept="application/xml")
    return str(xml)


@mcp.tool()
def bwl_list_app_list() -> str:
    """
    ユーザーがインスタンスを開始できる Process App の一覧を取得する。

    Returns:
        Process App 一覧の JSON 文字列
    """
    data = _get("/scr/api/AppList")
    return json.dumps(data, ensure_ascii=False, indent=2)


@mcp.tool()
def bwl_start_process_instance(
    process_id: str,
    input_data: dict = {},
) -> str:
    """
    指定したプロセスの新しいインスタンスを開始する（ワークフロー実行）。

    Args:
        process_id: 実行するプロセスの ID
        input_data: プロセスに渡す入力データ（キーと値のdict）

    Returns:
        開始されたインスタンスの情報 JSON 文字列
    """
    payload = {"processId": process_id, "data": input_data}
    data = _post("/scr/api/startInstance", payload)
    return json.dumps(data, ensure_ascii=False, indent=2)


@mcp.tool()
def bwl_get_instance(instance_id: str) -> str:
    """
    実行中または完了したプロセスインスタンスの状態・詳細を取得する。

    Args:
        instance_id: インスタンス ID

    Returns:
        インスタンス詳細の JSON 文字列
    """
    data = _get(f"/scr/api/instance/{instance_id}")
    return json.dumps(data, ensure_ascii=False, indent=2)


@mcp.tool()
def bwl_list_instances(
    process_id: str = "",
    status: str = "",
    max_results: int = 20,
) -> str:
    """
    プロセスインスタンスの一覧を取得する。

    Args:
        process_id: 絞り込むプロセス ID（省略時は全プロセス）
        status: 絞り込むステータス（"active" / "completed" / "terminated" / ""）
        max_results: 最大取得件数

    Returns:
        インスタンス一覧の JSON 文字列
    """
    params: dict = {"maxResults": max_results}
    if process_id:
        params["processId"] = process_id
    if status:
        params["status"] = status
    data = _get("/scr/api/instances", params=params)
    return json.dumps(data, ensure_ascii=False, indent=2)


@mcp.tool()
def bwl_complete_task(
    instance_id: str,
    task_id: str,
    output_data: dict = {},
) -> str:
    """
    実行中インスタンスの指定タスクを完了させる。

    Args:
        instance_id: インスタンス ID
        task_id: 完了させるタスク ID
        output_data: タスクの完了データ（キーと値のdict）

    Returns:
        完了結果の JSON 文字列
    """
    payload = {
        "instanceId": instance_id,
        "taskId": task_id,
        "data": output_data,
    }
    data = _post("/scr/api/completeTask", payload)
    return json.dumps(data, ensure_ascii=False, indent=2)


@mcp.tool()
def bwl_get_account_info() -> str:
    """
    接続中アカウントの情報（ユーザー、権限、ライセンス等）を取得する。

    Returns:
        アカウント情報の JSON 文字列
    """
    data = _get("/scr/api/Auth")
    return json.dumps(data, ensure_ascii=False, indent=2)
