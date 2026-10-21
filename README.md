# Blueworks Live MCP Server


## 構成

```
bwl-mcp-server/
├── __main__.py       # エントリーポイント
├── server.py         # MCPツール実装
├── requirements.txt  # 依存パッケージ
├── .env.example      # 環境変数テンプレート
└── README.md         # このファイル
```

## セットアップ

### 1. 依存パッケージをインストール

```bash
cd bwl/bwl-mcp-server
pip install -r requirements.txt
```

### 2. 環境変数を設定

```bash
cp .env.example .env
# .env を編集して認証情報を記入
```

**OAuth2 Service ID（推奨）**
1. Blueworks Live の Admin > Account Information を開く
2. **Enable API access via Service IDs** を有効化
3. Service ID を作成して Client ID / Client Secret を取得

**Basic 認証（テスト用）**
- メールアドレスとパスワードをそのまま設定

### 3. Bob の mcp.json に登録

`mcp.json` に以下を追加:

```json
{
  "mcpServers": {
    "blueworks-live": {
      "command": "/{path_to_folder}/.pyenv/versions/3.12.3/bin/python3",
      "args": [
        "/{path_to_mcp}/bwl-mcp-server/__main__.py"
      ],
      "env": {
        "BWL_ACCOUNT": "<account name>",
        "BWL_CLIENT_ID": "<client id>",
        "BWL_CLIENT_SECRET": "<client secret>"
      },
      "disabled": false,
      "alwaysAllow": []
    }
  }
}
```

## 使えるツール

| ツール | 機能 |
|--------|------|
| `bwl_get_server_info` | 接続設定の確認 |
| `bwl_search` | アーティファクトのテキスト検索 |
| `bwl_list_spaces` | スペース（フォルダ）一覧 |
| `bwl_get_process` | プロセス詳細の取得 |
| `bwl_list_process_revisions` | プロセスのリビジョン一覧 |
| `bwl_export_process_bpmn` | プロセスを BPMN 2.0 XML でエクスポート |
| `bwl_list_app_list` | 実行可能な Process App 一覧 |
| `bwl_start_process_instance` | プロセスインスタンスの開始 |
| `bwl_get_instance` | インスタンスの状態確認 |
| `bwl_list_instances` | インスタンス一覧 |
| `bwl_complete_task` | タスクの完了 |
| `bwl_get_account_info` | アカウント情報の取得 |

## 使用例

```
# プロセスを検索して BPMN をエクスポート
「経費申請」という名前のプロセスを検索して BPMN でエクスポートして

# ワークフローを実行
プロセス ID "abc123" のインスタンスを開始して

# 状態確認
インスタンス "xyz789" の現在の状態を確認して
```

## 認証方式について

| 方式 | 用途 | 設定 |
|------|------|------|
| OAuth2 Service ID | 自動化・本番 | `BWL_CLIENT_ID` + `BWL_CLIENT_SECRET` |
| Basic 認証 | テスト・開発 | `BWL_USERNAME` + `BWL_PASSWORD` |

OAuth2 を使う場合、Admin でアカウント単位の API 有効化が必要です。

