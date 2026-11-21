# 台股分點融資斷頭雷達 (Streamlit 版)

可在 GitHub 上託管並一鍵部署至 **Streamlit Community Cloud** 的台股分點融資斷頭價位試算工具。

## 功能特色
- **免費資料抓取**：後端 Python 直接向證交所 OpenAPI 抓取最新收盤價，並支援從公開券商分點網頁抓取買超分點明細（無瀏覽器 CORS 限制）。
- **彈性成本微調**：內建可編輯表格（`st.data_editor`），可直接微調各分點買進均價與張數並即時重算。
- **下跌壓力測試**：拖動「模擬現價」滑桿，即時檢視各分點維持率、已破 130% 追繳線家數與潛在斷頭賣壓牆。
- **多元匯入**：同步支援 CSV 檔案上傳與 FinMind Sponsor API 串接。

## 本機執行
```bash
pip install -r requirements.txt
streamlit run app.py
```

## 部署到 GitHub + Streamlit Community Cloud（免費）
1. 在 GitHub 建立一個新的 Repository，將本資料夾內的 `app.py`、`requirements.txt`、`README.md` 推送上去。
2. 前往 [Streamlit Community Cloud](https://share.streamlit.io/) 使用 GitHub 帳號登入。
3. 點擊 **New app** → 選擇你的 Repository、Branch（`main`）與主程式路徑（`app.py`）→ 點擊 **Deploy!** 即可取得公開網址。
