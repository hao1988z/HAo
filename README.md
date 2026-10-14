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

## art/globe/ — 網路地球（Network Globe）幾何重建

`art/globe/reference.webp` 的手工向量重建。所有幾何都由 `art/globe/globe-data.json`
（從原圖量測的參數）經 `tools/build_globe_svg.py` 產生，不是自動描圖。

| 檔案 | 說明 |
|---|---|
| `art/globe/globe.svg` | 最終向量檔（Illustrator 可直接開啟） |
| `art/globe/globe-preview.png` | SVG 的 1:1 預覽 |
| `art/globe/compare.png` | 左：原圖／右：重建 |
| `art/globe/globe-express.html` | 匯入 Adobe Express 用的單頁 HTML |
| `art/globe/globe-data.json` | 量測參數：球心/半徑、經緯網、節點、連線、陸地輪廓、點陣 |
| `tools/build_globe_svg.py` | 產生 SVG |
| `tools/build_globe_express.py` | 由 `globe.svg` 產生 Express 匯入頁 |
| `tools/bezierfit.py` | 輪廓 → 少錨點三次 Bézier（去抖動、只保留真角點、切線連續） |

重建方法：

- **球體**：一個正圓（由 alpha 邊緣擬合，r = 547.5）。
- **經緯網**：真正的 15° 球面經緯網（傾角 −11°、滾轉 3°）；每條經線／緯線都是圓的正交投影，
  因此每一條都是單一 SVG 橢圓弧（`A` 指令），沒有任何描圖點。
- **連線**：節點之間用單一圓弧（`A`）或單一二次 Bézier（`Q`），曲率由原圖量測擬合；
  虛線航線用 `stroke-dasharray`。
- **節點**：35 個正圓，白芯 → 黃環 → 橘色衰減完全用放射漸層表現。
- **陸地**：淺色大陸用少錨點的平滑三次 Bézier 輪廓；點陣大陸是規律點陣
  （間距 7.5 px，帶球面收縮），以虛線筆畫（dash 0 + 圓端點）繪製，
  每一排點只需 2 個錨點。
- **光效**：放射／線性漸層 + 高斯模糊濾鏡（節點光暈、連線輝光、點陣柔光、球緣高光）。

Adobe Express 匯入說明：Express 的 HTML 匯入器會把每個 SVG 元素拆成獨立可編輯圖層，
但會丟掉 `stroke-linecap`、`clip-path` 與群組濾鏡。因此 `globe-express.html` 採混合式：
海洋、淺色陸地、經緯網、連線、航線、節點、球緣都是原生可編輯向量圖層；
只有需要被丟掉之功能的三層（點陣大陸、連線輝光、節點光暈）以內嵌 SVG 圖片匯入。
