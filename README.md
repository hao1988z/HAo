# HAo

## art/ — 幾何重建（Geometric Reconstruction）

`art/reference.webp` 的手工向量重建，不是自動描圖（auto-trace）。

| 檔案 | 說明 |
|---|---|
| `art/brick-room.svg` | 最終向量檔，可直接用 Illustrator 開啟 |
| `art/brick-room-preview.png` | SVG 的 1:1 預覽 |
| `art/compare.png` | 上：原圖／下：重建 |
| `art/brick-room-express.html` | 匯入 Adobe Express 用的單頁 HTML |
| `tools/build_svg.py` | 由量測參數產生 SVG（`python3 tools/build_svg.py > art/brick-room.svg`） |
| `tools/render.mjs` | 用 Playwright 把 SVG 轉成 PNG 檢查 |

重建方法：

- **磚牆橫縫**：全部套用同一條圓柱透視曲線 `y = 576.75 + d·√(1+((x−940)/1470)²)`（雙曲線），
  以「雙段三次 Bézier」擬合一次（最大誤差 0.004 px），每一條橫縫都是同一模板的垂直縮放，
  每條只有 3 個錨點，中心錨點兩側把手水平、切線連續。行距固定 31.016 px。
- **磚縫**：真正的垂直直線，89 px 等距的錯縫排列（running bond）。
- **光楔／地板色帶／陽光光束**：全部是直線邊的多邊形，邊線由原圖量測擬合。
- **光效**：只用線性漸層、透明度與高斯模糊濾鏡，不用混合模式，
  在瀏覽器、Illustrator、Adobe Express 中顯示一致。
- 原圖中的手繪抖動、筆觸雜訊與不規則磚縫都刻意捨棄（shape fidelity > pixel fidelity）。
