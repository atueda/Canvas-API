import json
import os
import requests
import logging
from dotenv import load_dotenv
from slack_bolt import App, Ack
from slack_sdk.web import WebClient
from slack_bolt.adapter.socket_mode import SocketModeHandler

# 環境変数をロード
load_dotenv()

logging.basicConfig(level=logging.DEBUG)

client = WebClient(token=os.environ["SLACK_BOT_TOKEN"])
# ボットトークンとソケットモードハンドラーの設定
app = App(
    signing_secret=os.environ["SLACK_SIGNING_SECRET"],
    token=os.environ["SLACK_BOT_TOKEN"],
)

@app.command("/hello-bolt-python")
def command(ack, body, respond):
    ack()
    respond(f"Hi <@{body['user_id']}>!")
    # views.open という API を呼び出すことでモーダルを開きます
    client.views_open(
        # 上記で説明した trigger_id で、これは必須項目です
        # この値は、一度のみ 3 秒以内に使うという制約があることに注意してください
        trigger_id=body["trigger_id"],
        # モーダルの内容を view オブジェクトで指定します
        view={
            # このタイプは常に "modal"
            "type": "modal",
            # このモーダルに自分で付けられる ID で、次に説明する @app.view リスナーはこの文字列を指定します
            "callback_id": "modal-id",
            # これは省略できないため、必ず適切なテキストを指定してください
            "title": {"type": "plain_text", "text": "テストモーダル"},
            # input ブロックを含まないモーダルの場合は view から削除することをおすすめします
            # このコード例のように input ブロックがあるときは省略できません
            "submit": {"type": "plain_text", "text": "送信"},
            # 閉じるボタンのラベルを調整することができます（必須ではありません）
            "close": {"type": "plain_text", "text": "閉じる"},
            # Block Kit の仕様に準拠したブロックを配列で指定
            # 見た目の調整は https://app.slack.com/block-kit-builder を使うと便利です
            "blocks": [
                {
                    # モーダルの通常の使い方では input ブロックを使います
                    # ブロックの一覧はこちら: https://api.slack.com/reference/block-kit/blocks
                    "type": "input",
                    # block_id / action_id を指定しない場合 Slack がランダムに指定します
                    # この例のように明に指定することで、@app.view リスナー側での入力内容の取得で
                    # ブロックの順序に依存しないようにすることをおすすめします
                    "block_id": "question-block",
                    # ブロックエレメントの一覧は https://api.slack.com/reference/block-kit/block-elements
                    # Works with block types で Input がないものは input ブロックに含めることはできません
                    "element": {"type": "plain_text_input", "action_id": "input-element"},
                    # これはモーダル上での見た目を調整するものです
                    # 同様に placeholder を指定することも可能です 
                    "label": {"type": "plain_text", "text": "質問"},
                }
            ],
        },
    )
    
# Canvas作成コマンドのハンドラー
@app.command("/create_canvas")
def handle_create_canvas(ack: Ack, body: dict, client: WebClient, respond):
  try:
      ack()
      # respond(f"Hi <@{body['user_id']}>!")
      #user_id = body['user_id']
      trigger_id = body['trigger_id']
      
      view = {
          "type": "modal",
          "callback_id": "create_canvas_view",
          "title": {
              "type": "plain_text",
              "text": "Create Canvas"
          },
          "blocks": [
              {
                  "type": "input",
                  "block_id": "title_block",
                  "label": {
                      "type": "plain_text",
                      "text": "Title"
                  },
                  "element": {
                      "type": "plain_text_input",
                      "action_id": "title_input"
                  }
              },
              {
                  "type": "input",
                  "block_id": "users_select",
                  "label": {
                      "type": "plain_text",
                      "text": "owner select"
                  },
                  "element": {
                      "type": "users_select",
                      "action_id": "users_select",
                      "placeholder": {
                          "type": "plain_text",
                          "text": "Select users"
                      }
                  }
              },
              {
                  "type": "input",
                  "block_id": "content_block",
                  "label": {
                      "type": "plain_text",
                      "text": "Content"
                  },
                  "element": {
                      "type": "plain_text_input",
                      "action_id": "content_input",
                      "multiline": True
                  }
              }
          ],
          "submit": {
              "type": "plain_text",
              "text": "Submit"
          }
      }

      client.views_open(trigger_id=trigger_id, view=view)

  except Exception as e:
      print(f'{e}')

