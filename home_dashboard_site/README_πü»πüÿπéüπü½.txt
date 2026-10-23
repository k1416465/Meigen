【My Home ホーム画面サイト】

■ できること
・リアルタイム時計
・ライト／ダークモード切り替え
・今日の時間割と週間時間割
・固定表示の学校行事
・天気予報（Open-Meteo API）
・鉄道路線情報を後から追加しやすい構成
・スマートフォン／パソコン対応

■ 起動方法（Windows）
1. ZIPを展開します。
2. 展開したフォルダーを開き、アドレスバーに cmd と入力して Enter を押します。
3. 次のコマンドを1行ずつ実行します。

   py -m venv .venv
   .venv\Scripts\activate
   py -m pip install -r requirements.txt
   py app.py

4. ブラウザーで http://127.0.0.1:5000 を開きます。
5. 終了するときは、コマンド画面で Ctrl + C を押します。

■ 時間割を変更する
app.py をメモ帳や Visual Studio Code で開き、TIMETABLE の科目名を変更してください。
月曜日から金曜日まで、各曜日のリストに7科目を設定します。

■ 学校行事を変更する
app.py の SCHOOL_EVENTS を変更してください。
日付は YYYY-MM-DD、title は行事名、detail は補足です。
これは固定データなので、サイト画面からの編集機能はまだありません。

■ 天気の地点を変更する
static/app.js の loadWeather() にある latitude と longitude を変更します。
weatherLocation の表示名も合わせて変更してください。
天気の取得にはインターネット接続が必要です。

■ 下部メニューを変更する
templates/base.html の「下部メニュー」コメントの下にある nav-item を編集します。
アイコンやリンク先、項目名をあとから変更できます。

■ 注意
・授業・行事はサンプルです。実際の学校情報に変更してから使用してください。
・この段階では鉄道情報は未接続で、路線設定ボタンは準備中です。
・天気は Open-Meteo のAPIを利用しています。
