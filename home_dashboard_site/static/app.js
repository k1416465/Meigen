// 時計と日付を更新
function updateClock() {
  const now = new Date();
  const clock = document.getElementById("clock");
  if (clock) clock.textContent = new Intl.DateTimeFormat("ja-JP", {
    timeZone: "Asia/Tokyo", hour: "2-digit", minute: "2-digit", second: "2-digit", hour12: false
  }).format(now);
  const date = document.getElementById("clockDate");
  if (date) {
    const dateText = new Intl.DateTimeFormat("ja-JP", {timeZone:"Asia/Tokyo", year:"numeric", month:"long", day:"numeric"}).format(now);
    const weekday = new Intl.DateTimeFormat("ja-JP", {timeZone:"Asia/Tokyo", weekday:"short"}).format(now);
    date.textContent = `${dateText}（${weekday}）`;
  }
}
updateClock();
setInterval(updateClock, 1000);

// 外観設定（ライト・ダーク・デバイス設定）
// アイコンは static/icons/light/ と static/icons/dark/ に同名ファイルを置くと、
// 現在の外観に合わせて自動的に切り替わります。
const themeToggle = document.getElementById("themeToggle");
const appearanceSetting = document.body.dataset.appearance || "system";
const savedTheme = localStorage.getItem("myHomeTheme");
function devicePrefersDark() {
  return window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches;
}
function updateThemeIcons(theme) {
  document.querySelectorAll("img.custom-icon").forEach((img) => {
    const currentSrc = img.dataset.baseSrc || img.getAttribute("src") || "";
    if (!img.dataset.baseSrc) img.dataset.baseSrc = currentSrc;
    const fileName = img.dataset.iconName || img.dataset.baseSrc.split("/").pop();
    img.dataset.iconName = fileName;
    const themedSrc = `/static/icons/${theme === "dark" ? "dark" : "light"}/${fileName}`;
    img.onerror = () => {
      // テーマ別画像がまだ用意されていない場合は通常の icons フォルダーを使う
      img.onerror = null;
      img.src = img.dataset.baseSrc;
    };
    img.src = themedSrc;
  });
}
function setTheme(theme) {
  document.body.classList.toggle("dark", theme === "dark");
  document.documentElement.dataset.theme = theme;
  updateThemeIcons(theme);

  // 切り替えボタン専用アイコン：画像は static/icons/ に置きます。
  // ライトモード中はダークモードへ切り替える画像、
  // ダークモード中はライトモードへ切り替える画像を表示します。
  const themeIcon = document.getElementById("themeIcon");
  if (themeIcon) {
    themeIcon.src = theme === "dark"
      ? "/static/icons/theme-light.png"
      : "/static/icons/theme-dark.png";
  }
}
const initialTheme = savedTheme || (appearanceSetting === "system" ? (devicePrefersDark() ? "dark" : "light") : appearanceSetting);
setTheme(initialTheme);
if (themeToggle) themeToggle.addEventListener("click", () => {
  const nextTheme = document.body.classList.contains("dark") ? "light" : "dark";
  localStorage.setItem("myHomeTheme", nextTheme);
  setTheme(nextTheme);
});
if (window.matchMedia) {
  window.matchMedia("(prefers-color-scheme: dark)").addEventListener?.("change", () => {
    if (!localStorage.getItem("myHomeTheme") && appearanceSetting === "system") {
      setTheme(devicePrefersDark() ? "dark" : "light");
    }
  });
}

// 設定の「My路線」に応じた運行情報（1分ごとに更新）
const operationTopLink = document.getElementById("operationTopLink");
const operationStatusText = document.getElementById("operationStatusText");
const operationTopLabel = document.querySelector(".operation-top-label");
async function loadOperationStatus() {
  if (!operationStatusText) return;
  try {
    const response = await fetch("/api/operation", {cache: "no-store"});
    if (!response.ok) throw new Error("operation request failed");
    const data = await response.json();
    if (operationTopLabel && data.route) operationTopLabel.textContent = data.route;
    operationStatusText.textContent = data.status || "取得できません";
    operationStatusText.dataset.state = data.ok ? (data.status === "平常運転" ? "normal" : "alert") : "error";
    if (operationTopLink) {
      operationTopLink.href = data.source_url || "https://transit.yahoo.co.jp/diainfo/area/4";
      operationTopLink.title = `${data.route || "運行情報"}：${data.status || "取得できません"}。${data.detail || ""}`;
      operationTopLink.setAttribute("aria-label", operationTopLink.title);
    }
  } catch (error) {
    operationStatusText.textContent = "取得できません";
    operationStatusText.dataset.state = "error";
    if (operationTopLink) operationTopLink.title = "運行情報を取得できません。時間をおいて再読み込みしてください。";
  }
}
if (operationStatusText) {
  loadOperationStatus();
  setInterval(loadOperationStatus, 60 * 1000);
}

// 設定画面で選択した地点に応じた天気予報
const WEATHER_PLACES = {
  utsunomiya: {label:"宇都宮市", lat:36.5551, lon:139.8828},
  oyama: {label:"小山市", lat:36.3147, lon:139.8002},
  tochigi: {label:"栃木市", lat:36.3824, lon:139.7342},
  sano: {label:"佐野市", lat:36.3145, lon:139.5783},
  ashikaga: {label:"足利市", lat:36.3402, lon:139.4497}
};
async function loadWeather() {
  const key = document.body.dataset.weatherPlace || "sano";
  const place = WEATHER_PLACES[key] || WEATHER_PLACES.sano;
  const url = `https://api.open-meteo.com/v1/forecast?latitude=${place.lat}&longitude=${place.lon}&current=temperature_2m,weather_code&daily=temperature_2m_max,temperature_2m_min,precipitation_probability_max&timezone=Asia%2FTokyo&forecast_days=1`;
  const location = document.getElementById("weatherLocation");
  if (location) location.textContent = place.label;
  try {
    const response = await fetch(url);
    if (!response.ok) throw new Error("weather request failed");
    const data = await response.json();
    const current = data.current, daily = data.daily, weather = describeWeather(current.weather_code);
    document.getElementById("weatherTemp").textContent = `${Math.round(current.temperature_2m)}°`;
    document.getElementById("weatherDesc").textContent = weather.label;
    document.getElementById("weatherSymbol").textContent = weather.symbol;
    document.getElementById("weatherMax").textContent = `${Math.round(daily.temperature_2m_max[0])}°`;
    document.getElementById("weatherMin").textContent = `${Math.round(daily.temperature_2m_min[0])}°`;
    document.getElementById("weatherRain").textContent = `${daily.precipitation_probability_max?.[0] ?? "--"}%`;
  } catch (error) {
    document.getElementById("weatherDesc").textContent = "天気情報を取得できません";
  }
}
function describeWeather(code) {
  if (code === 0) return {label:"快晴", symbol:"☀"};
  if ([1,2].includes(code)) return {label:"晴れ・一部くもり", symbol:"🌤"};
  if (code === 3) return {label:"くもり", symbol:"☁"};
  if ([45,48].includes(code)) return {label:"霧", symbol:"🌫"};
  if ([51,53,55,56,57].includes(code)) return {label:"霧雨", symbol:"🌦"};
  if ([61,63,65,66,67,80,81,82].includes(code)) return {label:"雨", symbol:"🌧"};
  if ([71,73,75,77,85,86].includes(code)) return {label:"雪", symbol:"❄"};
  if ([95,96,99].includes(code)) return {label:"雷雨", symbol:"⛈"};
  return {label:"天気", symbol:"🌡"};
}
if (document.getElementById("weatherTemp")) loadWeather();