# Canvas作成モーダルのサブミッションハンドラー
@app.view("create_canvas_view")
def handle_create_view_submission(ack: Ack, view: dict, logger: logging.Logger):
    ack()
    state_values = view['state']['values']
    user_id = state_values['users_select']['users_select']['selected_user']
    title = state_values['title_block']['title_input']['value']
    content = state_values['content_block']['content_input']['value']

    data = {
        "title": title,
        "owner_id": user_id,
        "document_content": {"type": "markdown", "markdown": "> standalone canvas!" + content}
    }
    # データをJSONに変換
    json_data = json.dumps(data)
    res = requests.post('https://slack.com/api/canvases.create',
        headers = {
          'Authorization': 'Bearer ' + os.environ["SLACK_BOT_TOKEN"],
          'Content-Type': 'application/json'
        },
        data=json_data
    )
    res_data = res.json()
    print(f'response: {res_data.get}')

    if res_data.get('ok'):
        canvas_id = res_data.get('canvas_id')
    else:
        error_message = res_data.get('error')
        client.chat_postMessage(
            channel=user_id,
            text=f"Failed to create canvas: {error_message}"
        )
        return

    # Canvas APIを使ってコンテンツを作成
    # canvas_id = app.client.canvases_create(
    #     title = title,
    #     owner_id = user_id,
    #     document_content = document_content
    # )
    
    # 結果をユーザーに通知
    client.chat_postMessage(
        channel=user_id,
        text=f"Canvas created successfully \nid: {canvas_id} \ntitle: {title} \n url: `https://autest-dev1.slack.com/docs/T05SD2E14R3/{canvas_id}`"
    )

# Canvas編集コマンドのハンドラー
@app.command("/edit_canvas")
def handle_edit_canvas(ack: Ack, body: dict, client: WebClient):
    ack()
    user_id = body['user_id']
    trigger_id = body['trigger_id']
    

    view = {
        "type": "modal",
        "callback_id": "edit_canvas_view",
        "title": {
            "type": "plain_text",
            "text": "Edit Canvas"
        },
        "blocks": [
              {
                  "type": "input",
                  "block_id": "users_select",
                  "label": {
                      "type": "plain_text",
                      "text": "users select"
                  },
                  "element": {
                      "type": "users_select",
                      "action_id": "users_select",
                      "placeholder": {
                          "type": "plain_text",
                          "text": "Select users"
                      }
                  }
              },
            {
                "type": "input",
                "block_id": "title_block",
                "label": {
                    "type": "plain_text",
                    "text": "Title"
                },
                "element": {
                    "type": "plain_text_input",
                    "action_id": "title_input",
                }
            },
            {
                "type": "input",
                "block_id": "canvas_id_block",
                "label": {
                    "type": "plain_text",
                    "text": "Canvas ID"
                },
                "element": {
                    "type": "plain_text_input",
                    "action_id": "canvas_id",
                }
            },
            {
                "type": "input",
                "block_id": "content_block",
                "label": {
                    "type": "plain_text",
                    "text": "Content"
                },
                "element": {
                    "type": "plain_text_input",
                    "action_id": "content_input",
                    "multiline": True
                }
            }
        ],
        "submit": {
            "type": "plain_text",
            "text": "Submit"
        }
    }

    client.views_open(trigger_id=trigger_id, view=view)

# Canvas編集モーダルのサブミッションハンドラー
@app.view("edit_canvas_view")
def handle_edit_view_submission(ack: Ack, view: dict, logger: logging.Logger):
    ack()
    state_values = view['state']['values']
    user_id = state_values['users_select']['users_select']['selected_user']
    canvas_id = state_values['canvas_id_block']['canvas_id']['value']
    title = state_values['title_block']['title_input']['value']
    content = state_values['content_block']['content_input']['value']
    print(f"user_id: {user_id}")
    print(f"canvas_id: {canvas_id}" )

    data = {
        "canvas_id": canvas_id,
        "criteria": '{"contains_text":"canvas"}'
    }
    #セクションを取得
    json_data = json.dumps(data)
    res = requests.post('https://slack.com/api/canvases.sections.lookup ',
        headers = {
          'Authorization': 'Bearer ' + os.environ["SLACK_BOT_TOKEN"],
          'Content-Type': 'application/json'
        },
        data=json_data
    )
    res_data = res.json()
    print(f'res_data: {res_data}')
    sections = res_data.get('sections')[0]
    section = sections.get('id')
    
    print(f'section: {section}')
    data = {
        "title": title,
        "canvas_id": canvas_id,
        "changes": [{"operation":"insert_after","document_content":{"type":"markdown","markdown":"content edit"},"section_id":section }]
    }
    # データをJSONに変換
    json_data = json.dumps(data)
    res = requests.post('https://slack.com/api/canvases.edit',
        headers = {
          'Authorization': 'Bearer ' + os.environ["SLACK_BOT_TOKEN"],
          'Content-Type': 'application/json'
        },
        data=json_data
    )
    res_data = res.json()
    print(f'response: {res_data.get}')

    if res_data.get('ok'):
      # 結果をユーザーに通知
      client.chat_postMessage(
          channel=user_id,
          text=f"Canvas updated successfully with title: {title}"
      )
    else:
        error_message = res_data.get('error')
        client.chat_postMessage(
            channel=user_id,
            text=f"Failed to create canvas: {error_message}"
        )
        return
    # Canvas APIを使ってコンテンツを更新
    # canvas_response = client.canvases_edit(
    #     token = os.environ["SLACK_BOT_TOKEN"],
    #     canvas_id = canvas_id,
    #     changes = document_content
    # )

if __name__ == "__main__":
    handler = SocketModeHandler(app, os.environ.get("SLACK_APP_TOKEN"))
    handler.start()